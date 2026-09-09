import unittest
from unittest.mock import MagicMock

from equipo_local.almacenamiento_local import AlmacenamientoLocal
from equipo_local.visor_web import crear_app

CUADRADO = [[0, 0], [1, 0], [1, 1]]


class _ConfigDePrueba:
    def __init__(self):
        self.GRABACIONES_DIR = "/no/existe"
        self.VISOR_WEB_USUARIO = ""
        self.VISOR_WEB_PASSWORD = ""
        self.VISOR_WEB_HOST = "127.0.0.1"
        self.VISOR_WEB_PUERTO = 8090


def _sincronizador(almacenamiento=None, monitores=None):
    sincronizador = MagicMock()
    sincronizador.monitores = monitores or {}
    sincronizador.almacenamiento = almacenamiento
    return sincronizador


class ApiConfigZonasTests(unittest.TestCase):
    def setUp(self):
        self.db = AlmacenamientoLocal(":memory:")
        self.app = crear_app(_sincronizador(self.db), _ConfigDePrueba())
        self.cliente = self.app.test_client()

    def tearDown(self):
        self.db.cerrar()

    def test_sin_almacenamiento_devuelve_404(self):
        app = crear_app(_sincronizador(None), _ConfigDePrueba())
        resp = app.test_client().get("/api/config/camaras/1/zonas")
        self.assertEqual(resp.status_code, 404)

    def test_listar_zonas_vacio(self):
        resp = self.cliente.get("/api/config/camaras/1/zonas")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])

    def test_crear_zona_poligono(self):
        resp = self.cliente.post(
            "/api/config/camaras/1/zonas",
            json={"nombre": "Bodega", "tipo": "poligono", "poligono": CUADRADO, "activa": True},
        )
        self.assertEqual(resp.status_code, 201)
        datos = resp.get_json()
        self.assertEqual(datos["nombre"], "Bodega")
        self.assertIsNone(datos["cloud_id"])
        zonas = self.cliente.get("/api/config/camaras/1/zonas").get_json()
        self.assertEqual(len(zonas), 1)

    def test_crear_zona_sin_nombre_falla(self):
        resp = self.cliente.post(
            "/api/config/camaras/1/zonas",
            json={"nombre": "", "tipo": "poligono", "poligono": CUADRADO},
        )
        self.assertEqual(resp.status_code, 400)

    def test_crear_zona_poligono_con_menos_de_3_puntos_falla(self):
        resp = self.cliente.post(
            "/api/config/camaras/1/zonas",
            json={"nombre": "X", "tipo": "poligono", "poligono": [[0, 0], [1, 1]]},
        )
        self.assertEqual(resp.status_code, 400)

    def test_actualizar_zona(self):
        zona_id = self.db.crear_zona(1, "Vieja", poligono=CUADRADO)
        resp = self.cliente.put(f"/api/config/zonas/{zona_id}", json={"nombre": "Nueva"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["nombre"], "Nueva")

    def test_actualizar_zona_inexistente_devuelve_404(self):
        resp = self.cliente.put("/api/config/zonas/999", json={"nombre": "X"})
        self.assertEqual(resp.status_code, 404)

    def test_eliminar_zona(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=CUADRADO)
        resp = self.cliente.delete(f"/api/config/zonas/{zona_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(self.db.obtener_zona(zona_id))

    def test_crear_regla(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=CUADRADO)
        resp = self.cliente.post(
            f"/api/config/zonas/{zona_id}/reglas",
            json={"hora_inicio": "22:00:00", "hora_fin": "06:00:00", "dias_semana": [0, 1],
                  "canal_notificacion": "correo", "destinatario": "x@y.com"},
        )
        self.assertEqual(resp.status_code, 201)
        zonas = self.cliente.get("/api/config/camaras/1/zonas").get_json()
        self.assertEqual(len(zonas[0]["reglas"]), 1)

    def test_crear_regla_sin_destinatario_falla(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=CUADRADO)
        resp = self.cliente.post(
            f"/api/config/zonas/{zona_id}/reglas",
            json={"hora_inicio": "22:00:00", "hora_fin": "06:00:00", "dias_semana": [0], "destinatario": ""},
        )
        self.assertEqual(resp.status_code, 400)

    def test_eliminar_regla(self):
        zona_id = self.db.crear_zona(1, "Z", poligono=CUADRADO)
        regla_id = self.db.crear_regla(zona_id, "08:00:00", "17:00:00", dias_semana=[0], destinatario="x@y.com")
        resp = self.cliente.delete(f"/api/config/reglas/{regla_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(self.db.obtener_regla(regla_id))

    def test_sincronizar_llama_al_cliente_api(self):
        sinc = _sincronizador(self.db)
        sinc.cliente_api.sincronizar_zonas.return_value = {"ids": [], "errores": []}
        app = crear_app(sinc, _ConfigDePrueba())
        self.db.crear_zona(1, "Z", poligono=CUADRADO)
        resp = app.test_client().post("/api/config/sincronizar")
        self.assertEqual(resp.status_code, 200)
        sinc.cliente_api.sincronizar_zonas.assert_called_once()


class ApiFrameTests(unittest.TestCase):
    def test_frame_inexistente_devuelve_404(self):
        app = crear_app(_sincronizador(monitores={}), _ConfigDePrueba())
        resp = app.test_client().get("/api/camaras/1/frame.jpg")
        self.assertEqual(resp.status_code, 404)

    def test_frame_devuelve_el_ultimo_jpeg_del_monitor(self):
        monitor = MagicMock()
        monitor.obtener_ultimo_frame_jpeg.return_value = b"jpegdata"
        app = crear_app(_sincronizador(monitores={1: monitor}), _ConfigDePrueba())
        resp = app.test_client().get("/api/camaras/1/frame.jpg")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, b"jpegdata")
        self.assertEqual(resp.mimetype, "image/jpeg")


class PaginasConfigurarTests(unittest.TestCase):
    def test_pagina_index_responde(self):
        app = crear_app(_sincronizador(), _ConfigDePrueba())
        resp = app.test_client().get("/configurar")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Configurar zonas", resp.data)

    def test_pagina_camara_responde_con_id_inyectado(self):
        app = crear_app(_sincronizador(), _ConfigDePrueba())
        resp = app.test_client().get("/configurar/7")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"CAMARA_ID = 7", resp.data)


if __name__ == "__main__":
    unittest.main()
