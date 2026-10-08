"""Datos de la prueba integral: una empresa, un administrador, el equipo
local y 10 cámaras (cada una un escenario distinto), con sus zonas, reglas
y alertas de IA. Deja los ids en <carpeta>/ids.json.

Uso (desde la raíz del repo): python .github/prueba-integral/sembrar.py <carpeta_estado>
"""

import json
import os
import sys
from datetime import time
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402

from camaras_ia.models import (  # noqa: E402
    Camara,
    ConfiguracionIA,
    EquipoLocal,
    ReglaAlerta,
    TipoEventoIA,
    ZonaRestringida,
)
from core.models import Empresa, PerfilUsuario  # noqa: E402

SIMULADOR = "http://127.0.0.1:8554"
TODOS_LOS_DIAS = [0, 1, 2, 3, 4, 5, 6]
CUADRO_COMPLETO = [[0, 0], [1280, 0], [1280, 720], [0, 720]]
ESQUINA_SIN_NADIE = [[1180, 0], [1280, 0], [1280, 60], [1180, 60]]

carpeta = Path(sys.argv[1])
carpeta.mkdir(parents=True, exist_ok=True)

empresa = Empresa.objects.create(nombre="Planta de prueba integral")
admin = get_user_model().objects.create_superuser("admin", "admin@prueba.local", "clave-prueba-integral")
perfil, _ = PerfilUsuario.objects.get_or_create(usuario=admin)
perfil.rol = PerfilUsuario.Rol.ADMINISTRADOR
perfil.save()
equipo = EquipoLocal.objects.create(empresa=empresa, nombre="PC planta (prueba)")

config_ia = ConfiguracionIA.obtener()
config_ia.api_key = "sk-ant-prueba-integral"
config_ia.modelo = "claude-opus-5"  # USD 5 / 25 por millón: 1500+60 tokens = USD 0.009 por llamada
config_ia.tope_usd = Decimal("0.06")  # 3 cámaras con IA -> USD 0.02 por cámara: alcanza para 3 llamadas
config_ia.save()

ahora = timezone.localtime()
fuera_inicio = time((ahora.hour + 12) % 24, 0)
fuera_fin = time((ahora.hour + 13) % 24, 0)


def camara(numero, nombre, activa=True, url=None):
    return Camara.objects.create(
        empresa=empresa,
        nombre=nombre,
        ip=f"127.0.0.{numero}",
        rtsp_url=url or f"{SIMULADOR}/cam{numero}.mjpg",
        activa=activa,
    )


def zona(cam, nombre, poligono, regla=None, canal="whatsapp"):
    z = ZonaRestringida.objects.create(camara=cam, nombre=nombre, poligono=poligono)
    if regla:
        inicio, fin = regla
        ReglaAlerta.objects.create(
            zona=z,
            nombre="Horario de prueba",
            hora_inicio=inicio,
            hora_fin=fin,
            dias_semana=TODOS_LOS_DIAS,
            canal_notificacion=canal,
            destinatario="sst@prueba.local" if canal == "correo" else "+573000000000",
        )
    return z


SIEMPRE = (time(0, 0), time(23, 59, 59))

c1 = camara(1, "Cam 1 Casco")
zona(c1, "Zona 1", CUADRO_COMPLETO, SIEMPRE, canal="correo")
c2 = camara(2, "Cam 2 Distancia")
zona(c2, "Zona 2", CUADRO_COMPLETO, SIEMPRE)
c3 = camara(3, "Cam 3 Esquina")
zona(c3, "Esquina vacía", ESQUINA_SIN_NADIE, SIEMPRE)
c4 = camara(4, "Cam 4 Fuera de horario")
zona(c4, "Zona 4", CUADRO_COMPLETO, (fuera_inicio, fuera_fin))
c5 = camara(5, "Cam 5 Vacía")
zona(c5, "Zona 5", CUADRO_COMPLETO, SIEMPRE)
c6 = camara(6, "Cam 6 Inactiva", activa=False)
zona(c6, "Zona 6", CUADRO_COMPLETO, SIEMPRE)
c7 = camara(7, "Cam 7 Sin red", url="http://127.0.0.1:8555/cam7.mjpg")
zona(c7, "Zona 7", CUADRO_COMPLETO, SIEMPRE)
c8 = camara(8, "Cam 8 IA lenta")
zona(c8, "Zona 8", CUADRO_COMPLETO, SIEMPRE)
c9 = camara(9, "Cam 9 Aparece")
zona(c9, "Zona 9", CUADRO_COMPLETO, SIEMPRE)
c10 = camara(10, "Cam 10 Primer plano")
zona(c10, "Zona 10", CUADRO_COMPLETO, SIEMPRE)


def tipo_ia(nombre, descripcion, camaras):
    t = TipoEventoIA.objects.create(
        empresa=empresa, nombre=nombre, descripcion=descripcion, severidad=TipoEventoIA.Severidad.ALTA
    )
    t.camaras.set(camaras)
    return t


t1 = tipo_ia("Sin casco", "Trabajador sin casco [SI]", [c1])
t2 = tipo_ia("Cerca de la máquina", "A menos de 3 metros del equipo [NO]", [c2])
t8 = tipo_ia("Sin chaleco", "Trabajador sin chaleco [SI] [LENTO]", [c8])

ids = {
    "empresa": empresa.pk,
    "equipo": equipo.pk,
    "camaras": {str(n): c.pk for n, c in enumerate([c1, c2, c3, c4, c5, c6, c7, c8, c9, c10], start=1)},
    "tipos_ia": {"1": t1.pk, "2": t2.pk, "8": t8.pk},
    "fuera_de_horario": f"{fuera_inicio:%H:%M}-{fuera_fin:%H:%M}",
}
(carpeta / "ids.json").write_text(json.dumps(ids, indent=2))
print(json.dumps(ids, indent=2))
