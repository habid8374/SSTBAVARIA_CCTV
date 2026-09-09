import unittest
from unittest.mock import MagicMock, patch

from equipo_local.disuasion import activar_disuasion


class ActivarDisuasionTests(unittest.TestCase):
    @patch("equipo_local.disuasion.requests.get")
    def test_enciende_sirena_y_luz_por_defecto(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text="OK", raise_for_status=lambda: None)

        activar_disuasion("10.0.0.5", "admin", "clave123")

        self.assertEqual(mock_get.call_count, 2)
        llamada_sirena, llamada_luz = mock_get.call_args_list
        self.assertEqual(llamada_sirena.args, ("http://10.0.0.5/cgi-bin/coaxialControlIO.cgi",))
        self.assertEqual(
            llamada_sirena.kwargs["params"],
            {"action": "control", "channel": 1, "info[0].Type": 2, "info[0].IO": 1},
        )
        self.assertEqual(
            llamada_luz.kwargs["params"],
            {"action": "control", "channel": 1, "info[0].Type": 1, "info[0].IO": 1},
        )

    @patch("equipo_local.disuasion.requests.get")
    def test_usa_autenticacion_digest_con_las_credenciales_dadas(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text="OK", raise_for_status=lambda: None)

        activar_disuasion("10.0.0.5", "admin", "clave123")

        auth = mock_get.call_args_list[0].kwargs["auth"]
        self.assertEqual((auth.username, auth.password), ("admin", "clave123"))

    @patch("equipo_local.disuasion.requests.get")
    def test_solo_sirena_no_llama_a_la_luz(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text="OK", raise_for_status=lambda: None)

        activar_disuasion("10.0.0.5", "admin", "clave123", luz=False)

        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs["params"]["info[0].Type"], 2)

    @patch("equipo_local.disuasion.requests.get")
    def test_respeta_el_canal_indicado(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text="OK", raise_for_status=lambda: None)

        activar_disuasion("10.0.0.5", "admin", "clave123", canal=3, luz=False)

        self.assertEqual(mock_get.call_args.kwargs["params"]["channel"], 3)

    @patch("equipo_local.disuasion.requests.get")
    def test_error_http_se_propaga(self, mock_get):
        respuesta = MagicMock(status_code=401)
        respuesta.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_get.return_value = respuesta

        with self.assertRaises(Exception):
            activar_disuasion("10.0.0.5", "admin", "clave-mala", luz=False)


if __name__ == "__main__":
    unittest.main()
