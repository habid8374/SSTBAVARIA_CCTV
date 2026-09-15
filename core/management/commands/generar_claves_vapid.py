import base64

from django.core.management.base import BaseCommand
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization


class Command(BaseCommand):
    help = (
        "Genera un par de llaves VAPID nuevo para las notificaciones push. "
        "Copia la salida a las variables de entorno VAPID_PUBLIC_KEY y "
        "VAPID_PRIVATE_KEY (Railway y .env local) — VAPID_CLAIMS_EMAIL es "
        "un correo de contacto tuyo, no una llave, se pone a mano."
    )

    def handle(self, *args, **options):
        vapid = Vapid()
        vapid.generate_keys()

        clave_privada = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
        clave_publica = vapid.public_key.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )

        self.stdout.write("VAPID_PUBLIC_KEY=" + base64.urlsafe_b64encode(clave_publica).rstrip(b"=").decode())
        self.stdout.write("VAPID_PRIVATE_KEY=" + base64.urlsafe_b64encode(clave_privada).rstrip(b"=").decode())
