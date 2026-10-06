"""Clasificación de eventos de cámaras con un modelo de visión (Claude o
Gemini, según ConfiguracionIA) — le muestra a la IA el snapshot del evento y
el catálogo de TipoEventoIA activos de la empresa, y le pide que diga cuáles
aplican (EPP faltante, caída, comportamiento riesgoso, humo/incendio, etc.,
según lo que el cliente haya configurado en Sistema → Eventos IA).

Nunca rompe el flujo de recibir_evento_camara si falla: cualquier error de
red/API queda registrado en evento.ia_error y el evento sigue su curso
normal — mismo patrón "opcional, se degrada solo" que disparar_alerta con
Brevo (ver notificaciones.py).
"""

import base64
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .costos_ia import gasto_del_periodo_usd, registrar_consumo
from .models import ConfiguracionIA, EventoDetectado, TipoEventoIA

logger = logging.getLogger("camaras_ia.ia_deteccion")

VENTANA_SIN_REPETIR_AVISO_IA = timedelta(minutes=10)

MODELOS_POR_DEFECTO = {
    ConfiguracionIA.Proveedor.CLAUDE: "claude-opus-5",
    ConfiguracionIA.Proveedor.GEMINI: "gemini-flash-latest",
}

PROMPT_SISTEMA = (
    "Eres un asistente de seguridad industrial (SST) que revisa fotos tomadas por "
    "cámaras de una obra o planta. Te doy una lista de eventos a buscar, cada uno "
    "con un id numérico y una descripción de qué debe verse en la imagen para que "
    "aplique. Revisa la imagen con cuidado y responde ÚNICAMENTE con un JSON, sin "
    'texto adicional ni markdown, con esta forma exacta: {"eventos": [<ids que sí '
    'aplican, puede ser una lista vacía>], "descripcion": "<1-2 frases en español '
    'sobre lo relevante que ves en la imagen>"}. No inventes eventos que no estén '
    "en la lista, y no marques un id si no estás razonablemente seguro."
)


class ErrorClasificacionIA(Exception):
    """La clasificación no se pudo completar — falta configuración, la API
    respondió con error, o la respuesta no se pudo interpretar."""


def clasificar_evento(evento):
    """Corre la clasificación IA sobre `evento` (EventoDetectado ya guardado,
    con snapshot) contra los TipoEventoIA activos asignados a su cámara.
    Guarda el resultado directamente en el evento — no devuelve nada, se usa
    por su efecto secundario, igual que disparar_alerta. Si la IA detecta
    alguno, el evento queda como alerta y se avisa al personal interno. Si no
    hay API key configurada o la cámara no tiene eventos asignados, no hace
    nada silenciosamente (funcionalidad opcional)."""
    if not evento.snapshot:
        return

    config = ConfiguracionIA.obtener()
    api_key = config.api_key or _api_key_por_defecto(config.proveedor)
    if not api_key:
        return

    tipos = list(TipoEventoIA.objects.filter(camaras=evento.camara, activo=True))
    if not tipos:
        return

    try:
        evento.snapshot.open("rb")
        imagen_bytes = evento.snapshot.read()
    finally:
        evento.snapshot.close()

    modelo = config.modelo or MODELOS_POR_DEFECTO[config.proveedor]

    if config.proveedor == ConfiguracionIA.Proveedor.CLAUDE:
        gasto = gasto_del_periodo_usd(config)
        if gasto >= config.tope_usd:
            evento.ia_error = f"Tope de consumo de IA alcanzado (USD {gasto:.2f} de {config.tope_usd:.2f})."
            evento.ia_analizado_en = timezone.now()
            evento.save(update_fields=["ia_error", "ia_analizado_en"])
            return

    try:
        if config.proveedor == ConfiguracionIA.Proveedor.GEMINI:
            resultado = _clasificar_con_gemini(api_key, modelo, imagen_bytes, tipos)
        else:
            resultado = _clasificar_con_claude(api_key, modelo, imagen_bytes, tipos, evento)
    except Exception as err:
        logger.exception("No se pudo clasificar con IA el evento_id=%s", evento.pk)
        evento.ia_error = str(err)[:255]
        evento.ia_analizado_en = timezone.now()
        evento.save(update_fields=["ia_error", "ia_analizado_en"])
        return

    ids_devueltos = set(resultado.get("eventos", []))
    detectados = [t for t in tipos if t.id in ids_devueltos]
    evento.tipos_ia.set(detectados)
    evento.descripcion_ia = str(resultado.get("descripcion", ""))[:2000]
    evento.ia_analizado_en = timezone.now()
    evento.ia_error = ""
    if detectados:
        # En la respuesta al equipo local: con disparo_alerta graba el clip del evento.
        evento.disparo_alerta = True
    evento.save(update_fields=["descripcion_ia", "ia_analizado_en", "ia_error", "disparo_alerta"])
    if detectados:
        _notificar_alerta_ia(evento, detectados)


