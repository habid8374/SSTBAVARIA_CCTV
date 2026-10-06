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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from equipo_local.main import logger, main  # noqa: E402

if __name__ == "__main__":
    # Igual que el bloque final de main.py: corriendo como Tarea Programada
    # sin ventana, un error fatal sin este except no queda en equipo_local.log.
    try:
        main()
    except Exception:
        logger.exception("Error fatal no manejado — el programa se detiene.")
        sys.exit(1)
