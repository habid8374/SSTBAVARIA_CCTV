"""Lógica de negocio del módulo: cruce zona+horario y disparo de alertas.

Nada de esto habla con cámaras — recibe un punto ya detectado (por el
equipo local, vía ONVIF/análisis propio de la cámara) y decide si cae
dentro de una zona restringida y si hay una regla de horario vigente.
"""

import logging
from datetime import timedelta
from html import escape

from django.utils import timezone

from .notificaciones import ErrorEnvioCorreo, enviar_correo_brevo, plantilla_aviso_marca

logger = logging.getLogger("camaras_ia.alertas")

# Mientras la persona siga en la zona, el equipo local reporta cada minuto:
# el correo de alerta de una misma cámara y zona sale como mucho una vez en
# esta ventana (el evento queda igual en el dashboard cada vez).
VENTANA_SIN_REPETIR_CORREO = timedelta(minutes=10)
URL_DASHBOARD = "https://sst-cctv.com"


def punto_en_poligono(punto, poligono):
    """Ray casting clásico: True si `punto` (x, y) cae dentro de `poligono`
    (lista de [x, y]). Polígonos de menos de 3 vértices nunca contienen nada.
    """
    if len(poligono) < 3:
        return False

    x, y = punto
    dentro = False
    x1, y1 = poligono[-1]
    for x2, y2 in poligono:
        if (y1 > y) != (y2 > y):
            x_interseccion = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_interseccion:
                dentro = not dentro
        x1, y1 = x2, y2
    return dentro


def punto_en_circulo(punto, centro, radio_px):
    """True si `punto` (x, y) cae dentro del círculo de centro `centro`
    (x, y) y radio `radio_px`, ya en píxeles. `radio_px` None o <= 0 nunca
    contiene nada (ej. cámara sin calibrar, ver Camara.px_por_metro)."""
    if radio_px is None or radio_px <= 0:
        return False
    x, y = punto
    cx, cy = centro
    return (x - cx) ** 2 + (y - cy) ** 2 <= radio_px**2


def punto_en_zona(punto, zona, px_por_metro=None):
    """Dispatch según zona.tipo: polígono (por defecto) o punto+radio real
    (necesita que la cámara esté calibrada — px_por_metro no None)."""
    if zona.tipo == zona.Tipo.PUNTO_RADIO:
        if zona.centro_x is None or zona.centro_y is None or zona.radio_metros is None or not px_por_metro:
            return False
        radio_px = zona.radio_metros * px_por_metro
        return punto_en_circulo(punto, (zona.centro_x, zona.centro_y), radio_px)
    return punto_en_poligono(punto, zona.poligono)


def _regla_vigente(regla, momento):
    """True si `regla` está activa para el día/hora de `momento`.

    Maneja horarios que cruzan medianoche (ej. 22:00–06:00): en ese caso el
    día que manda es el del inicio del turno, no el de la hora actual.
    """
    hora = momento.time()
    dia_hoy = momento.weekday()

    if regla.hora_inicio <= regla.hora_fin:
        return dia_hoy in regla.dias_semana and regla.hora_inicio <= hora <= regla.hora_fin

    if hora >= regla.hora_inicio:
        return dia_hoy in regla.dias_semana
    if hora <= regla.hora_fin:
        dia_anterior = (dia_hoy - 1) % 7
        return dia_anterior in regla.dias_semana
    return False


def evaluar_zona_horario(camara, punto, momento=None):
    """Cruza un punto detectado en `camara` contra sus zonas restringidas
    activas y las reglas de alerta vigentes en `momento` (por defecto ahora).

    Devuelve (zona, regla):
    - (None, None) si el punto no cae en ninguna zona activa de la cámara.
    - (zona, None) si cae en una zona pero ninguna de sus reglas activas
      aplica en este momento (fuera de horario).
    - (zona, regla) si cae en una zona y hay una regla vigente ahora mismo.
    """
    momento = momento or timezone.localtime()

    px_por_metro = camara.px_por_metro
    for zona in camara.zonas.filter(activa=True).prefetch_related("reglas"):
        if not punto_en_zona(punto, zona, px_por_metro):
            continue
        for regla in zona.reglas.filter(activa=True):
            if _regla_vigente(regla, momento):
                return zona, regla
        return zona, None

    return None, None


