import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from equipo_local.grabador import (
    GrabadorCamara,
    LimpiadorPeriodico,
    carpeta_dia,
    eliminar_grabaciones,
    limpiar_antiguas,
    listar_grabaciones,
    nombre_archivo_clip,
    ruta_clip,
)


def _tocar(ruta, contenido=b"x"):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)


class RutasTests(unittest.TestCase):
    def test_carpeta_dia(self):
        fecha = datetime(2026, 3, 5).date()
        self.assertEqual(carpeta_dia("/base", 7, fecha), Path("/base/7/2026-03-05"))

    def test_nombre_archivo_clip(self):
        momento = datetime(2026, 3, 5, 14, 7, 9)
        self.assertEqual(nombre_archivo_clip(momento), "14-07-09.mp4")

    def test_ruta_clip(self):
        momento = datetime(2026, 3, 5, 14, 7, 9)
        self.assertEqual(ruta_clip("/base", 7, momento), Path("/base/7/2026-03-05/14-07-09.mp4"))


class ListarGrabacionesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_directorio_inexistente_devuelve_lista_vacia(self):
        self.assertEqual(listar_grabaciones("/no/existe"), [])

    def test_lista_todas_las_camaras_y_fechas(self):
        _tocar(Path(self.base) / "1" / "2026-03-05" / "10-00-00.mp4")
        _tocar(Path(self.base) / "2" / "2026-03-06" / "11-00-00.mp4")
        grabaciones = listar_grabaciones(self.base)
        self.assertEqual({(g.camara_id, g.fecha, g.archivo) for g in grabaciones}, {
            (1, "2026-03-05", "10-00-00.mp4"),
            (2, "2026-03-06", "11-00-00.mp4"),
        })

    def test_filtra_por_camara(self):
        _tocar(Path(self.base) / "1" / "2026-03-05" / "10-00-00.mp4")
        _tocar(Path(self.base) / "2" / "2026-03-05" / "10-00-00.mp4")
        grabaciones = listar_grabaciones(self.base, camara_id=1)
        self.assertEqual([g.camara_id for g in grabaciones], [1])

    def test_filtra_por_fecha(self):
        _tocar(Path(self.base) / "1" / "2026-03-05" / "10-00-00.mp4")
        _tocar(Path(self.base) / "1" / "2026-03-06" / "10-00-00.mp4")
        grabaciones = listar_grabaciones(self.base, fecha="2026-03-06")
        self.assertEqual([g.fecha for g in grabaciones], ["2026-03-06"])

    def test_ignora_carpetas_de_camara_no_numericas(self):
        _tocar(Path(self.base) / "no-es-un-id" / "2026-03-05" / "x.mp4")
        self.assertEqual(listar_grabaciones(self.base), [])

    def test_incluye_tamano_del_archivo(self):
        _tocar(Path(self.base) / "1" / "2026-03-05" / "10-00-00.mp4", contenido=b"1234567")
        grabaciones = listar_grabaciones(self.base)
        self.assertEqual(grabaciones[0].tamano_bytes, 7)


class EliminarGrabacionesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_sin_filtros_lanza_error(self):
        with self.assertRaises(ValueError):
            eliminar_grabaciones(self.base)

    def test_elimina_por_fecha_y_limpia_carpeta_vacia(self):
        ruta = Path(self.base) / "1" / "2026-03-05" / "10-00-00.mp4"
        _tocar(ruta)
        borrados = eliminar_grabaciones(self.base, fecha="2026-03-05")
        self.assertEqual(borrados, 1)
        self.assertFalse(ruta.exists())
        self.assertFalse(ruta.parent.exists())  # la carpeta de fecha, ya vacía, también se borra

    def test_elimina_solo_de_la_camara_indicada(self):
        _tocar(Path(self.base) / "1" / "2026-03-05" / "a.mp4")
        _tocar(Path(self.base) / "2" / "2026-03-05" / "b.mp4")
        borrados = eliminar_grabaciones(self.base, camara_id=1)
        self.assertEqual(borrados, 1)
        self.assertEqual(len(listar_grabaciones(self.base)), 1)
        self.assertEqual(listar_grabaciones(self.base)[0].camara_id, 2)

    def test_sin_coincidencias_no_falla(self):
        self.assertEqual(eliminar_grabaciones(self.base, fecha="2099-01-01"), 0)


class LimpiarAntiguasTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_borra_carpetas_mas_viejas_que_la_retencion(self):
        _tocar(Path(self.base) / "1" / "2026-01-01" / "a.mp4")
        _tocar(Path(self.base) / "1" / "2026-03-01" / "b.mp4")
        borradas = limpiar_antiguas(self.base, dias_retencion=15, ahora=datetime(2026, 3, 10))
        self.assertEqual(borradas, 1)
        restantes = {g.fecha for g in listar_grabaciones(self.base)}
        self.assertEqual(restantes, {"2026-03-01"})

    def test_directorio_inexistente_no_falla(self):
        self.assertEqual(limpiar_antiguas("/no/existe", dias_retencion=15), 0)

    def test_ignora_carpetas_con_nombre_no_fecha(self):
        _tocar(Path(self.base) / "1" / "no-es-fecha" / "a.mp4")
        borradas = limpiar_antiguas(self.base, dias_retencion=1, ahora=datetime(2026, 3, 10))
        self.assertEqual(borradas, 0)


