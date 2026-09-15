"""Aviso al contratista (por correo) y al personal de SST/interventoría (por
correo y por la bandeja propia de la app) cuando pasa algo en una radicación
de seguridad social o una declaración de método. El correo reutiliza el
envío de Brevo ya centralizado en camaras_ia.notificaciones (misma
configuración, mismo remitente; no se duplica nada acá) — si falla, nunca
rompe la acción en sí, solo queda en el log del servidor. La notificación
interna (NotificacionInterna) es la bandeja compartida del dashboard: no
depende de Brevo ni de revisar el correo, para que no se pierda un aviso de
"esto hay que revisarlo" entre el resto del inbox.
"""

import logging

from camaras_ia.notificaciones import ErrorEnvioCorreo, enviar_correo_brevo

logger = logging.getLogger("contratistas.notificaciones")


def _crear_notificacion_interna(tipo, mensaje, instancia):
    from core.push import enviar_push_a_personal_interno

    from .models import NotificacionInterna

    NotificacionInterna.objects.create(
        tipo=tipo,
        mensaje=mensaje,
        modelo=instancia.__class__.__name__,
        objeto_id=instancia.pk,
    )
    seccion = "contratistas" if tipo == NotificacionInterna.Tipo.RADICACION_PENDIENTE else "declaracion-metodo"
    enviar_push_a_personal_interno("SST Bavaria — pendiente por revisar", mensaje, url=f"/dashboard?ir={seccion}")


def notificar_decision_radicacion(radicacion):
    destinatario = radicacion.trabajador.contratista.contacto_correo
    if not destinatario:
        return

    aprobada = radicacion.estado == radicacion.Estado.APROBADA
    palabra = "aprobada" if aprobada else "rechazada"
    asunto = f"Radicación de seguridad social {palabra} — {radicacion.trabajador}"
    contenido_html = (
        f"<p>La radicación de seguridad social de <strong>{radicacion.trabajador}</strong> "
        f"({radicacion.mes} {radicacion.anio}) fue <strong>{palabra}</strong>.</p>"
    )
    if radicacion.observaciones:
        contenido_html += f"<p>Observaciones: {radicacion.observaciones}</p>"

    _enviar(destinatario, asunto, contenido_html, contexto=f"radicación #{radicacion.pk}")


def notificar_radicacion_pendiente(radicacion):
    """Avisa que una radicación nueva quedó pendiente de revisión — a
    diferencia de notificar_decision_radicacion, esto se dispara al entrar
    la radicación, no al decidirla. Dos canales, independientes entre sí:
    correo al `correo_revisor` (si está configurado) y una notificación en
    la bandeja propia de la app (siempre, no depende del correo)."""
    from .models import ConfiguracionAlertas, NotificacionInterna

    mensaje = (
        f"Se radicó seguridad social de {radicacion.trabajador} "
        f"({radicacion.mes} {radicacion.anio}) y quedó pendiente de revisión."
    )
    _crear_notificacion_interna(NotificacionInterna.Tipo.RADICACION_PENDIENTE, mensaje, radicacion)

    destinatario = ConfiguracionAlertas.obtener().correo_revisor
    if not destinatario:
        return
    asunto = f"Nueva radicación pendiente de revisión — {radicacion.trabajador}"
    contenido_html = f"<p>{mensaje}</p>"
    _enviar(destinatario, asunto, contenido_html, contexto=f"radicación pendiente #{radicacion.pk}")


def notificar_declaracion_pendiente(declaracion, es_subsanacion=False):
    """Igual que notificar_radicacion_pendiente, pero para una declaración
    de método que se envió a revisión — ya sea la primera vez (borrador →
    enviada) o una corrección reenviada tras un rechazo (rechazada →
    enviada, es_subsanacion=True). El asunto del correo y el tipo de la
    notificación interna distinguen un caso del otro, para que quien revisa
    sepa de un vistazo si es algo nuevo o algo que ya había rechazado."""
    from .models import ConfiguracionAlertas, NotificacionInterna

    if es_subsanacion:
        tipo = NotificacionInterna.Tipo.DECLARACION_SUBSANADA
        verbo = "fue corregida y reenviada a revisión"
        asunto_prefijo = "Declaración corregida y reenviada"
    else:
        tipo = NotificacionInterna.Tipo.DECLARACION_PENDIENTE
        verbo = "quedó pendiente de revisión"
        asunto_prefijo = "Nueva declaración de método pendiente de revisión"

    mensaje = (
        f"La declaración de método «{declaracion.descripcion_trabajo}» de "
        f"{declaracion.contratista.nombre} {verbo}."
    )
    _crear_notificacion_interna(tipo, mensaje, declaracion)

    destinatario = ConfiguracionAlertas.obtener().correo_revisor
    if not destinatario:
        return
    asunto = f"{asunto_prefijo} — {declaracion.contratista.nombre}"
    contenido_html = f"<p>{mensaje}</p>"
    _enviar(destinatario, asunto, contenido_html, contexto=f"declaración pendiente #{declaracion.pk}")


def notificar_decision_declaracion(declaracion):
    destinatario = declaracion.contratista.contacto_correo
    if not destinatario:
        return

    aprobada = declaracion.estado == declaracion.Estado.APROBADA
    palabra = "aprobada" if aprobada else "rechazada"
    asunto = f"Declaración de método {palabra} — {declaracion.descripcion_trabajo[:60]}"
    contenido_html = (
        f"<p>La declaración de método &laquo;{declaracion.descripcion_trabajo}&raquo; "
        f"fue <strong>{palabra}</strong>.</p>"
    )
    if declaracion.observaciones:
        contenido_html += f"<p>Observaciones: {declaracion.observaciones}</p>"

    _enviar(destinatario, asunto, contenido_html, contexto=f"declaración #{declaracion.pk}")


def _enviar(destinatario, asunto, contenido_html, contexto):
    try:
        enviar_correo_brevo(destinatario, asunto, contenido_html)
    except ErrorEnvioCorreo as err:
        logger.error("No se pudo notificar la decisión de %s a %s: %s", contexto, destinatario, err)