def _notificar_alerta_ia(evento, detectados):
    """Push al personal interno — sin repetir el mismo evento IA de la misma
    cámara dentro de VENTANA_SIN_REPETIR_AVISO_IA: el equipo local reporta a
    la misma persona cada minuto mientras siga en la zona."""
    from core.push import enviar_push_a_personal_interno

    desde = evento.ia_analizado_en - VENTANA_SIN_REPETIR_AVISO_IA
    nuevos = [
        tipo
        for tipo in detectados
        if not EventoDetectado.objects.filter(camara=evento.camara, tipos_ia=tipo, ia_analizado_en__gte=desde)
        .exclude(pk=evento.pk)
        .exists()
    ]
    if not nuevos:
        return
    detalle = ", ".join(f"{tipo.nombre} ({tipo.get_severidad_display().lower()})" for tipo in nuevos)
    donde = f" en {evento.zona.nombre}" if evento.zona else ""
    enviar_push_a_personal_interno(
        f"Alerta IA — {evento.camara.nombre}", f"{detalle}{donde}.", url="/dashboard?ir=alertas"
    )


def _api_key_por_defecto(proveedor):
    if proveedor == ConfiguracionIA.Proveedor.GEMINI:
        return getattr(settings, "GEMINI_API_KEY", "")
    return getattr(settings, "ANTHROPIC_API_KEY", "")


def _catalogo_texto(tipos):
    return "\n".join(f"- id={t.id}: {t.nombre} — {t.descripcion}" for t in tipos)


def _clasificar_con_claude(api_key, modelo, imagen_bytes, tipos, evento):
    import anthropic  # noqa: PLC0415 (import perezoso — ver docstring de equipo_local/deteccion.py)

    cliente = anthropic.Anthropic(api_key=api_key)
    imagen_b64 = base64.standard_b64encode(imagen_bytes).decode("utf-8")
    try:
        respuesta = cliente.messages.create(
            model=modelo,
            max_tokens=1024,
            system=PROMPT_SISTEMA,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": imagen_b64}},
                    {"type": "text", "text": f"Eventos a buscar:\n{_catalogo_texto(tipos)}"},
                ],
            }],
        )
    except anthropic.APIError as err:
        raise ErrorClasificacionIA(f"Claude respondió con error: {err}") from err

    registrar_consumo(respuesta.model, respuesta.usage, evento)
    texto = next((bloque.text for bloque in respuesta.content if bloque.type == "text"), "{}")
    return _parsear_json(texto)


def _clasificar_con_gemini(api_key, modelo, imagen_bytes, tipos):
    from google import genai  # noqa: PLC0415
    from google.genai import types  # noqa: PLC0415

    cliente = genai.Client(api_key=api_key)
    try:
        respuesta = cliente.models.generate_content(
            model=modelo,
            contents=[
                types.Part.from_bytes(data=imagen_bytes, mime_type="image/jpeg"),
                f"Eventos a buscar:\n{_catalogo_texto(tipos)}",
            ],
            config=types.GenerateContentConfig(system_instruction=PROMPT_SISTEMA),
        )
    except Exception as err:
        raise ErrorClasificacionIA(f"Gemini respondió con error: {err}") from err

    return _parsear_json(respuesta.text or "{}")


def _parsear_json(texto):
    """La respuesta debería ser JSON puro (se lo pedimos explícito en el
    prompt), pero algunos modelos igual la envuelven en ```json ... ``` — se
    limpia eso antes de parsear. Si de todos modos no es JSON válido, se
    trata como "no se detectó nada" en vez de reventar la clasificación."""
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.lower().startswith("json"):
            texto = texto[4:]
        texto = texto.strip()
    try:
        datos = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Respuesta de IA no es JSON válido: %r", texto[:500])
        return {"eventos": [], "descripcion": ""}
    if not isinstance(datos, dict):
        return {"eventos": [], "descripcion": ""}
    return datos
