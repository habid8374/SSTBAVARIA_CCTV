"""Envío de notificaciones Web Push (VAPID) — la alerta con la app cerrada,
igual que WhatsApp, en vez de depender de tener el dashboard abierto para
enterarse. Sin las 3 variables VAPID_* configuradas, el envío no hace nada
(mismo patrón que camaras_ia.notificaciones sin BREVO_API_KEY): nunca rompe
el flujo que lo dispara — crear una NotificacionInterna o una alerta de
cámara sigue funcionando igual, con o sin push configurado.
"""

import json
import logging

from django.conf import settings

logger = logging.getLogger("core.push")


def _personal_interno():
    from django.contrib.auth import get_user_model

    from .models import PerfilUsuario

    Usuario = get_user_model()
    return Usuario.objects.filter(
        perfil__rol__in=[PerfilUsuario.Rol.ADMINISTRADOR, PerfilUsuario.Rol.OPERADOR]
    )


def enviar_push_a_usuario(usuario, titulo, cuerpo, url="/dashboard"):
    """Manda la notificación a cada dispositivo suscrito de `usuario`. Una
    suscripción que el navegador ya dio de baja (404/410) se borra sola acá
    — así la bandeja de SuscripcionPush no se llena de basura."""
    if not (settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY and settings.VAPID_CLAIMS_EMAIL):
        return

    from pywebpush import WebPushException, webpush

    payload = json.dumps({"titulo": titulo, "cuerpo": cuerpo, "url": url})
    for suscripcion in usuario.suscripciones_push.all():
        try:
            webpush(
                subscription_info={
                    "endpoint": suscripcion.endpoint,
                    "keys": {"p256dh": suscripcion.p256dh, "auth": suscripcion.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
            )
        except WebPushException as err:
            codigo = err.response.status_code if err.response is not None else None
            if codigo in (404, 410):
                suscripcion.delete()
            else:
                logger.error("No se pudo enviar push a %s (%s): %s", usuario, suscripcion.pk, err)


def enviar_push_a_personal_interno(titulo, cuerpo, url="/dashboard"):
    """Igual que enviar_push_a_usuario, pero a todo el personal de
    SST/interventoría (Administrador/Operador) — nunca al portal de
    contratistas, mismo público que ya ve la bandeja de la campanita."""
    if not (settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY and settings.VAPID_CLAIMS_EMAIL):
        return
    for usuario in _personal_interno():
        enviar_push_a_usuario(usuario, titulo, cuerpo, url)
