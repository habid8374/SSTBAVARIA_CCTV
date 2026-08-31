"""Monitor de una cámara: conecta al RTSP, corre detección sobre los frames,
cruza cada detección contra las zonas conocidas (con cooldown por zona) y
reporta al backend. El backend es quien decide si el punto realmente cae en
una zona activa con horario vigente — acá solo se filtra localmente lo obvio,
para no gastar ancho de banda subiendo snapshots de detecciones que a todas
luces no tocan ninguna zona dibujada.
"""

import logging
import threading
import time

import cv2
import numpy as np
import requests

from .geometria import escalar_punto, punto_en_poligono
from .grabador import GrabadorCamara

logger = logging.getLogger("equipo_local.camara")


class CamaraMonitor:
    def __init__(self, camara_datos, detector, cliente_api, config, fabrica_grabador=GrabadorCamara):
        """`camara_datos` es el dict de una cámara tal como lo devuelve
        obtener_reglas_activas(): id, nombre, rtsp_url, snapshot_referencia, zonas[]."""
        self.id = camara_datos["id"]
        self.nombre = camara_datos.get("nombre", f"Cámara {self.id}")
        self.rtsp_url = camara_datos["rtsp_url"]
        self.zonas = camara_datos.get("zonas", [])
        self._snapshot_referencia_url = camara_datos.get("snapshot_referencia")
        self.detector = detector
        self.cliente_api = cliente_api
        self.config = config
        self._tamano_referencia = None  # se resuelve la primera vez que hace falta, después se cachea
        self._ultimo_reporte_por_zona = {}
        self._detener = threading.Event()
        self._hilo = None
        self._lock_frame = threading.Lock()
        self._ultimo_frame_jpeg = None
        self._grabador = None
        if getattr(config, "GRABAR_VIDEO", False):
            self._grabador = fabrica_grabador(
                self.id,
                config.GRABACIONES_DIR,
                config.GRABACIONES_FPS,
                config.GRABACIONES_DURACION_CLIP_MINUTOS * 60,
            )

    def actualizar(self, camara_datos):
        """Refresca zonas/reglas/rtsp sin perder el cooldown acumulado ni
        reiniciar la conexión — se llama en cada ciclo de sincronización."""
        self.nombre = camara_datos.get("nombre", self.nombre)
        self.rtsp_url = camara_datos["rtsp_url"]
        self.zonas = camara_datos.get("zonas", [])
        if camara_datos.get("snapshot_referencia") != self._snapshot_referencia_url:
            self._snapshot_referencia_url = camara_datos.get("snapshot_referencia")
            self._tamano_referencia = None  # cambió la referencia, hay que releerla

    def iniciar(self):
        self._hilo = threading.Thread(target=self._loop_captura, name=f"camara-{self.id}", daemon=True)
        self._hilo.start()

    def detener(self):
        self._detener.set()
        if self._hilo:
            self._hilo.join(timeout=5)
        if self._grabador is not None:
            self._grabador.cerrar()

    def obtener_ultimo_frame_jpeg(self):
        """Último frame capturado, ya codificado en JPEG — lo consume el
        visor web en vivo (ver visor_web.py). None si todavía no hay ninguno."""
        with self._lock_frame:
            return self._ultimo_frame_jpeg

    # --- Lógica de decisión, separada de la captura para poder probarla sin cámara real ---

    def evaluar_deteccion(self, punto, tamano_frame, ahora=None):
        """Dado un punto detectado (en coordenadas del frame RTSP) y el
        tamaño de ese frame, decide en qué zona(s) cae — ya escalado al
        sistema de coordenadas del snapshot de referencia — y si toca
        reportarlo según el cooldown. Devuelve la lista de zonas a reportar
        (puede ser más de una si los polígonos se solapan)."""
        ahora = ahora if ahora is not None else time.monotonic()
        tamano_referencia = self._resolver_tamano_referencia()
        punto_escalado = escalar_punto(punto, tamano_frame, tamano_referencia) if tamano_referencia else punto

        zonas_a_reportar = []
        for zona in self.zonas:
            if not punto_en_poligono(punto_escalado, zona["poligono"]):
                continue
            if self._paso_cooldown(zona["id"], ahora):
                zonas_a_reportar.append(zona)
        return punto_escalado, zonas_a_reportar

    def _paso_cooldown(self, zona_id, ahora):
        ultimo = self._ultimo_reporte_por_zona.get(zona_id, float("-inf"))
        if ahora - ultimo < self.config.COOLDOWN_ZONA_SEGUNDOS:
            return False
        self._ultimo_reporte_por_zona[zona_id] = ahora
        return True

    def _resolver_tamano_referencia(self):
        if self._tamano_referencia is not None:
            return self._tamano_referencia
        if not self._snapshot_referencia_url:
            return None
        try:
            respuesta = requests.get(self._snapshot_referencia_url, timeout=self.config.TIMEOUT_HTTP_SEGUNDOS)
            respuesta.raise_for_status()
            datos = np.frombuffer(respuesta.content, dtype=np.uint8)
            imagen = cv2.imdecode(datos, cv2.IMREAD_COLOR)
            if imagen is None:
                raise ValueError("No se pudo decodificar la imagen de referencia.")
            alto, ancho = imagen.shape[:2]
            self._tamano_referencia = (ancho, alto)
        except Exception:
            logger.exception("No se pudo leer el snapshot de referencia de %s", self.nombre)
            return None
        return self._tamano_referencia

    # --- Captura real (necesita cámara/RTSP de verdad, no se prueba en unit tests) ---

    def _loop_captura(self):
        while not self._detener.is_set():
            captura = cv2.VideoCapture(self.rtsp_url)
            if not captura.isOpened():
                logger.warning(
                    "No se pudo conectar a %s (%s) — reintentando en %ss",
                    self.nombre,
                    self.rtsp_url,
                    self.config.RECONEXION_SEGUNDOS,
                )
                captura.release()
                time.sleep(self.config.RECONEXION_SEGUNDOS)
                continue

            logger.info("Conectado a %s", self.nombre)
            while not self._detener.is_set():
                ok, frame = captura.read()
                if not ok:
                    logger.warning("Se perdió la señal de %s — reconectando…", self.nombre)
                    break
                self._actualizar_ultimo_frame(frame)
                if self._grabador is not None:
                    self._grabador.escribir_frame(frame)
                self._procesar_frame(frame)
                time.sleep(self.config.INTERVALO_DETECCION_SEGUNDOS)
            captura.release()

    def _actualizar_ultimo_frame(self, frame):
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            return
        with self._lock_frame:
            self._ultimo_frame_jpeg = buffer.tobytes()

    def _procesar_frame(self, frame):
        alto, ancho = frame.shape[:2]
        for x, y, confianza in self.detector.detectar(frame):
            punto_escalado, zonas = self.evaluar_deteccion((x, y), (ancho, alto))
            for zona in zonas:
                self._reportar(punto_escalado, frame, zona, confianza)

    def _reportar(self, punto, frame, zona, confianza):
        ok, buffer = cv2.imencode(".jpg", frame)
        snapshot = buffer.tobytes() if ok else None
        try:
            resultado = self.cliente_api.reportar_evento(self.id, punto[0], punto[1], snapshot)
            logger.info(
                "Evento reportado — %s / %s (confianza=%.2f): disparo_alerta=%s",
                self.nombre,
                zona.get("nombre"),
                confianza,
                resultado.get("disparo_alerta"),
            )
        except Exception:
            logger.exception("No se pudo reportar el evento de %s / %s", self.nombre, zona.get("nombre"))
