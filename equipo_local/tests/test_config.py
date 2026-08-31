import unittest

from equipo_local.config import Config


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
