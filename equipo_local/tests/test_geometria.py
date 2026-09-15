import unittest

from equipo_local.geometria import escalar_punto, punto_en_circulo, punto_en_poligono, punto_en_zona

CUADRADO = [[0, 0], [10, 0], [10, 10], [0, 10]]


class PuntoEnPoligonoTests(unittest.TestCase):
    def test_punto_dentro(self):
        self.assertTrue(punto_en_poligono((5, 5), CUADRADO))

    def test_punto_fuera(self):
        self.assertFalse(punto_en_poligono((15, 5), CUADRADO))

    def test_poligono_invalido(self):
        self.assertFalse(punto_en_poligono((1, 1), [[0, 0], [1, 1]]))


class PuntoEnCirculoTests(unittest.TestCase):
    def test_punto_dentro(self):
        self.assertTrue(punto_en_circulo((3, 4), (0, 0), 5))

    def test_punto_justo_en_el_borde(self):
        self.assertTrue(punto_en_circulo((5, 0), (0, 0), 5))

    def test_punto_fuera(self):
        self.assertFalse(punto_en_circulo((10, 10), (0, 0), 5))

    def test_radio_none_nunca_contiene_nada(self):
        self.assertFalse(punto_en_circulo((0, 0), (0, 0), None))

    def test_radio_cero_o_negativo_nunca_contiene_nada(self):
        self.assertFalse(punto_en_circulo((0, 0), (0, 0), 0))
        self.assertFalse(punto_en_circulo((0, 0), (0, 0), -1))


class PuntoEnZonaTests(unittest.TestCase):
    def test_tipo_poligono_usa_punto_en_poligono(self):
        zona = {"tipo": "poligono", "poligono": CUADRADO}
        self.assertTrue(punto_en_zona((5, 5), zona))
        self.assertFalse(punto_en_zona((15, 5), zona))

    def test_zona_sin_tipo_se_trata_como_poligono(self):
        zona = {"poligono": CUADRADO}
        self.assertTrue(punto_en_zona((5, 5), zona))

    def test_tipo_punto_radio_dentro_con_camara_calibrada(self):
        zona = {"tipo": "punto_radio", "centro_x": 100, "centro_y": 100, "radio_metros": 3}
        # px_por_metro=10 -> radio de 30px
        self.assertTrue(punto_en_zona((110, 100), zona, px_por_metro=10))

    def test_tipo_punto_radio_fuera_con_camara_calibrada(self):
        zona = {"tipo": "punto_radio", "centro_x": 100, "centro_y": 100, "radio_metros": 3}
        self.assertFalse(punto_en_zona((200, 200), zona, px_por_metro=10))

    def test_tipo_punto_radio_sin_calibrar_nunca_dispara(self):
        zona = {"tipo": "punto_radio", "centro_x": 100, "centro_y": 100, "radio_metros": 3}
        self.assertFalse(punto_en_zona((100, 100), zona, px_por_metro=None))

    def test_tipo_punto_radio_sin_centro_o_radio_nunca_dispara(self):
        zona = {"tipo": "punto_radio", "centro_x": None, "centro_y": None, "radio_metros": None}
        self.assertFalse(punto_en_zona((100, 100), zona, px_por_metro=10))


class EscalarPuntoTests(unittest.TestCase):
    def test_mismo_tamano_no_cambia_el_punto(self):
        self.assertEqual(escalar_punto((50, 25), (100, 100), (100, 100)), (50, 25))

    def test_escala_proporcionalmente(self):
        # Frame RTSP de 640x360 escalado a un snapshot de referencia de 1280x720 (el doble).
        x, y = escalar_punto((320, 180), (640, 360), (1280, 720))
        self.assertEqual((x, y), (640, 360))

    def test_escala_con_relaciones_de_aspecto_distintas(self):
        x, y = escalar_punto((100, 50), (200, 100), (100, 400))
        self.assertEqual((x, y), (50, 200))

    def test_tamano_origen_invalido_lanza_error(self):
        with self.assertRaises(ValueError):
            escalar_punto((1, 1), (0, 100), (100, 100))


if __name__ == "__main__":
    unittest.main()