def disparar_alerta(evento, regla):
    """Dispara la notificación de una alerta.

    Canal "correo": envío real vía Brevo, con el resultado (éxito o el
    motivo del error) guardado en evento.notificacion_enviada/_detalle para
    que se vea en la bandeja de Alertas del dashboard.
    Canal "whatsapp": sigue siendo un stub — solo el log de abajo. Conectar
    un proveedor real de WhatsApp es una decisión de proveedor aparte que
    todavía no se ha tomado.
    """
    logger.warning(
        "ALERTA disparada: evento_id=%s camara=%s zona=%s canal=%s destinatario=%s",
        evento.pk,
        evento.camara_id,
        regla.zona_id,
        regla.canal_notificacion,
        regla.destinatario,
    )

    _enviar_push_alerta(evento)

    evento.canal_notificacion = regla.canal_notificacion
    if regla.canal_notificacion == "correo":  # ReglaAlerta.Canal.CORREO
        _enviar_notificacion_correo(evento, regla)
    else:
        evento.notificacion_enviada = False
        evento.notificacion_detalle = "Canal WhatsApp — integración de envío pendiente."
        evento.save(update_fields=["canal_notificacion", "notificacion_enviada", "notificacion_detalle"])

    _correo_alerta_de_zona(evento, regla)


def _correo_alerta_de_zona(evento, regla):
    """Correo a los correos de Sistema → Brevo por una alerta de zona — sin
    repetir la misma cámara y zona dentro de VENTANA_SIN_REPETIR_CORREO."""
    from .models import EventoDetectado

    desde = timezone.now() - VENTANA_SIN_REPETIR_CORREO
    ya_avisado = (
        EventoDetectado.objects.filter(camara=evento.camara, zona=evento.zona, correo_alerta_enviado_en__gte=desde)
        .exclude(pk=evento.pk)
        .exists()
    )
    if ya_avisado:
        return
    zona_nombre = evento.zona.nombre if evento.zona else "zona restringida"
    excluir = {regla.destinatario.strip().lower()} if regla.canal_notificacion == "correo" else set()
    enviados = enviar_correo_alerta_al_cliente(
        evento,
        asunto=f"Alerta GuardIA — persona en {zona_nombre} ({evento.camara.nombre_para_mostrar})",
        titulo=f"Persona en zona restringida: {zona_nombre}",
        detalle_html=(
            f"<p>Se detectó una persona en <strong>{escape(zona_nombre)}</strong> dentro del horario restringido.</p>"
        ),
        excluir=excluir,
    )
    if enviados:
        _registrar_correo_enviado(evento, enviados)


