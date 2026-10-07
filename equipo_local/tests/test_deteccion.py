import sys
import threading
import time
import types
import unittest
from unittest.mock import patch

from equipo_local.deteccion import DetectorPersonas


class _ModeloQueCuentaSimultaneas:
    """Doble del modelo YOLO: registra cuántas predicciones corren a la vez."""

    def __init__(self, _ruta):
        self._lock = threading.Lock()
        self.en_curso = 0
        self.maximo_simultaneas = 0

    def __call__(self, frame, **kwargs):
        with self._lock:
            self.en_curso += 1
            self.maximo_simultaneas = max(self.maximo_simultaneas, self.en_curso)
        time.sleep(0.02)
        with self._lock:
            self.en_curso -= 1
        return []


class DetectorPersonasTests(unittest.TestCase):
    def test_las_camaras_se_turnan_el_modelo(self):
        """Todas las cámaras comparten un solo modelo, cada una desde su hilo:
        un modelo de ultralytics no admite predicciones simultáneas."""
        ultralytics_falso = types.SimpleNamespace(YOLO=_ModeloQueCuentaSimultaneas)
        with patch.dict(sys.modules, {"ultralytics": ultralytics_falso}):
            detector = DetectorPersonas("yolov8n.pt")

        hilos = [threading.Thread(target=detector.detectar, args=(None,)) for _ in range(10)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(detector.modelo.maximo_simultaneas, 1)


if __name__ == "__main__":
    unittest.main()
