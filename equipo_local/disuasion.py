"""Activación remota del altavoz/sirena de disuasión de la cámara (luz +
sonido), vía su API HTTP CGI no oficial `coaxialControlIO.cgi`.

⚠️ **NO CONFIRMADO CONTRA HARDWARE REAL** — ver `CLAUDE_CAMARAS.md`,
sección "Pendiente de verificar con hardware real". El datasheet oficial de
la Dahua Picoo B1 (`DH-P3B-PV`) confirma que la cámara tiene luz y sirena de
"disuasión activa" incorporadas, pero Dahua no publica documentación de API
para esa línea de consumo. El endpoint y los parámetros de acá salen de
`coaxialControlIO.cgi`, usado por una integración de Home Assistant de
código abierto ampliamente probada con cámaras Dahua
(github.com/rroller/dahua) — no de documentación oficial. Por eso
`Config.ALTAVOZ_DISUASION_ACTIVO` queda en `False` por defecto: hay que
probar `activar_disuasion()` contra una Picoo B1 real (mismo patrón que se
siguió con RTSP y la calibración: documentar el candidato, confirmarlo en
sitio, recién ahí darlo por bueno) antes de prender el flag en producción.
"""

from __future__ import annotations

import logging

import requests
from requests.auth import HTTPDigestAuth

logger = logging.getLogger("equipo_local.disuasion")

_TIPO_LUZ = 1
_TIPO_SIRENA = 2
_IO_ENCENDER = 1
_IO_APAGAR = 2


def _controlar(ip, usuario, password, tipo, encender, canal=1, timeout=5):
    url = f"http://{ip}/cgi-bin/coaxialControlIO.cgi"
    parametros = {
        "action": "control",
        "channel": canal,
        "info[0].Type": tipo,
        "info[0].IO": _IO_ENCENDER if encender else _IO_APAGAR,
    }
    respuesta = requests.get(url, params=parametros, auth=HTTPDigestAuth(usuario, password), timeout=timeout)
    respuesta.raise_for_status()
    return respuesta.text


def activar_disuasion(ip, usuario, password, canal=1, luz=True, sirena=True, timeout=5):
    """Enciende la sirena y/o la luz de disuasión de la cámara en `ip`,
    autenticando con las mismas credenciales ONVIF que ya tiene registradas
    (`Camara.usuario_onvif`/`password_onvif`). La propia cámara la apaga
    sola a los 10-15 segundos (comportamiento reportado del firmware Dahua),
    así que no hace falta un "apagar" explícito acá."""
    if sirena:
        _controlar(ip, usuario, password, _TIPO_SIRENA, True, canal, timeout)
    if luz:
        _controlar(ip, usuario, password, _TIPO_LUZ, True, canal, timeout)