def enviar_correo_alerta_al_cliente(evento, *, asunto, titulo, detalle_html, excluir=()):
    """Manda el correo de una alerta, con la foto del momento, a cada correo
    de ConfiguracionNotificaciones.correos_alertas (menos los de `excluir`,
    que ya lo recibieron por el canal de la regla). Devuelve a cuáles salió.
    Nunca rompe el flujo del evento: un fallo de Brevo queda en el log."""
    from .models import ConfiguracionNotificaciones

    correos = [
        correo for correo in ConfiguracionNotificaciones.obtener().lista_correos_alertas()
        if correo.lower() not in excluir
    ]
    if not correos:
        return []

    adjunto_bytes = adjunto_nombre = None
    if evento.snapshot:
        try:
            evento.snapshot.open("rb")
            adjunto_bytes = evento.snapshot.read()
            adjunto_nombre = evento.snapshot.name.rsplit("/", 1)[-1]
        except Exception:
            logger.exception("No se pudo leer la foto del evento_id=%s para el correo", evento.pk)
        finally:
            evento.snapshot.close()

    momento = timezone.localtime(evento.timestamp)
    camara = escape(evento.camara.nombre_para_mostrar)
    ubicacion = f" — {escape(evento.camara.ubicacion)}" if evento.camara.ubicacion else ""
    cuerpo_html = (
        f'<div style="font-size:14px; line-height:1.6; color:#333333;">{detalle_html}'
        f"<p><strong>Cámara:</strong> {camara}{ubicacion}<br>"
        f"<strong>Fecha y hora:</strong> {momento:%d/%m/%Y %H:%M:%S}</p>"
        f'<p>La foto del momento va adjunta. Detalle e historial en <a href="{URL_DASHBOARD}/dashboard?ir=alertas" '
        f'style="color:#7a5e00;">GuardIA → Alertas</a>.</p></div>'
    )
    contenido_html = plantilla_aviso_marca(
        preheader=asunto,
        eyebrow="Alerta de cámaras",
        titulo=escape(titulo),
        cuerpo_html=cuerpo_html,
        logo_url=f"{URL_DASHBOARD}/logo-guardia.png",
        nota_html=(
            "Recibes este correo porque está en los correos de alertas de GuardIA (Sistema → Brevo). "
            "Si la persona sigue en la zona, no se repite el aviso de la misma cámara por 10 minutos."
        ),
    )
    enviados = []
    for correo in correos:
        try:
            enviar_correo_brevo(correo, asunto, contenido_html, adjunto_bytes, adjunto_nombre)
        except ErrorEnvioCorreo as err:
            logger.error("No se pudo enviar el correo de alerta a %s (evento_id=%s): %s", correo, evento.pk, err)
        else:
            enviados.append(correo)
    return enviados


def _registrar_correo_enviado(evento, enviados):
    texto = f"Correo de alerta enviado a {', '.join(enviados)}"
    if evento.notificacion_enviada and evento.notificacion_detalle:
        texto = f"{evento.notificacion_detalle} · {texto}"
    evento.notificacion_enviada = True
    evento.notificacion_detalle = texto[:255]
    evento.correo_alerta_enviado_en = timezone.now()
    evento.save(update_fields=["notificacion_enviada", "notificacion_detalle", "correo_alerta_enviado_en"])


def _enviar_push_alerta(evento):
    """Push al celular del personal interno — independiente del canal
    correo/whatsapp de la regla, para que se entere aunque no tenga la app
    abierta. Nunca rompe disparar_alerta si falla (ver core.push)."""
    from core.push import enviar_push_a_personal_interno

    zona_nombre = evento.zona.nombre if evento.zona else "zona restringida"
    enviar_push_a_personal_interno(
        "Alerta GuardIA — cámaras",
        f"Se detectó una persona en {zona_nombre} (cámara {evento.camara.nombre_para_mostrar}) fuera del horario permitido.",
        url="/dashboard?ir=alertas",
    )


def _enviar_notificacion_correo(evento, regla):
    zona_nombre = evento.zona.nombre if evento.zona else "zona restringida"
    momento = timezone.localtime(evento.timestamp)
    asunto = f"Alerta GuardIA — {zona_nombre}"
    contenido_html = (
        f"<p>Se detectó una persona en <strong>{zona_nombre}</strong> "
        f"(cámara <strong>{evento.camara.nombre_para_mostrar}</strong>) fuera del horario permitido.</p>"
        f"<p>Fecha y hora: {momento:%Y-%m-%d %H:%M:%S}</p>"
    )

    adjunto_bytes = None
    adjunto_nombre = None
    if evento.snapshot:
        try:
            evento.snapshot.open("rb")
            adjunto_bytes = evento.snapshot.read()
            adjunto_nombre = evento.snapshot.name.rsplit("/", 1)[-1]
        finally:
            evento.snapshot.close()

    try:
        enviar_correo_brevo(regla.destinatario, asunto, contenido_html, adjunto_bytes, adjunto_nombre)
    except ErrorEnvioCorreo as err:
        logger.error("No se pudo enviar la alerta por correo (evento_id=%s): %s", evento.pk, err)
        evento.notificacion_enviada = False
        evento.notificacion_detalle = str(err)[:255]
    else:
        evento.notificacion_enviada = True
        evento.notificacion_detalle = f"Correo enviado a {regla.destinatario}"[:255]
    evento.save(update_fields=["canal_notificacion", "notificacion_enviada", "notificacion_detalle"])
