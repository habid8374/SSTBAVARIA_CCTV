import itertools
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from equipo_local.visor_web import crear_app, generar_stream_mjpeg


class GenerarStreamMjpegTests(unittest.TestCase):
    def test_produce_partes_multipart_con_el_frame(self):
        partes = list(
            itertools.islice(
                generar_stream_mjpeg(lambda: b"jpegdata", dormir=lambda s: None),
                2,
            )
        )
        self.assertEqual(len(partes), 2)
        for parte in partes:
            self.assertIn(b"--frame", parte)
            self.assertIn(b"image/jpeg", parte)
            self.assertIn(b"jpegdata", parte)

    def test_se_corta_solo_si_nunca_aparece_el_primer_frame(self):
        dormidas = []
        partes = list(
            generar_stream_mjpeg(
                lambda: None,
                intervalo_segundos=0.5,
                limite_espera_segundos=1,
                dormir=dormidas.append,
            )
        )
        self.assertEqual(partes, [])
        self.assertTrue(len(dormidas) >= 2)

    def test_reinicia_la_espera_cuando_vuelve_a_aparecer_un_frame(self):
        secuencia = iter([None, b"jpegdata", None, None, None])

        def obtener():
            return next(secuencia, None)

        partes = list(
            itertools.islice(
                generar_stream_mjpeg(obtener, intervalo_segundos=0.1, limite_espera_segundos=100, dormir=lambda s: None),
                1,
            )
        )
        self.assertEqual(len(partes), 1)
        self.assertIn(b"jpegdata", partes[0])


class _ConfigDePrueba:
    def __init__(self, base_dir, usuario="", password=""):
        self.GRABACIONES_DIR = base_dir
        self.VISOR_WEB_USUARIO = usuario
        self.VISOR_WEB_PASSWORD = password
        self.VISOR_WEB_HOST = "127.0.0.1"
        self.VISOR_WEB_PUERTO = 8090


def _sincronizador(monitores=None):
    sincronizador = MagicMock()
    sincronizador.monitores = monitores or {}
    return sincronizador


class ApiCamarasTests(unittest.TestCase):
    def test_lista_las_camaras_activas(self):
        monitor = MagicMock(id=1, nombre="Cam Bodega")
        app = crear_app(_sincronizador({1: monitor}), _ConfigDePrueba("/no/existe"))
        cliente = app.test_client()
        respuesta = cliente.get("/api/camaras")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json(), [{"id": 1, "nombre": "Cam Bodega"}])

    def test_sin_camaras_devuelve_lista_vacia(self):
        app = crear_app(_sincronizador(), _ConfigDePrueba("/no/existe"))
        respuesta = app.test_client().get("/api/camaras")
        self.assertEqual(respuesta.get_json(), [])


class VivoTests(unittest.TestCase):
    def test_camara_inexistente_devuelve_404(self):
        app = crear_app(_sincronizador(), _ConfigDePrueba("/no/existe"))
        respuesta = app.test_client().get("/vivo/99")
        self.assertEqual(respuesta.status_code, 404)

    def test_camara_existente_devuelve_multipart(self):
        monitor = MagicMock(id=1, nombre="Cam Bodega")
        app = crear_app(_sincronizador({1: monitor}), _ConfigDePrueba("/no/existe"))
        respuesta = app.test_client().get("/vivo/1", buffered=False)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("multipart/x-mixed-replace", respuesta.headers["Content-Type"])
        respuesta.close()  # no se consume el body: es un generador potencialmente infinito


class ApiGrabacionesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.addCleanup(self._tmp.cleanup)
        self.app = crear_app(_sincronizador(), _ConfigDePrueba(self.base))
        self.cliente = self.app.test_client()

    def _tocar(self, camara_id, fecha, archivo, contenido=b"abc"):
        ruta = Path(self.base) / str(camara_id) / fecha / archivo
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
        return ruta

    def test_lista_grabaciones_existentes(self):
        self._tocar(1, "2026-03-05", "10-00-00.mp4")
        respuesta = self.cliente.get("/api/grabaciones")
        datos = respuesta.get_json()
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["camara_id"], 1)
        self.assertEqual(datos[0]["url"], "/grabaciones/1/2026-03-05/10-00-00.mp4")

    def test_filtra_por_camara_y_fecha(self):
        self._tocar(1, "2026-03-05", "a.mp4")
        self._tocar(2, "2026-03-06", "b.mp4")
        respuesta = self.cliente.get("/api/grabaciones?camara=1&fecha=2026-03-05")
        datos = respuesta.get_json()
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["camara_id"], 1)

    def test_fecha_invalida_devuelve_400(self):
        respuesta = self.cliente.get("/api/grabaciones?fecha=no-es-fecha")
        self.assertEqual(respuesta.status_code, 400)

    def test_eliminar_sin_filtros_devuelve_400(self):
        respuesta = self.cliente.post("/api/grabaciones/eliminar", json={})
        self.assertEqual(respuesta.status_code, 400)

    def test_eliminar_por_fecha_borra_los_archivos(self):
        ruta = self._tocar(1, "2026-03-05", "a.mp4")
        respuesta = self.cliente.post("/api/grabaciones/eliminar", json={"fecha": "2026-03-05"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["borrados"], 1)
        self.assertFalse(ruta.exists())

    def test_descargar_grabacion_existente(self):
        self._tocar(1, "2026-03-05", "a.mp4", contenido=b"contenido-del-video")
        with self.app.test_client() as cliente:  # contexto: libera el archivo servido al terminar
            respuesta = cliente.get("/grabaciones/1/2026-03-05/a.mp4")
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.data, b"contenido-del-video")

    def test_nombre_de_archivo_invalido_devuelve_404(self):
        respuesta = self.cliente.get("/grabaciones/1/2026-03-05/../../etc-passwd")
        self.assertIn(respuesta.status_code, (404, 308))  # 308: Flask normaliza el path antes de matchear la ruta


class AutenticacionTests(unittest.TestCase):
    def test_sin_credenciales_configuradas_no_pide_autenticacion(self):
        app = crear_app(_sincronizador(), _ConfigDePrueba("/no/existe"))
        respuesta = app.test_client().get("/api/camaras")
        self.assertEqual(respuesta.status_code, 200)

    def test_con_credenciales_configuradas_exige_autenticacion(self):
        app = crear_app(_sincronizador(), _ConfigDePrueba("/no/existe", usuario="admin", password="clave123"))
        respuesta = app.test_client().get("/api/camaras")
        self.assertEqual(respuesta.status_code, 401)

    def test_con_credenciales_correctas_deja_pasar(self):
        import base64

        app = crear_app(_sincronizador(), _ConfigDePrueba("/no/existe", usuario="admin", password="clave123"))
        credenciales = base64.b64encode(b"admin:clave123").decode()
        respuesta = app.test_client().get("/api/camaras", headers={"Authorization": f"Basic {credenciales}"})
        self.assertEqual(respuesta.status_code, 200)

    def test_con_credenciales_incorrectas_rechaza(self):
        import base64

        app = crear_app(_sincronizador(), _ConfigDePrueba("/no/existe", usuario="admin", password="clave123"))
        credenciales = base64.b64encode(b"admin:otra-clave").decode()
        respuesta = app.test_client().get("/api/camaras", headers={"Authorization": f"Basic {credenciales}"})
        self.assertEqual(respuesta.status_code, 401)


if __name__ == "__main__":
    unittest.main()
