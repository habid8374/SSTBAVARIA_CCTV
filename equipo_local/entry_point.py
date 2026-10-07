"""Punto de entrada para compilar equipo_local en un .exe con PyInstaller
(ver windows/compilar.bat) — NO se usa para correr normalmente desde código
fuente (para eso: `python -m equipo_local.main`, ver main.py).

PyInstaller necesita un archivo .py como entrada (no admite "-m paquete"
directo), y ese archivo tiene que poder hacer `import equipo_local` como
paquete absoluto — igual que main.py explica para
`python -m equipo_local.main`, hace falta que la carpeta *padre* de
equipo_local/ esté en sys.path. Como este archivo vive dentro de
equipo_local/, se agrega esa carpeta padre a mano antes de importar.
"""

import faulthandler
import multiprocessing
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from equipo_local.main import logger, main  # noqa: E402

if __name__ == "__main__":
    # Obligatorio en un .exe de PyInstaller que use multiprocessing (lo usan
    # dependencias como torch/ultralytics): sin esto, cada proceso auxiliar
    # vuelve a correr el programa entero, que lanza otro auxiliar, y así en
    # cadena — el programa nunca pasaba de "Cargando modelo" como Tarea
    # Programada. Debe ir antes que cualquier otra cosa.
    multiprocessing.freeze_support()

    # Un cierre a nivel nativo (DLL de torch/OpenCV) no pasa por el except
    # de abajo ni deja nada en equipo_local.log: faulthandler deja la pila de
    # Python en este archivo, junto al .exe.
    from equipo_local.rutas import carpeta_base  # noqa: E402

    _archivo_fallos = open(carpeta_base() / "equipo_local_fallos.log", "a", encoding="utf-8")  # noqa: SIM115
    faulthandler.enable(file=_archivo_fallos)
    if os.environ.get("GUARDIA_DIAGNOSTICO"):
        # Para diagnosticar un arranque trabado: cada 40 s, la pila de todos
        # los hilos a la salida de error.
        faulthandler.dump_traceback_later(40, repeat=True, file=sys.stderr)
    # Igual que el bloque final de main.py: corriendo como Tarea Programada
    # sin ventana, un error fatal sin este except no queda en equipo_local.log.
    try:
        main()
    except Exception:
        logger.exception("Error fatal no manejado — el programa se detiene.")
        sys.exit(1)
