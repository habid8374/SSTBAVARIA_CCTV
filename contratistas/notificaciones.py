"""Aviso por correo al contratista cuando se aprueba/rechaza una radicación
de seguridad social o una declaración de método — reutiliza el envío de
Brevo ya centralizado en camaras_ia.notificaciones (misma configuración,
mismo remitente; no se duplica nada acá). Un correo que falla nunca rompe
la acción de aprobar/rechazar en sí — solo queda en el log del servidor.
"""

import logging

from camaras_ia.notificaciones import ErrorEnvioCorreo, enviar_correo_brevo

logger = logging.getLogger("contratistas.notificaciones")


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
    """Avisa al correo configurado en ConfiguracionAlertas (Sistema → Reglas
    de contratistas) que una radicación nueva quedó pendiente de revisión —
    a diferencia de notificar_decision_radicacion, este correo se dispara al
    entrar la radicación, no al decidirla."""
    from .models import ConfiguracionAlertas

    destinatario = ConfiguracionAlertas.obtener().correo_revisor
    if not destinatario:
        return

    asunto = f"Nueva radicación pendiente de revisión — {radicacion.trabajador}"
    contenido_html = (
        f"<p>Se radicó seguridad social de <strong>{radicacion.trabajador}</strong> "
        f"({radicacion.mes} {radicacion.anio}) y quedó <strong>pendiente de revisión</strong>.</p>"
    )
    _enviar(destinatario, asunto, contenido_html, contexto=f"radicación pendiente #{radicacion.pk}")


def notificar_declaracion_pendiente(declaracion):
    """Igual que notificar_radicacion_pendiente, pero para una declaración
    de método que se envió a revisión (transición borrador → enviada)."""
    from .models import ConfiguracionAlertas

    destinatario = ConfiguracionAlertas.obtener().correo_revisor
    if not destinatario:
        return

    asunto = f"Nueva declaración de método pendiente de revisión — {declaracion.contratista.nombre}"
    contenido_html = (
        f"<p>La declaración de método &laquo;{declaracion.descripcion_trabajo}&raquo; de "
        f"<strong>{declaracion.contratista.nombre}</strong> quedó <strong>pendiente de revisión</strong>.</p>"
    )
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
