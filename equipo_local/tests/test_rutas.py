import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from equipo_local.rutas import carpeta_base


class CarpetaBaseTests(unittest.TestCase):
    def test_sin_compilar_usa_la_carpeta_del_paquete(self):
        self.assertEqual(carpeta_base(), Path(__file__).resolve().parent.parent)

    def test_compilado_usa_la_carpeta_del_exe_no_del_file(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "executable", "/ruta/al/exe/equipo_local.exe"
        ):
            self.assertEqual(carpeta_base(), Path("/ruta/al/exe"))
