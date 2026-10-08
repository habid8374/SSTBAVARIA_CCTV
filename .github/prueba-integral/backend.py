"""Levanta el backend (runserver, sin recarga) igual que en producción pero
anotando cada notificación push en <carpeta>/pushes.jsonl — en la prueba no
hay celulares suscritos, así se puede comprobar a quién y cuándo se avisó.

Uso (desde la raíz del repo): python .github/prueba-integral/backend.py <carpeta_estado>
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

import core.push  # noqa: E402
from django.core.management import call_command  # noqa: E402

registro = Path(sys.argv[1]) / "pushes.jsonl"


def _anotar_push(titulo, cuerpo, url="/dashboard"):
    with registro.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps({"hora": time.time(), "titulo": titulo, "cuerpo": cuerpo}) + "\n")


core.push.enviar_push_a_personal_interno = _anotar_push
call_command("runserver", "127.0.0.1:8000", use_reloader=False)
