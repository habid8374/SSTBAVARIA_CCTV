import unittest
from unittest.mock import MagicMock, patch

import requests

from equipo_local.cliente_api import ClienteApi, ErrorApi


class ClienteApiTests(unittest.TestCase):
    def setUp(self):
        self.cliente = ClienteApi("http://127.0.0.1:8000", "clave-de-prueba")

    @patch("equipo_local.cliente_api.requests.get")
    def test_obtener_reglas_activas_devuelve_json(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: {"camaras": []}, raise_for_status=lambda: None
        )
        resultado = self.cliente.obtener_reglas_activas()
        self.assertEqual(resultado, {"camaras": []})
        mock_get.assert_called_once_with(
            "http://127.0.0.1:8000/api/camaras-ia/reglas-activas/",
            headers={"X-API-Key": "clave-de-prueba"},
            timeout=10,
        )

    @patch("equipo_local.cliente_api.requests.get")
    def test_error_de_red_lanza_error_api(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("sin red")
        with self.assertRaises(ErrorApi):
            self.cliente.obtener_reglas_activas()

    @patch("equipo_local.cliente_api.requests.post")
    def test_reportar_evento_envia_snapshot_como_archivo(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": 1, "disparo_alerta": True},
            raise_for_status=lambda: None,
        )
        resultado = self.cliente.reportar_evento(1, 50.0, 25.0, snapshot_jpeg=b"contenido-jpeg-falso")
        self.assertTrue(resultado["disparo_alerta"])
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"], {"camara": 1, "punto_x": 50.0, "punto_y": 25.0})
        self.assertIn("snapshot", kwargs["files"])

    @patch("equipo_local.cliente_api.requests.post")
    def test_reportar_evento_sin_snapshot(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201, json=lambda: {"id": 1}, raise_for_status=lambda: None
        )
        self.cliente.reportar_evento(1, 10.0, 10.0)
        _, kwargs = mock_post.call_args
        self.assertIsNone(kwargs["files"])

    @patch("equipo_local.cliente_api.requests.post")
    def test_http_error_lanza_error_api(self, mock_post):
        respuesta = requests.Response()
        respuesta.status_code = 401
        mock_post.return_value = respuesta
        with self.assertRaises(ErrorApi):
            self.cliente.reportar_evento(1, 10.0, 10.0)


if __name__ == "__main__":
    unittest.main()
