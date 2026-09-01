"""Respaldo diario de toda la base de datos (dumpdata comprimido) al
storage configurado — Cloudflare R2 si está configurado (ver USANDO_R2 en
config/settings.py), disco local si no. Pensado para correr como Cron Job
de Railway a las 2:00 a.m. hora de Bogotá (07:00 UTC) — ver README.md,
sección "Respaldo automático de la base de datos"."""

import gzip
import io
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

DIAS_RETENCION = 30
PREFIJO = "backups/"


class Command(BaseCommand):
    help = "Genera un dump completo de la base de datos (JSON comprimido) y lo sube al storage configurado."

    def handle(self, *args, **options):
        buffer = io.StringIO()
        call_command(
            "dumpdata",
            exclude=["contenttypes", "auth.permission", "sessions.session", "admin.logentry"],
            indent=None,
            stdout=buffer,
        )
        contenido = gzip.compress(buffer.getvalue().encode("utf-8"))

        marca = timezone.localtime(timezone.now()).strftime("%Y-%m-%d_%H-%M-%S")
        nombre = f"{PREFIJO}db_{marca}.json.gz"
        ruta_guardada = default_storage.save(nombre, ContentFile(contenido))
        self.stdout.write(self.style.SUCCESS(f"Respaldo guardado: {ruta_guardada} ({len(contenido)} bytes)"))

        self._eliminar_respaldos_viejos()

    def _eliminar_respaldos_viejos(self):
        """Borra respaldos con más de DIAS_RETENCION días — evita que el
        storage crezca sin límite. No falla el comando si el storage no
        soporta listar (algunos backends no implementan listdir)."""
        limite = timezone.now() - timedelta(days=DIAS_RETENCION)
        try:
            _, archivos = default_storage.listdir(PREFIJO)
        except (NotImplementedError, FileNotFoundError, OSError):
            return

        eliminados = 0
        for nombre in archivos:
            ruta = f"{PREFIJO}{nombre}"
            try:
                modificado = default_storage.get_modified_time(ruta)
            except (NotImplementedError, OSError):
                continue
            if timezone.is_naive(modificado):
                modificado = timezone.make_aware(modificado)
            if modificado < limite:
                default_storage.delete(ruta)
                eliminados += 1
        if eliminados:
            self.stdout.write(f"Respaldos eliminados por antigüedad (> {DIAS_RETENCION} días): {eliminados}")
