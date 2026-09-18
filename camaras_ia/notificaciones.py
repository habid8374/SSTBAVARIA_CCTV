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


def _encabezado_correo_marca(logo_url):
    return f"""
        <tr>
          <td style="background-color:#111111; padding:28px 32px; text-align:center;">
            <img src="{logo_url}" alt="GuardIA" width="56" height="56" style="display:block; margin:0 auto 12px; border:0;">
            <span style="font-size:22px; font-weight:bold;">
              <span style="color:#ffffff;">Guard</span><span style="color:#fde202;">IA</span>
            </span>
            <div style="color:#a8a8a8; font-size:11px; letter-spacing:0.06em; text-transform:uppercase; margin-top:6px;">
              Seguridad Laboral &middot; CCTV &middot; Inteligencia Artificial
            </div>
          </td>
        </tr>"""


def _envoltura_correo_marca(preheader, tarjeta_html):
    return f"""
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0; padding:0; background-color:#f7f6f1; font-family:Arial, Helvetica, sans-serif;">
  <span style="display:none; font-size:1px; color:#f7f6f1; line-height:1px; max-height:0; max-width:0; opacity:0; overflow:hidden;">
    {preheader}
  </span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f6f1; padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px; width:100%; background-color:#ffffff; border:1px solid #e6e1d0; border-radius:12px; overflow:hidden;">
        {tarjeta_html}
      </table>
      <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px; width:100%; margin-top:20px;">
        <tr><td style="text-align:center; font-size:11px; line-height:1.6; color:#9a9a9a; padding:0 16px;">
          Este es un mensaje automático de GuardIA — Seguridad Laboral + CCTV + Inteligencia Artificial.<br>
          Si usted no esperaba este correo, puede ignorarlo con tranquilidad.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def plantilla_correo_marca(*, preheader, eyebrow, titulo, intro_html, usuario, password, cta_url, cta_label, logo_url, nota_html):
    """HTML de correo con la identidad de marca de GuardIA (negro/amarillo,
    ver frontend/app/globals.css) — encabezado con logo, credenciales de
    acceso destacadas y botón de llamado a la acción. Compartida entre los
    distintos correos de "acceso a la plataforma" (visitantes, portal de
    contratistas) para que todos tengan el mismo diseño formal.

    Maquetado con tablas + estilos en línea, como exige el HTML de correo
    (la mayoría de clientes de correo ignora <style> y flexbox/grid)."""
    tarjeta_html = f"""{_encabezado_correo_marca(logo_url)}
        <tr>
          <td style="padding:36px 32px 8px;">
            <p style="margin:0 0 6px; font-size:11px; letter-spacing:0.08em; text-transform:uppercase; color:#7a5e00; font-weight:bold;">
              {eyebrow}
            </p>
            <h1 style="margin:0 0 20px; font-size:20px; line-height:1.3; color:#111111; font-weight:600;">
              {titulo}
            </h1>
            {intro_html}
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#fef6d8; border:1px solid #fde202; border-radius:8px;">
              <tr><td style="padding:20px 24px;">
                <p style="margin:0 0 12px; font-size:11px; letter-spacing:0.06em; text-transform:uppercase; color:#7a5e00; font-weight:bold;">
                  Credenciales de acceso
                </p>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="padding:4px 0; font-size:13px; color:#5c5c5c; width:100px;">Usuario</td>
                    <td style="padding:4px 0; font-size:14px; color:#111111; font-family:'Courier New', monospace; font-weight:bold;">{usuario}</td>
                  </tr>
                  <tr>
                    <td style="padding:4px 0; font-size:13px; color:#5c5c5c;">Contraseña</td>
                    <td style="padding:4px 0; font-size:14px; color:#111111; font-family:'Courier New', monospace; font-weight:bold;">{password}</td>
                  </tr>
                </table>
              </td></tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 32px; text-align:center;">
            <a href="{cta_url}" style="display:inline-block; background-color:#fde202; color:#111111; text-decoration:none; font-size:14px; font-weight:bold; padding:14px 32px; border-radius:8px;">
              {cta_label}
            </a>
            <p style="margin:16px 0 0; font-size:11px; color:#9a9a9a; word-break:break-all;">
              {cta_url}
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px;">
            <p style="margin:0; font-size:12px; line-height:1.6; color:#7a7a7a; border-top:1px solid #e6e1d0; padding-top:16px;">
              {nota_html}
            </p>
          </td>
        </tr>"""
    return _envoltura_correo_marca(preheader, tarjeta_html)


def plantilla_aviso_marca(*, preheader, eyebrow, titulo, cuerpo_html, logo_url, nota_html=None):
    """Variante de plantilla_correo_marca sin credenciales ni botón de
    acceso — para avisos informativos cuyo dato principal va en el cuerpo o
    en un adjunto (ej. el listado de capacitaciones aprobadas que Sistema
    manda a portería, ver contratistas.views.capacitacion_enviar_aprobados)."""
    nota_bloque = ""
    if nota_html:
        nota_bloque = f"""
        <tr>
          <td style="padding:0 32px 32px;">
            <p style="margin:0; font-size:12px; line-height:1.6; color:#7a7a7a; border-top:1px solid #e6e1d0; padding-top:16px;">
              {nota_html}
            </p>
          </td>
        </tr>"""
    tarjeta_html = f"""{_encabezado_correo_marca(logo_url)}
        <tr>
          <td style="padding:36px 32px 32px;">
            <p style="margin:0 0 6px; font-size:11px; letter-spacing:0.08em; text-transform:uppercase; color:#7a5e00; font-weight:bold;">
              {eyebrow}
            </p>
            <h1 style="margin:0 0 20px; font-size:20px; line-height:1.3; color:#111111; font-weight:600;">
              {titulo}
            </h1>
            {cuerpo_html}
          </td>
        </tr>{nota_bloque}"""
    return _envoltura_correo_marca(preheader, tarjeta_html)


def _credenciales_brevo():
    """La API key y el remitente se pueden digitar desde el dashboard
    (Sistema → Brevo, tabla ConfiguracionNotificaciones) en vez de depender
    de que alguien las configure como variable de entorno en Railway. Si esa
    fila está vacía, se cae de vuelta a settings.BREVO_* (compatibilidad con
    despliegues que sí las manejan por variable de entorno)."""
    from .models import ConfiguracionNotificaciones

    config = ConfiguracionNotificaciones.obtener()
    api_key = config.brevo_api_key or settings.BREVO_API_KEY
    remitente_email = config.brevo_remitente_email or settings.BREVO_REMITENTE_EMAIL
    remitente_nombre = config.brevo_remitente_nombre or settings.BREVO_REMITENTE_NOMBRE
    return api_key, remitente_email, remitente_nombre


def enviar_correo_brevo(destinatario, asunto, contenido_html, adjunto_bytes=None, adjunto_nombre=None):
    """Envía un correo transaccional a `destinatario`. Lanza ErrorEnvioCorreo
    si falta la API key o si Brevo rechaza la solicitud — el llamador decide
    qué hacer con eso (acá no se traga el error silenciosamente)."""
    api_key, remitente_email, remitente_nombre = _credenciales_brevo()
    if not api_key:
        raise ErrorEnvioCorreo("Falta configurar la API key de Brevo (Sistema → Brevo).")

    payload = {
        "sender": {"name": remitente_nombre, "email": remitente_email},
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
