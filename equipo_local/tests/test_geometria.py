import unittest

from equipo_local.geometria import escalar_punto, punto_en_poligono

CUADRADO = [[0, 0], [10, 0], [10, 10], [0, 10]]


class PuntoEnPoligonoTests(unittest.TestCase):
    def test_punto_dentro(self):
        self.assertTrue(punto_en_poligono((5, 5), CUADRADO))

    def test_punto_fuera(self):
        self.assertFalse(punto_en_poligono((15, 5), CUADRADO))

    def test_poligono_invalido(self):
        self.assertFalse(punto_en_poligono((1, 1), [[0, 0], [1, 1]]))


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
