"""Detección de personas sobre un frame de video con YOLOv8n (ultralytics).

Import de ultralytics/torch perezoso (dentro de __init__, no al nivel del
módulo): así config.py, geometria.py y cliente_api.py se pueden importar y
probar sin tener el modelo (~500MB con dependencias) instalado.
"""

import logging
import threading

logger = logging.getLogger("equipo_local.deteccion")

CLASE_PERSONA = 0  # índice de "person" en el dataset COCO — el que trae YOLOv8n preentrenado


class DetectorPersonas:
    def __init__(self, modelo_path="yolov8n.pt", confianza_minima=0.5):
        from ultralytics import YOLO  # noqa: PLC0415 (import perezoso intencional, ver docstring)

        logger.info("Cargando modelo %s…", modelo_path)
        self.modelo = YOLO(modelo_path)
        self.confianza_minima = confianza_minima
        # Un solo modelo para todas las cámaras (cargar uno por cámara
        # multiplicaría la RAM), pero cada cámara corre en su propio hilo y
        # un modelo de ultralytics no admite predicciones simultáneas desde
        # varios hilos (comparten el estado interno del predictor): se
        # turnan con este lock.
        self._lock = threading.Lock()

    def detectar(self, frame):
        """Devuelve una lista de (x, y, confianza) por cada persona detectada
        en `frame` (array BGR de OpenCV). (x, y) es el punto de apoyo
        estimado — centro-inferior del cuadro detectado, es decir la
        posición de los pies, más preciso que el centro del cuadro para
        decidir si alguien está parado dentro de una zona en el piso."""
        with self._lock:
            resultados = self.modelo(frame, classes=[CLASE_PERSONA], conf=self.confianza_minima, verbose=False)
        detecciones = []
        for resultado in resultados:
            for caja in resultado.boxes:
                x1, y1, x2, y2 = caja.xyxy[0].tolist()
                confianza = float(caja.conf[0])
                detecciones.append(((x1 + x2) / 2, y2, confianza))
        return detecciones
