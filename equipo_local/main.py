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
from pathlib import Path


def _configurar_logging(nivel="INFO"):
    """Corre como Tarea Programada sin ventana (pythonw.exe): sys.stderr no
    existe ahí, así que un logging.basicConfig() normal (StreamHandler a
    stderr) no imprime nada en ningún lado y cualquier error se pierde en
    silencio. Por eso siempre se agrega un archivo — equipo_local.log, junto
    a este script — que sí persiste sin importar cómo se esté corriendo.
    Se llama al importar este módulo (no solo dentro de main()) para que ni
    siquiera un error temprano al importar una dependencia (ej. cv2) se
    pierda sin dejar rastro."""
    directorio = Path(__file__).resolve().parent
    handlers = [logging.FileHandler(directorio / "equipo_local.log", encoding="utf-8")]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=nivel, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers)


_configurar_logging()
logger = logging.getLogger("equipo_local.main")

try:
    from dotenv import load_dotenv

    # Ruta explícita (no la búsqueda automática por defecto de load_dotenv,
    # que parte de la carpeta de trabajo actual) — así el .env se encuentra
    # sin importar con qué carpeta de trabajo se haya arrancado el proceso
    # (ver windows/instalar_tarea_programada.ps1 y
    # systemd/equipo-local-camaras.service: la carpeta de trabajo tiene que
    # ser la carpeta *padre* de este paquete para que
    # "python -m equipo_local.main" se pueda importar).
    load_dotenv(Path(__file__).resolve().parent / ".env")

    from .camara import CamaraMonitor
    from .cliente_api import ClienteApi, ErrorApi
    from .config import Config
except Exception:
    logger.exception("Error importando una dependencia — el programa se detiene.")
    sys.exit(1)


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


def main():
    logging.getLogger().setLevel(Config.LOG_LEVEL)  # el bootstrap arrancó en INFO; ya se puede ajustar
    try:
        Config.validar()
    except ValueError as err:
        logger.error(str(err))
        sys.exit(1)

    from .deteccion import DetectorPersonas  # import perezoso: acá sí hace falta el modelo real

    cliente_api = ClienteApi(Config.API_BASE_URL, Config.API_KEY, Config.TIMEOUT_HTTP_SEGUNDOS)
    detector = DetectorPersonas(Config.MODELO_YOLO, Config.CONFIANZA_MINIMA)
    sincronizador = SincronizadorCamaras(cliente_api, detector, Config)

    anuncio_mdns = None
    if Config.VISOR_WEB_ACTIVO:
        from .visor_web import iniciar_en_hilo  # import perezoso: acá sí hace falta Flask

        iniciar_en_hilo(sincronizador, Config)

        if Config.VISOR_WEB_MDNS_ACTIVO:
            from .mdns import anunciar  # import perezoso: acá sí hace falta zeroconf

            anuncio_mdns = anunciar(Config)

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
    if anuncio_mdns is not None:
        from .mdns import dejar_de_anunciar

        dejar_de_anunciar(anuncio_mdns)
    logger.info("Equipo local detenido.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Error fatal no manejado — el programa se detiene.")
        sys.exit(1)
