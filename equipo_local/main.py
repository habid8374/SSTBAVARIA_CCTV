"""Punto de entrada del equipo local.

Sincroniza periódicamente la lista de cámaras/zonas/horarios activos desde
el backend (obtener_reglas_activas) y mantiene un CamaraMonitor corriendo
por cada cámara activa — creándolo, actualizándolo o deteniéndolo según
corresponda en cada ciclo. Pensado para correr como servicio en segundo
plano (systemd en Linux, Tarea Programada en Windows — ver equipo_local/README.md).
"""

import logging
import signal
import sys
import time

from dotenv import load_dotenv

load_dotenv()  # antes de leer Config: toma las variables de un .env si existe junto a este archivo

from .camara import CamaraMonitor  # noqa: E402
from .cliente_api import ClienteApi, ErrorApi  # noqa: E402
from .config import Config  # noqa: E402

logger = logging.getLogger("equipo_local.main")


class SincronizadorCamaras:
    """Reconcilia los CamaraMonitor activos contra lo que devuelve el
    backend. Recibe `fabrica_monitor` para poder inyectar un doble de
    CamaraMonitor en los tests, sin depender de cv2/ultralytics reales."""

    def __init__(self, cliente_api, detector, config, fabrica_monitor=CamaraMonitor):
        self.cliente_api = cliente_api
        self.detector = detector
        self.config = config
        self._fabrica_monitor = fabrica_monitor
        self.monitores = {}

    def sincronizar(self):
        try:
            datos = self.cliente_api.obtener_reglas_activas()
        except ErrorApi as err:
            logger.error("No se pudo sincronizar reglas-activas: %s", err)
            return

        camaras_actuales = {c["id"]: c for c in datos.get("camaras", [])}

        for camara_id in list(self.monitores):
            if camara_id not in camaras_actuales:
                logger.info("Cámara %s ya no está activa — deteniendo su monitor.", camara_id)
                self.monitores.pop(camara_id).detener()

        for camara_id, camara_datos in camaras_actuales.items():
            if camara_id in self.monitores:
                self.monitores[camara_id].actualizar(camara_datos)
            else:
                logger.info("Nueva cámara activa: %s (id=%s)", camara_datos.get("nombre"), camara_id)
                monitor = self._fabrica_monitor(camara_datos, self.detector, self.cliente_api, self.config)
                monitor.iniciar()
                self.monitores[camara_id] = monitor

    def detener_todo(self):
        for monitor in self.monitores.values():
            monitor.detener()
        self.monitores.clear()


def _configurar_logging():
    logging.basicConfig(level=Config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main():
    _configurar_logging()
    try:
        Config.validar()
    except ValueError as err:
        logger.error(str(err))
        sys.exit(1)

    from .deteccion import DetectorPersonas  # import perezoso: acá sí hace falta el modelo real

    cliente_api = ClienteApi(Config.API_BASE_URL, Config.API_KEY, Config.TIMEOUT_HTTP_SEGUNDOS)
    detector = DetectorPersonas(Config.MODELO_YOLO, Config.CONFIANZA_MINIMA)
    sincronizador = SincronizadorCamaras(cliente_api, detector, Config)

    if Config.VISOR_WEB_ACTIVO:
        from .visor_web import iniciar_en_hilo  # import perezoso: acá sí hace falta Flask

        iniciar_en_hilo(sincronizador, Config)

    limpiador = None
    if Config.GRABAR_VIDEO:
        from .grabador import LimpiadorPeriodico

        limpiador = LimpiadorPeriodico(Config.GRABACIONES_DIR, Config.GRABACIONES_RETENCION_DIAS)

    estado = {"detener": False}

    def _manejar_senal(signum, frame):
        logger.info("Señal recibida, deteniendo…")
        estado["detener"] = True

    signal.signal(signal.SIGINT, _manejar_senal)
    signal.signal(signal.SIGTERM, _manejar_senal)

    logger.info("Equipo local iniciado — backend: %s", Config.API_BASE_URL)
    while not estado["detener"]:
        sincronizador.sincronizar()
        if limpiador is not None:
            limpiador.tick()
        time.sleep(Config.INTERVALO_SYNC_SEGUNDOS)

    sincronizador.detener_todo()
    logger.info("Equipo local detenido.")


if __name__ == "__main__":
    main()
