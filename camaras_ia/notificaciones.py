"""Envío de correo transaccional vía la API HTTP de Brevo (antes Sendinblue).

Sin SDK ni dependencias externas — es una sola llamada REST, así que se
implementa con `urllib` (librería estándar) para no agregar un paquete nuevo
solo para esto. Ver https://developers.brevo.com/reference/sendtransacemail
"""

import base64
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger("camaras_ia.notificaciones")

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"
TIMEOUT_SEGUNDOS = 10


class ErrorEnvioCorreo(Exception):
    """El correo no se pudo enviar — falta configuración o Brevo respondió con error."""


def enviar_correo_brevo(destinatario, asunto, contenido_html, adjunto_bytes=None, adjunto_nombre=None):
    """Envía un correo transaccional a `destinatario`. Lanza ErrorEnvioCorreo
    si falta la API key o si Brevo rechaza la solicitud — el llamador decide
    qué hacer con eso (acá no se traga el error silenciosamente)."""
    api_key = settings.BREVO_API_KEY
    if not api_key:
        raise ErrorEnvioCorreo("BREVO_API_KEY no está configurada.")

    payload = {
        "sender": {"name": settings.BREVO_REMITENTE_NOMBRE, "email": settings.BREVO_REMITENTE_EMAIL},
        "to": [{"email": destinatario}],
        "subject": asunto,
        "htmlContent": contenido_html,
    }
    if adjunto_bytes and adjunto_nombre:
        payload["attachment"] = [
            {"content": base64.b64encode(adjunto_bytes).decode("ascii"), "name": adjunto_nombre}
        ]

    request = urllib.request.Request(
        BREVO_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SEGUNDOS) as respuesta:
            if respuesta.status not in (200, 201):
                raise ErrorEnvioCorreo(f"Brevo respondió {respuesta.status}.")
    except urllib.error.HTTPError as err:
        cuerpo = err.read().decode("utf-8", errors="replace")
        raise ErrorEnvioCorreo(f"Brevo respondió {err.code}: {cuerpo}") from err
    except urllib.error.URLError as err:
        raise ErrorEnvioCorreo(f"No se pudo conectar con Brevo: {err.reason}") from err
