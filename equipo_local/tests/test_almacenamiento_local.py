import unittest

from equipo_local.almacenamiento_local import AlmacenamientoLocal


class AlmacenamientoLocalTests(unittest.TestCase):
    def setUp(self):
        self.db = AlmacenamientoLocal(":memory:")

    def tearDown(self):
        self.db.cerrar()

    def test_crear_y_listar_zona_poligono(self):
        zona_id = self.db.crear_zona(1, "Estiba", poligono=[[0, 0], [10, 0], [10, 10]])
        zonas = self.db.listar_zonas_por_camara(1)
        self.assertEqual(len(zonas), 1)
        self.assertEqual(zonas[0]["id"], zona_id)
        self.assertEqual(zonas[0]["nombre"], "Estiba")
        self.assertEqual(zonas[0]["poligono"], [[0, 0], [10, 0], [10, 10]])
        self.assertEqual(zonas[0]["reglas"], [])

    def test_listar_zonas_no_incluye_otra_camara(self):
        self.db.crear_zona(1, "Zona cámara 1", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.crear_zona(2, "Zona cámara 2", poligono=[[0, 0], [1, 0], [1, 1]])
        self.assertEqual(len(self.db.listar_zonas_por_camara(1)), 1)
        self.assertEqual(len(self.db.listar_zonas_por_camara(2)), 1)

    def test_listar_zonas_excluye_inactivas(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.actualizar_zona(zona_id, activa=False)
        self.assertEqual(self.db.listar_zonas_por_camara(1), [])

    def test_actualizar_zona(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.actualizar_zona(zona_id, nombre="Renombrada", poligono=[[5, 5], [6, 5], [6, 6]])
        zona = self.db.obtener_zona(zona_id)
        self.assertEqual(zona["nombre"], "Renombrada")
        self.assertEqual(zona["poligono"], [[5, 5], [6, 5], [6, 6]])

    def test_eliminar_zona_nunca_sincronizada_la_borra_de_una(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.eliminar_zona(zona_id)
        self.assertIsNone(self.db.obtener_zona(zona_id))
        self.assertEqual(self.db.zonas_pendientes_de_eliminar(), [])

    def test_eliminar_zona_ya_sincronizada_queda_pendiente_de_avisar(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.marcar_zona_sincronizada(zona_id, cloud_id=99)
        self.db.eliminar_zona(zona_id)
        self.assertIsNone(self.db.obtener_zona(zona_id))
        pendientes = self.db.zonas_pendientes_de_eliminar()
        self.assertEqual(len(pendientes), 1)
        self.assertEqual(pendientes[0]["cloud_id"], 99)
        self.db.confirmar_eliminacion_zona(zona_id)
        self.assertEqual(self.db.zonas_pendientes_de_eliminar(), [])

    def test_zona_nueva_queda_pendiente_de_sincronizar(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        pendientes = self.db.zonas_pendientes_de_sincronizar()
        self.assertEqual([z["id"] for z in pendientes], [zona_id])

    def test_zona_sincronizada_deja_de_estar_pendiente(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.marcar_zona_sincronizada(zona_id, cloud_id=7)
        self.assertEqual(self.db.zonas_pendientes_de_sincronizar(), [])
        zona = self.db.obtener_zona(zona_id)
        self.assertEqual(zona["cloud_id"], 7)

    def test_editar_zona_ya_sincronizada_la_vuelve_a_marcar_pendiente(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.marcar_zona_sincronizada(zona_id, cloud_id=7)
        self.db.actualizar_zona(zona_id, nombre="Cambiada")
        pendientes = self.db.zonas_pendientes_de_sincronizar()
        self.assertEqual([z["id"] for z in pendientes], [zona_id])

    def test_importar_zona_desde_cloud_no_queda_pendiente(self):
        zona_id = self.db.importar_zona_desde_cloud(
            1, cloud_id=42, nombre="Existente", tipo="poligono",
            poligono=[[0, 0], [1, 0], [1, 1]], centro_x=None, centro_y=None, radio_metros=None, activa=True,
        )
        self.assertEqual(self.db.zonas_pendientes_de_sincronizar(), [])
        zona = self.db.obtener_zona(zona_id)
        self.assertEqual(zona["cloud_id"], 42)

    def test_listar_zonas_incluir_inactivas_las_muestra(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.actualizar_zona(zona_id, activa=False)
        zonas = self.db.listar_zonas_por_camara(1, incluir_inactivas=True)
        self.assertEqual(len(zonas), 1)
        self.assertFalse(zonas[0]["activa"])

    def test_tiene_zonas(self):
        self.assertFalse(self.db.tiene_zonas(1))
        self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.assertTrue(self.db.tiene_zonas(1))

    # --- Reglas ---

    def test_crear_y_listar_regla(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        regla_id = self.db.crear_regla(
            zona_id, "22:00:00", "06:00:00", dias_semana=[0, 1, 2], canal_notificacion="correo",
            destinatario="x@y.com",
        )
        reglas = self.db.listar_reglas_por_zona(zona_id)
        self.assertEqual(len(reglas), 1)
        self.assertEqual(reglas[0]["id"], regla_id)
        self.assertEqual(reglas[0]["dias_semana"], [0, 1, 2])
        self.assertEqual(reglas[0]["destinatario"], "x@y.com")

    def test_zonas_incluyen_sus_reglas_anidadas(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.crear_regla(zona_id, "08:00:00", "17:00:00", dias_semana=[0])
        zonas = self.db.listar_zonas_por_camara(1)
        self.assertEqual(len(zonas[0]["reglas"]), 1)

    def test_listar_reglas_excluye_inactivas_si_se_pide(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        regla_id = self.db.crear_regla(zona_id, "08:00:00", "17:00:00", dias_semana=[0])
        self.db.actualizar_regla(regla_id, activa=False)
        self.assertEqual(self.db.listar_reglas_por_zona(zona_id, solo_activas=True), [])
        self.assertEqual(len(self.db.listar_reglas_por_zona(zona_id)), 1)

    def test_eliminar_regla_ya_sincronizada_queda_pendiente_de_avisar(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        regla_id = self.db.crear_regla(zona_id, "08:00:00", "17:00:00", dias_semana=[0])
        self.db.marcar_regla_sincronizada(regla_id, cloud_id=5)
        self.db.eliminar_regla(regla_id)
        pendientes = self.db.reglas_pendientes_de_eliminar()
        self.assertEqual([r["cloud_id"] for r in pendientes], [5])
        self.db.confirmar_eliminacion_regla(regla_id)
        self.assertEqual(self.db.reglas_pendientes_de_eliminar(), [])

    def test_eliminar_zona_en_cascada_borra_sus_reglas(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        self.db.crear_regla(zona_id, "08:00:00", "17:00:00", dias_semana=[0])
        self.db.eliminar_zona(zona_id)  # nunca sincronizada -> borrado directo, dispara ON DELETE CASCADE
        self.assertEqual(self.db.listar_reglas_por_zona(zona_id), [])

    def test_regla_nueva_queda_pendiente_de_sincronizar(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=[[0, 0], [1, 0], [1, 1]])
        regla_id = self.db.crear_regla(zona_id, "08:00:00", "17:00:00", dias_semana=[0])
        pendientes = self.db.reglas_pendientes_de_sincronizar()
        self.assertEqual([r["id"] for r in pendientes], [regla_id])


if __name__ == "__main__":
    unittest.main()
