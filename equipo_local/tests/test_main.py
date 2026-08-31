import unittest
from unittest.mock import MagicMock

from equipo_local.cliente_api import ErrorApi
from equipo_local.main import SincronizadorCamaras


def _camara(id_, nombre="Cam"):
    return {"id": id_, "nombre": nombre, "rtsp_url": "rtsp://x", "zonas": []}


class SincronizadorCamarasTests(unittest.TestCase):
    def setUp(self):
        self.cliente_api = MagicMock()
        self.fabrica_monitor = MagicMock(side_effect=lambda *args, **kwargs: MagicMock())
        self.sincronizador = SincronizadorCamaras(
            self.cliente_api, detector=MagicMock(), config=MagicMock(), fabrica_monitor=self.fabrica_monitor
        )

    def test_crea_un_monitor_por_cada_camara_nueva(self):
        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1), _camara(2)]}
        self.sincronizador.sincronizar()
        self.assertEqual(set(self.sincronizador.monitores), {1, 2})
        self.assertEqual(self.fabrica_monitor.call_count, 2)
        for monitor in self.sincronizador.monitores.values():
            monitor.iniciar.assert_called_once()

    def test_actualiza_monitores_existentes_en_vez_de_recrearlos(self):
        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1)]}
        self.sincronizador.sincronizar()
        monitor_original = self.sincronizador.monitores[1]

        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1, nombre="Renombrada")]}
        self.sincronizador.sincronizar()

        self.assertIs(self.sincronizador.monitores[1], monitor_original)
        self.assertEqual(self.fabrica_monitor.call_count, 1)  # no se creó de nuevo
        monitor_original.actualizar.assert_called_once_with(_camara(1, nombre="Renombrada"))

    def test_detiene_el_monitor_de_una_camara_que_ya_no_esta_activa(self):
        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1), _camara(2)]}
        self.sincronizador.sincronizar()
        monitor_1 = self.sincronizador.monitores[1]

        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(2)]}
        self.sincronizador.sincronizar()

        self.assertEqual(set(self.sincronizador.monitores), {2})
        monitor_1.detener.assert_called_once()

    def test_error_de_api_no_rompe_ni_borra_los_monitores_existentes(self):
        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1)]}
        self.sincronizador.sincronizar()

        self.cliente_api.obtener_reglas_activas.side_effect = ErrorApi("sin red")
        self.sincronizador.sincronizar()  # no debe lanzar

        self.assertEqual(set(self.sincronizador.monitores), {1})

    def test_detener_todo_detiene_todos_los_monitores_y_limpia_el_estado(self):
        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1), _camara(2)]}
        self.sincronizador.sincronizar()
        monitores = list(self.sincronizador.monitores.values())

        self.sincronizador.detener_todo()

        for monitor in monitores:
            monitor.detener.assert_called_once()
        self.assertEqual(self.sincronizador.monitores, {})


if __name__ == "__main__":
    unittest.main()
