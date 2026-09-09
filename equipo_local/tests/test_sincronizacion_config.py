import unittest
from unittest.mock import MagicMock

from equipo_local.almacenamiento_local import AlmacenamientoLocal
from equipo_local.sincronizacion_config import (
    importar_configuracion_desde_cloud,
    sincronizar_configuracion_local,
)

CUADRADO = [[0, 0], [1, 0], [1, 1]]


class SincronizarConfiguracionLocalTests(unittest.TestCase):
    def setUp(self):
        self.db = AlmacenamientoLocal(":memory:")
        self.cliente_api = MagicMock()

    def tearDown(self):
        self.db.cerrar()

    def test_sin_nada_pendiente_no_llama_a_la_api(self):
        sincronizar_configuracion_local(self.db, self.cliente_api)
        self.cliente_api.sincronizar_zonas.assert_not_called()
        self.cliente_api.sincronizar_reglas.assert_not_called()

    def test_zona_nueva_se_sube_y_guarda_el_cloud_id(self):
        zona_id = self.db.crear_zona(1, "Bodega", poligono=CUADRADO)
        self.cliente_api.sincronizar_zonas.return_value = {
            "ids": [{"cliente_id": str(zona_id), "cloud_id": 42}], "errores": [],
        }
        sincronizar_configuracion_local(self.db, self.cliente_api)
        self.cliente_api.sincronizar_zonas.assert_called_once()
        zona = self.db.obtener_zona(zona_id)
        self.assertEqual(zona["cloud_id"], 42)
        self.assertEqual(self.db.zonas_pendientes_de_sincronizar(), [])

    def test_zona_eliminada_se_reporta_y_se_borra_localmente_al_confirmar(self):
        zona_id = self.db.crear_zona(1, "Bodega", poligono=CUADRADO)
        self.db.marcar_zona_sincronizada(zona_id, cloud_id=42)
        self.db.eliminar_zona(zona_id)
        self.cliente_api.sincronizar_zonas.return_value = {"ids": [], "errores": []}
        sincronizar_configuracion_local(self.db, self.cliente_api)
        self.cliente_api.sincronizar_zonas.assert_called_once_with([], eliminar=[42])
        self.assertEqual(self.db.zonas_pendientes_de_eliminar(), [])

    def test_regla_espera_a_que_su_zona_tenga_cloud_id(self):
        zona_id = self.db.crear_zona(1, "Bodega", poligono=CUADRADO)
        self.db.crear_regla(zona_id, "08:00:00", "17:00:00", dias_semana=[0])
        # La zona todavía no está sincronizada (no se le da cloud_id en la respuesta).
        self.cliente_api.sincronizar_zonas.return_value = {"ids": [], "errores": []}
        sincronizar_configuracion_local(self.db, self.cliente_api)
        self.cliente_api.sincronizar_reglas.assert_not_called()

    def test_regla_se_sube_una_vez_su_zona_tiene_cloud_id(self):
        zona_id = self.db.crear_zona(1, "Bodega", poligono=CUADRADO)
        regla_id = self.db.crear_regla(zona_id, "08:00:00", "17:00:00", dias_semana=[0], destinatario="x@y.com")
        self.cliente_api.sincronizar_zonas.return_value = {
            "ids": [{"cliente_id": str(zona_id), "cloud_id": 42}], "errores": [],
        }
        self.cliente_api.sincronizar_reglas.return_value = {
            "ids": [{"cliente_id": str(regla_id), "cloud_id": 99}], "errores": [],
        }
        sincronizar_configuracion_local(self.db, self.cliente_api)
        llamada = self.cliente_api.sincronizar_reglas.call_args
        self.assertEqual(llamada.args[0][0]["zona"], 42)
        regla = self.db.obtener_regla(regla_id)
        self.assertEqual(regla["cloud_id"], 99)

    def test_error_al_sincronizar_no_rompe_el_ciclo(self):
        self.db.crear_zona(1, "Bodega", poligono=CUADRADO)
        self.cliente_api.sincronizar_zonas.side_effect = Exception("sin red")
        sincronizar_configuracion_local(self.db, self.cliente_api)  # no debe lanzar


class ImportarConfiguracionDesdeCloudTests(unittest.TestCase):
    def setUp(self):
        self.db = AlmacenamientoLocal(":memory:")

    def tearDown(self):
        self.db.cerrar()

    def test_importa_zonas_y_reglas_si_no_hay_nada_local(self):
        zonas_cloud = [
            {
                "id": 5, "nombre": "Bodega", "tipo": "poligono", "poligono": CUADRADO,
                "centro_x": None, "centro_y": None, "radio_metros": None,
                "reglas": [
                    {"id": 9, "hora_inicio": "22:00:00", "hora_fin": "06:00:00", "dias_semana": [0, 1],
                     "canal_notificacion": "correo", "destinatario": "x@y.com", "nombre": ""},
                ],
            }
        ]
        importar_configuracion_desde_cloud(self.db, camara_id=1, zonas_cloud=zonas_cloud)
        zonas = self.db.listar_zonas_por_camara(1)
        self.assertEqual(len(zonas), 1)
        self.assertEqual(zonas[0]["cloud_id"], 5)
        self.assertEqual(len(zonas[0]["reglas"]), 1)
        self.assertEqual(zonas[0]["reglas"][0]["cloud_id"], 9)
        # Ya sincronizada, no queda pendiente de subir de nuevo.
        self.assertEqual(self.db.zonas_pendientes_de_sincronizar(), [])
        self.assertEqual(self.db.reglas_pendientes_de_sincronizar(), [])

    def test_no_importa_si_ya_hay_zonas_locales(self):
        self.db.crear_zona(1, "Ya configurada a mano", poligono=CUADRADO)
        importar_configuracion_desde_cloud(
            self.db, camara_id=1,
            zonas_cloud=[{"id": 5, "nombre": "De la nube", "tipo": "poligono", "poligono": CUADRADO, "reglas": []}],
        )
        zonas = self.db.listar_zonas_por_camara(1)
        self.assertEqual(len(zonas), 1)
        self.assertEqual(zonas[0]["nombre"], "Ya configurada a mano")


if __name__ == "__main__":
    unittest.main()
