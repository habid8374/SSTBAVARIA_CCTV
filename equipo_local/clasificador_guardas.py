"""Clasificador local «guarda abierta: sí/no», destilado de Claude (ver la
carpeta entrenamiento/ en la raíz del repo).

Corre gratis en el PC. En el MODO HÍBRIDO pre-filtra la revisión periódica:
en vez de mandar todas las fotos a Claude, el modelo local mira cada una y
solo las que marca como «posible guarda abierta» se escalan a Claude para
confirmar. Así se detecta lo importante sin gastar API en los frames normales.

Import de ultralytics perezoso (dentro de __init__), igual que deteccion.py:
así config.py y el resto se importan y prueban sin el modelo instalado.
"""

import logging
import threading
from pathlib import Path

logger = logging.getLogger("equipo_local.clasificador_guardas")


class ClasificadorGuardas:
    def __init__(self, modelo_path, umbral=0.5, clase_abierta="positivos"):
        from ultralytics import YOLO  # noqa: PLC0415 (import perezoso intencional, ver docstring)

        logger.info("Cargando clasificador de guardas %s…", modelo_path)
        self.modelo = YOLO(modelo_path)
        self.umbral = umbral
        self.clase_abierta = clase_abierta
        # Un modelo de ultralytics no admite predicciones simultáneas desde
        # varios hilos (ver deteccion.py): las cámaras se turnan con este lock.
        self._lock = threading.Lock()

    def posible_guarda_abierta(self, frame):
        """True si el modelo cree que hay una guarda abierta en `frame` (BGR de
        OpenCV) con confianza >= umbral. Ante cualquier error, devuelve True
        (conservador: mejor escalar a Claude que arriesgarse a no ver una
        guarda abierta)."""
        try:
            with self._lock:
                resultados = self.modelo(frame, verbose=False)
            probs = resultados[0].probs
            if probs is None:
                return True
            indice = int(probs.top1)
            confianza = float(probs.top1conf)
            nombre = self.modelo.names.get(indice, "")
            return nombre == self.clase_abierta and confianza >= self.umbral
        except Exception:
            logger.exception("Falló el clasificador de guardas — se escala a Claude por las dudas.")
            return True


def cargar_si_existe(modelo_path, umbral=0.5, clase_abierta="positivos"):
    """Carga el clasificador si el archivo del modelo existe. Si no está (o
    falla al cargar), devuelve None y el modo híbrido queda desactivado: la
    revisión periódica sigue funcionando como siempre (todo a Claude)."""
    if not modelo_path or not Path(modelo_path).is_file():
        logger.info("Sin modelo de guardas en %s — modo híbrido desactivado.", modelo_path)
        return None
    try:
        return ClasificadorGuardas(modelo_path, umbral, clase_abierta)
    except Exception:
        logger.exception("No se pudo cargar el clasificador de guardas — se sigue sin modo híbrido.")
        return None