class LimpiadorPeriodicoTests(unittest.TestCase):
    def test_corre_la_primera_vez(self):
        limpiador = LimpiadorPeriodico("/no/existe", dias_retencion=15)
        self.assertEqual(limpiador.tick(ahora=datetime(2026, 3, 10)), 0)

    def test_no_vuelve_a_correr_antes_de_un_dia(self):
        limpiador = LimpiadorPeriodico("/no/existe", dias_retencion=15)
        limpiador.tick(ahora=datetime(2026, 3, 10, 8, 0))
        resultado = limpiador.tick(ahora=datetime(2026, 3, 10, 20, 0))
        self.assertIsNone(resultado)

    def test_vuelve_a_correr_pasado_un_dia(self):
        limpiador = LimpiadorPeriodico("/no/existe", dias_retencion=15)
        limpiador.tick(ahora=datetime(2026, 3, 10, 8, 0))
        resultado = limpiador.tick(ahora=datetime(2026, 3, 11, 9, 0))
        self.assertEqual(resultado, 0)


class GrabadorCamaraTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.addCleanup(self._tmp.cleanup)
        self.escritores_creados = []

        def fabrica(ruta, ancho, alto):
            escritor = MagicMock()
            escritor.ruta = ruta
            escritor.tamano = (ancho, alto)
            self.escritores_creados.append(escritor)
            return escritor

        self.fabrica_escritor = fabrica

    def _frame(self, ancho=640, alto=480):
        import numpy as np

        return np.zeros((alto, ancho, 3), dtype="uint8")

    def test_primer_frame_abre_un_escritor_y_crea_la_carpeta(self):
        grabador = GrabadorCamara(1, self.base, fps=3, duracion_clip_segundos=3600, fabrica_escritor=self.fabrica_escritor)
        grabador.escribir_frame(self._frame(), ahora=0)
        self.assertEqual(len(self.escritores_creados), 1)
        self.escritores_creados[0].write.assert_called_once()

    def test_no_reabre_dentro_del_mismo_clip(self):
        grabador = GrabadorCamara(1, self.base, fps=3, duracion_clip_segundos=3600, fabrica_escritor=self.fabrica_escritor)
        grabador.escribir_frame(self._frame(), ahora=0)
        grabador.escribir_frame(self._frame(), ahora=100)
        self.assertEqual(len(self.escritores_creados), 1)
        self.assertEqual(self.escritores_creados[0].write.call_count, 2)

    def test_reabre_al_vencer_la_duracion_del_clip(self):
        grabador = GrabadorCamara(1, self.base, fps=3, duracion_clip_segundos=60, fabrica_escritor=self.fabrica_escritor)
        grabador.escribir_frame(self._frame(), ahora=0)
        grabador.escribir_frame(self._frame(), ahora=61)
        self.assertEqual(len(self.escritores_creados), 2)
        self.escritores_creados[0].release.assert_called_once()

    def test_reabre_si_cambia_el_tamano_del_frame(self):
        grabador = GrabadorCamara(1, self.base, fps=3, duracion_clip_segundos=3600, fabrica_escritor=self.fabrica_escritor)
        grabador.escribir_frame(self._frame(640, 480), ahora=0)
        grabador.escribir_frame(self._frame(1280, 720), ahora=1)
        self.assertEqual(len(self.escritores_creados), 2)

    def test_error_al_abrir_no_rompe_y_sigue_sin_grabar(self):
        def fabrica_rota(ruta, ancho, alto):
            raise OSError("disco lleno")

        grabador = GrabadorCamara(1, self.base, fps=3, duracion_clip_segundos=3600, fabrica_escritor=fabrica_rota)
        grabador.escribir_frame(self._frame(), ahora=0)  # no debe lanzar

    def test_cerrar_libera_el_escritor_activo(self):
        grabador = GrabadorCamara(1, self.base, fps=3, duracion_clip_segundos=3600, fabrica_escritor=self.fabrica_escritor)
        grabador.escribir_frame(self._frame(), ahora=0)
        grabador.cerrar()
        self.escritores_creados[0].release.assert_called_once()

    def test_cerrar_sin_haber_grabado_no_falla(self):
        grabador = GrabadorCamara(1, self.base, fps=3, duracion_clip_segundos=3600, fabrica_escritor=self.fabrica_escritor)
        grabador.cerrar()  # no debe lanzar


if __name__ == "__main__":
    unittest.main()
