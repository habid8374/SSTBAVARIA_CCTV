import unittest
from unittest.mock import MagicMock

from equipo_local.almacenamiento_local import AlmacenamientoLocal
from equipo_local.cliente_api import ErrorApi
from equipo_local.main import SincronizadorCamaras


def _camara(id_, nombre="Cam", zonas=None):
    return {"id": id_, "nombre": nombre, "rtsp_url": "rtsp://x", "zonas": zonas if zonas is not None else []}


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


class SincronizadorCamarasConAlmacenamientoLocalTests(unittest.TestCase):
    """Con `almacenamiento`, las zonas que ve cada monitor son las locales
    (configuradas en el equipo, rol de NVR) — no las que manda la nube."""

    def setUp(self):
        self.cliente_api = MagicMock()
        self.cliente_api.sincronizar_zonas.return_value = {"ids": [], "errores": []}
        self.cliente_api.sincronizar_reglas.return_value = {"ids": [], "errores": []}
        self.fabrica_monitor = MagicMock(side_effect=lambda *args, **kwargs: MagicMock())
        self.almacenamiento = AlmacenamientoLocal(":memory:")
        self.sincronizador = SincronizadorCamaras(
            self.cliente_api, detector=MagicMock(), config=MagicMock(), fabrica_monitor=self.fabrica_monitor,
            almacenamiento=self.almacenamiento,
        )

    def tearDown(self):
        self.almacenamiento.cerrar()

    def test_primera_vez_importa_las_zonas_que_ya_traia_la_nube(self):
        zona_cloud = {"id": 5, "nombre": "Bodega", "tipo": "poligono", "poligono": [[0, 0], [1, 0], [1, 1]],
                      "reglas": []}
        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1, zonas=[zona_cloud])]}
        self.sincronizador.sincronizar()
        camara_datos = self.fabrica_monitor.call_args[0][0]
        self.assertEqual(len(camara_datos["zonas"]), 1)
        self.assertEqual(camara_datos["zonas"][0]["nombre"], "Bodega")
        self.assertEqual(camara_datos["zonas"][0]["cloud_id"], 5)

    def test_zona_configurada_localmente_prevalece_sobre_la_de_la_nube(self):
        self.almacenamiento.crear_zona(1, "Configurada en el equipo", poligono=[[0, 0], [1, 0], [1, 1]])
        zona_cloud = {"id": 5, "nombre": "De la nube (vieja)", "tipo": "poligono",
                      "poligono": [[0, 0], [1, 0], [1, 1]], "reglas": []}
        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1, zonas=[zona_cloud])]}
        self.sincronizador.sincronizar()
        camara_datos = self.fabrica_monitor.call_args[0][0]
        self.assertEqual(len(camara_datos["zonas"]), 1)
        self.assertEqual(camara_datos["zonas"][0]["nombre"], "Configurada en el equipo")

    def test_sincroniza_config_local_pendiente_hacia_la_nube(self):
        self.almacenamiento.crear_zona(1, "Nueva desde el equipo", poligono=[[0, 0], [1, 0], [1, 1]])
        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1)]}
        self.cliente_api.sincronizar_zonas.return_value = {
            "ids": [{"cliente_id": "1", "cloud_id": 77}], "errores": [],
        }
        self.sincronizador.sincronizar()
        self.cliente_api.sincronizar_zonas.assert_called_once()
        zonas = self.almacenamiento.listar_zonas_por_camara(1)
        self.assertEqual(zonas[0]["cloud_id"], 77)

    def test_sin_almacenamiento_se_comporta_como_antes(self):
        sincronizador = SincronizadorCamaras(
            self.cliente_api, detector=MagicMock(), config=MagicMock(), fabrica_monitor=self.fabrica_monitor,
        )
        self.cliente_api.obtener_reglas_activas.return_value = {"camaras": [_camara(1)]}
        sincronizador.sincronizar()
        self.cliente_api.sincronizar_zonas.assert_not_called()


if __name__ == "__main__":
    unittest.main()
