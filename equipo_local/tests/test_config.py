import unittest
from pathlib import Path

from equipo_local.config import Config


class ModeloYoloTests(unittest.TestCase):
    def test_por_defecto_es_ruta_absoluta_dentro_de_equipo_local(self):
        """Nunca un nombre suelto como "yolov8n.pt": si el proceso arranca con la
        carpeta de trabajo en la raíz de un disco (ej. C:\\, como exige rutas.py
        para "-m equipo_local.main"), ultralytics intenta descargar el modelo ahí
        y falla con "Permission denied" — visto en un equipo real."""
        self.assertTrue(Path(Config.MODELO_YOLO).is_absolute())
        self.assertEqual(Path(Config.MODELO_YOLO).name, "yolov8n.pt")
        self.assertEqual(Path(Config.MODELO_YOLO).parent, Path(__file__).resolve().parent.parent)


class ConfigValidarTests(unittest.TestCase):
    def setUp(self):
        self._api_key_original = Config.API_KEY

    def tearDown(self):
        Config.API_KEY = self._api_key_original

    def test_lanza_error_sin_api_key(self):
        Config.API_KEY = ""
        with self.assertRaises(ValueError):
            Config.validar()

    def test_no_lanza_error_con_api_key(self):
        Config.API_KEY = "clave-de-prueba"
        Config.validar()  # no debe lanzar


if __name__ == "__main__":
    unittest.main()
