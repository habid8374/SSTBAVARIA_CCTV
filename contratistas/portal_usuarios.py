"""Alta automática del login de portal de una empresa contratista.

Antes, el único camino para que un contratista pudiera entrar al portal
(radicar seguridad social, gestionar su Declaración de Método) era que
alguien de SST se acordara de ir a Usuarios y crearle el acceso a mano.
Ahora se dispara solo al registrar su primer trabajador (ver
TrabajadorSerializer.validate/create en contratistas/serializers.py): si la
empresa contratista todavía no tiene ningún usuario de portal, se crea uno
con contraseña aleatoria y se le envía por correo — igual que el resto de
notificaciones de esta app, si el envío falla no rompe el registro del
trabajador, solo queda en el log del servidor."""

import logging
import secrets

from django.contrib.auth import get_user_model
from django.utils.text import slugify

from camaras_ia.notificaciones import ErrorEnvioCorreo, enviar_correo_brevo
from core.models import PerfilUsuario

logger = logging.getLogger("contratistas.portal_usuarios")

DOMINIO_USUARIOS_PORTAL = "sst-cctv.com"
URL_PORTAL = "https://sst-cctv.com"


def tiene_usuario_portal(contratista):
    return contratista.usuarios_portal.filter(rol=PerfilUsuario.Rol.CONTRATISTA).exists()


def _generar_username(nombre_contratista):
    Usuario = get_user_model()
    base = slugify(nombre_contratista) or "contratista"
    username = f"{base}@{DOMINIO_USUARIOS_PORTAL}"
    sufijo = 2
    while Usuario.objects.filter(username=username).exists():
        username = f"{base}{sufijo}@{DOMINIO_USUARIOS_PORTAL}"
        sufijo += 1
    return username


def crear_usuario_portal_si_hace_falta(contratista):
    """Si `contratista` ya tiene un usuario de portal (rol Contratista), no
    hace nada — evita duplicar el acceso en cada trabajador nuevo. Si no
    tiene, crea uno (usuario tipo nombre-de-la-empresa@sst-cctv.com,
    contraseña aleatoria) y le manda las credenciales por correo a
    contacto_correo. Devuelve el Usuario creado, o None si ya existía."""
    if tiene_usuario_portal(contratista):
        return None

    Usuario = get_user_model()
    username = _generar_username(contratista.nombre)
    contrasena = secrets.token_urlsafe(9)

    usuario = Usuario.objects.create_user(username=username, password=contrasena)
    usuario.perfil.rol = PerfilUsuario.Rol.CONTRATISTA
    usuario.perfil.contratista = contratista
    usuario.perfil.save(update_fields=["rol", "contratista"])

    asunto = f"Acceso al portal SST Bavaria — {contratista.nombre}"
    contenido_html = (
        f"<p>Se creó el acceso al portal de SST Bavaria para <strong>{contratista.nombre}</strong>, "
        "para radicar seguridad social y gestionar la Declaración de Método de sus trabajadores.</p>"
        f"<p><strong>Usuario:</strong> {username}<br>"
        f"<strong>Contraseña:</strong> {contrasena}</p>"
        f"<p><strong>Portal:</strong> <a href=\"{URL_PORTAL}\">{URL_PORTAL}</a></p>"
        "<p>Por seguridad, cambia la contraseña después de tu primer ingreso.</p>"
    )
    try:
        enviar_correo_brevo(contratista.contacto_correo, asunto, contenido_html)
    except ErrorEnvioCorreo as err:
        logger.error(
            "Se creó el usuario de portal %s para la contratista #%s pero no se pudo enviar el correo: %s",
            username,
            contratista.pk,
            err,
        )
    return usuario
