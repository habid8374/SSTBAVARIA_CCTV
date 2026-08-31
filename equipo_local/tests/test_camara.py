import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from equipo_local.camara import CamaraMonitor
from equipo_local.config import Config

CUADRADO = [[0, 0], [100, 0], [100, 100], [0, 100]]


def _camara_datos(**overrides):
    base = {
        "id": 1,
        "nombre": "Cam Bodega",
        "rtsp_url": "rtsp://10.0.0.1:554/cam/realmonitor?channel=1&subtype=1",
        "snapshot_referencia": None,
        "zonas": [{"id": 10, "nombre": "Zona Restringida", "poligono": CUADRADO, "reglas": []}],
    }
    base.update(overrides)
    return base


def _config(**overrides):
    class ConfigDePrueba(Config):
        pass

    for clave, valor in overrides.items():
        setattr(ConfigDePrueba, clave, valor)
    return ConfigDePrueba


class EvaluarDeteccionTests(unittest.TestCase):
    def setUp(self):
        self.monitor = CamaraMonitor(
            _camara_datos(), detector=MagicMock(), cliente_api=MagicMock(), config=_config()
        )

    def test_punto_dentro_de_zona_se_reporta(self):
        _, zonas = self.monitor.evaluar_deteccion((50, 50), (100, 100), ahora=0)
        self.assertEqual([z["id"] for z in zonas], [10])

    def test_punto_fuera_de_toda_zona_no_se_reporta(self):
        _, zonas = self.monitor.evaluar_deteccion((500, 500), (100, 100), ahora=0)
        self.assertEqual(zonas, [])

    def test_respeta_cooldown_por_zona(self):
        config = _config(COOLDOWN_ZONA_SEGUNDOS=60)
        monitor = CamaraMonitor(_camara_datos(), MagicMock(), MagicMock(), config)

        _, primero = monitor.evaluar_deteccion((50, 50), (100, 100), ahora=0)
        self.assertEqual(len(primero), 1)

        # Misma zona, 10s después: todavía dentro del cooldown de 60s.
        _, segundo = monitor.evaluar_deteccion((50, 50), (100, 100), ahora=10)
        self.assertEqual(segundo, [])

        # 61s después: ya pasó el cooldown, se puede volver a reportar.
        _, tercero = monitor.evaluar_deteccion((50, 50), (100, 100), ahora=61)
        self.assertEqual(len(tercero), 1)

    def test_escala_el_punto_cuando_hay_referencia_de_otro_tamano(self):
        monitor = CamaraMonitor(
            _camara_datos(snapshot_referencia="http://x/ref.jpg"), MagicMock(), MagicMock(), _config()
        )
        with patch.object(monitor, "_resolver_tamano_referencia", return_value=(200, 200)):
            # Frame de 100x100, punto (25,25) => referencia 200x200, punto escalado (50,50).
            punto_escalado, zonas = monitor.evaluar_deteccion((25, 25), (100, 100), ahora=0)
        self.assertEqual(punto_escalado, (50.0, 50.0))
        self.assertEqual(len(zonas), 1)


class ActualizarTests(unittest.TestCase):
    def test_actualizar_refresca_zonas_sin_perder_cooldown(self):
        monitor = CamaraMonitor(_camara_datos(), MagicMock(), MagicMock(), _config())
        monitor.evaluar_deteccion((50, 50), (100, 100), ahora=0)  # marca cooldown de la zona 10

        nueva_zona = {"id": 20, "nombre": "Zona 2", "poligono": CUADRADO, "reglas": []}
        monitor.actualizar(_camara_datos(zonas=[nueva_zona]))

        self.assertEqual(monitor.zonas, [nueva_zona])
        # El cooldown viejo de la zona 10 sigue en memoria pero ya no aplica a nada (zona nueva).
        _, zonas = monitor.evaluar_deteccion((50, 50), (100, 100), ahora=1)
        self.assertEqual([z["id"] for z in zonas], [20])

    def test_actualizar_invalida_cache_de_referencia_si_cambia_la_url(self):
        monitor = CamaraMonitor(
            _camara_datos(snapshot_referencia="http://x/a.jpg"), MagicMock(), MagicMock(), _config()
        )
        monitor._tamano_referencia = (100, 100)
        monitor.actualizar(_camara_datos(snapshot_referencia="http://x/b.jpg"))
        self.assertIsNone(monitor._tamano_referencia)


class ResolverTamanoReferenciaTests(unittest.TestCase):
    @patch("equipo_local.camara.requests.get")
    def test_descarga_y_mide_la_imagen_de_referencia(self, mock_get):
        imagen = (np.ones((50, 80, 3), dtype=np.uint8) * 255)
        import cv2

        ok, buffer = cv2.imencode(".jpg", imagen)
        self.assertTrue(ok)
        mock_get.return_value = MagicMock(content=buffer.tobytes(), raise_for_status=lambda: None)

        monitor = CamaraMonitor(
            _camara_datos(snapshot_referencia="http://x/ref.jpg"), MagicMock(), MagicMock(), _config()
        )
        self.assertEqual(monitor._resolver_tamano_referencia(), (80, 50))
        # Segunda llamada: debe usar el caché, no volver a pedir la imagen.
        monitor._resolver_tamano_referencia()
        mock_get.assert_called_once()

    def test_sin_snapshot_referencia_devuelve_none(self):
        monitor = CamaraMonitor(
            _camara_datos(snapshot_referencia=None), MagicMock(), MagicMock(), _config()
        )
        self.assertIsNone(monitor._resolver_tamano_referencia())

    @patch("equipo_local.camara.requests.get", side_effect=Exception("timeout"))
    def test_error_de_red_no_rompe_y_devuelve_none(self, mock_get):
        monitor = CamaraMonitor(
            _camara_datos(snapshot_referencia="http://x/ref.jpg"), MagicMock(), MagicMock(), _config()
        )
        self.assertIsNone(monitor._resolver_tamano_referencia())


class ReportarTests(unittest.TestCase):
    def test_reportar_llama_al_cliente_api_con_el_punto_y_el_snapshot(self):
        cliente_api = MagicMock()
        cliente_api.reportar_evento.return_value = {"disparo_alerta": True}
        monitor = CamaraMonitor(_camara_datos(), MagicMock(), cliente_api, _config())

        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        monitor._reportar((5.0, 5.0), frame, {"id": 10, "nombre": "Zona Restringida"}, confianza=0.9)

        cliente_api.reportar_evento.assert_called_once()
        args, _ = cliente_api.reportar_evento.call_args
        self.assertEqual(args[0], 1)  # camara.id
        self.assertEqual(args[1:3], (5.0, 5.0))
        self.assertIsInstance(args[3], (bytes, bytearray))

    def test_reportar_no_propaga_si_el_cliente_api_falla(self):
        cliente_api = MagicMock()
        cliente_api.reportar_evento.side_effect = Exception("red caída")
        monitor = CamaraMonitor(_camara_datos(), MagicMock(), cliente_api, _config())

        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        # No debe lanzar — un evento que no se pudo reportar no debe tumbar el hilo de la cámara.
        monitor._reportar((5.0, 5.0), frame, {"id": 10, "nombre": "Zona Restringida"}, confianza=0.9)


if __name__ == "__main__":
    unittest.main()
