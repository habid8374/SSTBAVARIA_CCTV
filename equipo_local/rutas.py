"""Resuelve la carpeta base del programa — la carpeta junto a la cual viven
el `.env`, el log y las grabaciones.

Corriendo desde código fuente (`python -m equipo_local.main`) esa carpeta es
la de este paquete (`Path(__file__).resolve().parent`). Pero compilado con
PyInstaller en modo "onefile" (ver windows/compilar.bat), `__file__` apunta
a la carpeta temporal donde el .exe se descomprime a sí mismo al arrancar
(`sys._MEIPASS`) — una carpeta distinta cada vez y que se borra al cerrar el
programa, así que un `.env`/log/grabaciones ahí desaparecerían. En ese caso
hay que ubicarse junto al .exe real con `sys.executable` en su lugar (ver
PyInstaller docs sobre `sys.frozen`).
"""

import sys
from pathlib import Path


def carpeta_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent
