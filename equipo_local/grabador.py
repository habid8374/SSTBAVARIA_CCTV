"""Grabación en disco de lo que ven las cámaras, con retención automática y
utilidades para listar/eliminar clips por cámara/fecha.

Las funciones de acá abajo que no tocan cv2.VideoWriter (listar, eliminar,
limpiar_antiguas, las rutas) son puras — trabajan sobre el sistema de
archivos y se prueban directo, sin cámara ni video real. GrabadorCamara sí
necesita un escritor de video; acepta uno inyectado (`fabrica_escritor`)
para poder probarlo sin cv2 real.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("equipo_local.grabador")

EXTENSION_CLIP = ".mp4"
CODEC_CLIP = "mp4v"


def carpeta_dia(base_dir, camara_id, fecha):
    """base_dir/<camara_id>/<YYYY-MM-DD>/ — con esta estructura, "todo lo de
    una fecha" es simplemente esa carpeta: fácil de listar y de borrar."""
    return Path(base_dir) / str(camara_id) / fecha.strftime("%Y-%m-%d")


def nombre_archivo_clip(momento):
    return momento.strftime("%H-%M-%S") + EXTENSION_CLIP


def ruta_clip(base_dir, camara_id, momento):
    return carpeta_dia(base_dir, camara_id, momento.date()) / nombre_archivo_clip(momento)


@dataclass
class Grabacion:
    camara_id: int
    fecha: str  # "YYYY-MM-DD"
    archivo: str
    ruta: Path
    tamano_bytes: int
    modificado_en: float


def listar_grabaciones(base_dir, camara_id=None, fecha=None):
    """Recorre base_dir/<camara_id>/<fecha>/*.mp4 y devuelve la lista de
    Grabacion, más recientes primero. camara_id/fecha son filtros
    opcionales (fecha como texto "YYYY-MM-DD")."""
    base = Path(base_dir)
    resultado = []
    if not base.is_dir():
        return resultado

    if camara_id is not None:
        carpetas_camara = [base / str(camara_id)]
    else:
        carpetas_camara = sorted(p for p in base.iterdir() if p.is_dir())

    for carpeta_camara in carpetas_camara:
        if not carpeta_camara.is_dir():
            continue
        try:
            id_camara = int(carpeta_camara.name)
        except ValueError:
            continue

        if fecha:
            carpetas_fecha = [carpeta_camara / fecha]
        else:
            carpetas_fecha = sorted(p for p in carpeta_camara.iterdir() if p.is_dir())

        for carpeta_fecha in carpetas_fecha:
            if not carpeta_fecha.is_dir():
                continue
            for archivo in sorted(carpeta_fecha.glob(f"*{EXTENSION_CLIP}")):
                stat = archivo.stat()
                resultado.append(
                    Grabacion(
                        camara_id=id_camara,
                        fecha=carpeta_fecha.name,
                        archivo=archivo.name,
                        ruta=archivo,
                        tamano_bytes=stat.st_size,
                        modificado_en=stat.st_mtime,
                    )
                )

    resultado.sort(key=lambda g: g.modificado_en, reverse=True)
    return resultado


def eliminar_grabaciones(base_dir, camara_id=None, fecha=None):
    """Borra las grabaciones que calcen con los filtros dados. Al menos uno
    de los dos (cámara o fecha) es obligatorio, para no poder vaciar todo el
    disco de un click desde la web por error. Devuelve cuántos archivos borró."""
    if camara_id is None and fecha is None:
        raise ValueError("Hay que indicar al menos cámara o fecha para eliminar grabaciones.")

    grabaciones = listar_grabaciones(base_dir, camara_id=camara_id, fecha=fecha)
    for grabacion in grabaciones:
        grabacion.ruta.unlink(missing_ok=True)
    _limpiar_carpetas_vacias(base_dir)
    return len(grabaciones)


def limpiar_antiguas(base_dir, dias_retencion, ahora=None):
    """Borra automáticamente las carpetas de fecha más viejas que
    `dias_retencion` días — para que el disco no se llene solo. Se corre
    periódicamente (ver main.py). Devuelve cuántas carpetas de fecha borró."""
    ahora = ahora if ahora is not None else datetime.now()
    limite = ahora.date() - timedelta(days=dias_retencion)
    base = Path(base_dir)
    if not base.is_dir():
        return 0

    borradas = 0
    for carpeta_camara in base.iterdir():
        if not carpeta_camara.is_dir():
            continue
        for carpeta_fecha in carpeta_camara.iterdir():
            if not carpeta_fecha.is_dir():
                continue
            try:
                fecha = datetime.strptime(carpeta_fecha.name, "%Y-%m-%d").date()
            except ValueError:
                continue
            if fecha < limite:
                _borrar_carpeta(carpeta_fecha)
                borradas += 1
    return borradas


def _borrar_carpeta(carpeta):
    for archivo in carpeta.glob("*"):
        archivo.unlink(missing_ok=True)
    carpeta.rmdir()


def _limpiar_carpetas_vacias(base_dir):
    base = Path(base_dir)
    if not base.is_dir():
        return
    for carpeta_camara in base.iterdir():
        if not carpeta_camara.is_dir():
            continue
        for carpeta_fecha in carpeta_camara.iterdir():
            if carpeta_fecha.is_dir() and not any(carpeta_fecha.iterdir()):
                carpeta_fecha.rmdir()


class LimpiadorPeriodico:
    """Corre limpiar_antiguas() a lo sumo una vez por día — se llama en
    cada ciclo del loop principal (main.py) y decide sola si ya toca."""

    def __init__(self, base_dir, dias_retencion):
        self.base_dir = base_dir
        self.dias_retencion = dias_retencion
        self._ultima_limpieza = None

    def tick(self, ahora=None):
        ahora = ahora if ahora is not None else datetime.now()
        if self._ultima_limpieza is not None and (ahora - self._ultima_limpieza) < timedelta(days=1):
            return None
        self._ultima_limpieza = ahora
        borradas = limpiar_antiguas(self.base_dir, self.dias_retencion, ahora=ahora)
        if borradas:
            logger.info("Limpieza de retención: %s carpetas de fecha eliminadas.", borradas)
        return borradas


class GrabadorCamara:
    """Escribe el video de una cámara a disco en clips de duración fija —
    abre un escritor nuevo cada `duracion_clip_segundos` (o si cambia el
    tamaño del frame) y lo cierra/reabre solo, transparente para quien
    llama a escribir_frame() en cada frame capturado."""

    def __init__(self, camara_id, base_dir, fps, duracion_clip_segundos, fabrica_escritor=None):
        self.camara_id = camara_id
        self.base_dir = base_dir
        self.fps = fps
        self.duracion_clip_segundos = duracion_clip_segundos
        self._fabrica_escritor = fabrica_escritor or self._crear_escritor_cv2
        self._escritor = None
        self._inicio_clip = None
        self._tamano_frame = None

    def escribir_frame(self, frame, ahora=None):
        ahora = ahora if ahora is not None else time.monotonic()
        alto, ancho = frame.shape[:2]
        clip_vencido = self._inicio_clip is not None and (ahora - self._inicio_clip) >= self.duracion_clip_segundos
        cambio_tamano = self._tamano_frame is not None and self._tamano_frame != (ancho, alto)
        if self._escritor is None or clip_vencido or cambio_tamano:
            self._reabrir(ancho, alto, ahora)
        if self._escritor is not None:
            self._escritor.write(frame)

    def _reabrir(self, ancho, alto, ahora):
        self.cerrar()
        ruta = ruta_clip(self.base_dir, self.camara_id, datetime.now())
        ruta.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._escritor = self._fabrica_escritor(str(ruta), ancho, alto)
        except Exception:
            logger.exception("No se pudo abrir el archivo de grabación %s", ruta)
            self._escritor = None
            return
        self._tamano_frame = (ancho, alto)
        self._inicio_clip = ahora

    def _crear_escritor_cv2(self, ruta, ancho, alto):
        import cv2

        fourcc = cv2.VideoWriter_fourcc(*CODEC_CLIP)
        return cv2.VideoWriter(ruta, fourcc, self.fps, (ancho, alto))

    def cerrar(self):
        if self._escritor is not None:
            self._escritor.release()
            self._escritor = None
