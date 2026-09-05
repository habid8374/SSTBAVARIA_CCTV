"""Configuración del equipo local, leída de variables de entorno.

Se pensó para correr como servicio en el mini-PC dedicado de la planta, así que todo se
configura por variable de entorno (systemd Environment=, o el .env que carga
main.py con python-dotenv) — nada de credenciales en el código.
"""

import os
from pathlib import Path

_CARPETA_EQUIPO_LOCAL = Path(__file__).resolve().parent


def _entero(nombre, default):
    valor = os.environ.get(nombre)
    return int(valor) if valor else default


def _flotante(nombre, default):
    valor = os.environ.get(nombre)
    return float(valor) if valor else default


def _booleano(nombre, default):
    valor = os.environ.get(nombre)
    if valor is None or valor == "":
        return default
    return valor.strip().lower() not in ("0", "false", "no")


class Config:
    # URL base del backend Django (Railway en producción, 127.0.0.1:8000 en pruebas locales).
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    # API key de este EquipoLocal — se genera al crear el registro desde el
    # dashboard (Sistema → Equipo local) o, alternativamente, en el admin de
    # Django (/admin/camaras_ia/equipolocal/add/), y se copia acá.
    API_KEY = os.environ.get("API_KEY", "")

    # Cada cuánto se refresca la lista de cámaras/zonas/horarios a vigilar.
    INTERVALO_SYNC_SEGUNDOS = _entero("INTERVALO_SYNC_SEGUNDOS", 60)

    # Cada cuánto se corre la detección sobre el frame más reciente de cada
    # cámara — no hace falta analizar cada frame del video (24-30 fps),
    # con 2-3 por segundo alcanza para no perder a alguien cruzando la zona.
    INTERVALO_DETECCION_SEGUNDOS = _flotante("INTERVALO_DETECCION_SEGUNDOS", 0.4)

    # Confianza mínima (0-1) para aceptar una detección de "persona" del modelo.
    CONFIANZA_MINIMA = _flotante("CONFIANZA_MINIMA", 0.5)

    # Una vez se reporta un evento para una zona, no se vuelve a reportar
    # para esa misma zona hasta que pase este tiempo — evita saturar la API
    # (y la bandeja de correo) mientras la persona sigue parada ahí.
    COOLDOWN_ZONA_SEGUNDOS = _entero("COOLDOWN_ZONA_SEGUNDOS", 60)

    # Ruta o nombre del modelo de ultralytics. "yolov8n.pt" (nano) se
    # descarga solo la primera vez; para un PC más limitado puede apuntar a
    # un modelo ya cuantizado/exportado a ONNX en disco.
    MODELO_YOLO = os.environ.get("MODELO_YOLO", "yolov8n.pt")

    # Timeout de las llamadas HTTP al backend.
    TIMEOUT_HTTP_SEGUNDOS = _entero("TIMEOUT_HTTP_SEGUNDOS", 10)

    # Segundos de espera antes de reintentar conectar una cámara caída.
    RECONEXION_SEGUNDOS = _entero("RECONEXION_SEGUNDOS", 10)

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # --- Grabación en disco (para revisar después) ---

    # Si se desactiva, el equipo local solo detecta/reporta — no graba nada
    # a disco (útil si el PC no tiene espacio de sobra).
    GRABAR_VIDEO = _booleano("GRABAR_VIDEO", True)

    # Carpeta base donde se guardan los clips: <carpeta>/<camara_id>/<YYYY-MM-DD>/HH-MM-SS.mp4
    # — con esa estructura, "eliminar por fecha" es simplemente borrar una subcarpeta.
    # Ruta absoluta por defecto (equipo_local/grabaciones), no relativa a la
    # carpeta de trabajo del proceso — la Tarea Programada/servicio corren
    # con la carpeta de trabajo en el padre de equipo_local (ver
    # windows/instalar_tarea_programada.ps1), así que una ruta relativa
    # terminaría creando la carpeta en el lugar equivocado.
    GRABACIONES_DIR = os.environ.get("GRABACIONES_DIR") or str(_CARPETA_EQUIPO_LOCAL / "grabaciones")

    # Cada cuánto se cierra el clip actual y se abre uno nuevo — clips más
    # cortos son más fáciles de indexar/borrar por fecha, pero generan más
    # archivos. Una hora es un buen equilibrio para revisión manual.
    GRABACIONES_DURACION_CLIP_MINUTOS = _entero("GRABACIONES_DURACION_CLIP_MINUTOS", 60)

    # FPS con el que se graba el clip — igual a la frecuencia real de
    # captura (1 / INTERVALO_DETECCION_SEGUNDOS), no a los 24-30fps del
    # stream original: no se lee cada frame del RTSP (ver arriba), así que
    # grabar más "fps" de los que en verdad se capturan solo generaría un
    # video acelerado. Si cambias INTERVALO_DETECCION_SEGUNDOS, ajusta esto también.
    GRABACIONES_FPS = _entero("GRABACIONES_FPS", 3)

    # Cuántos días se conservan las grabaciones antes de borrarse solas —
    # corre una limpieza automática una vez al día.
    GRABACIONES_RETENCION_DIAS = _entero("GRABACIONES_RETENCION_DIAS", 15)

    # --- Visor web local (cámaras en vivo + grabaciones) ---

    # Si se desactiva, no se levanta el visor web (solo detección/grabación).
    VISOR_WEB_ACTIVO = _booleano("VISOR_WEB_ACTIVO", True)

    # 0.0.0.0 para que se pueda ver desde otros equipos de la misma red —
    # nunca sale a internet, el equipo local no expone puertos públicos.
    VISOR_WEB_HOST = os.environ.get("VISOR_WEB_HOST", "0.0.0.0")
    VISOR_WEB_PUERTO = _entero("VISOR_WEB_PUERTO", 8090)

    # Usuario/contraseña del visor (HTTP Basic) — si se deja vacío, el visor
    # queda sin autenticación (solo recomendable si la red local ya es de
    # confianza). Ver equipo_local/README.md.
    VISOR_WEB_USUARIO = os.environ.get("VISOR_WEB_USUARIO", "")
    VISOR_WEB_PASSWORD = os.environ.get("VISOR_WEB_PASSWORD", "")

    # Anuncia <nombre>.local en la red (mDNS/Bonjour) apuntando a este PC,
    # para no tener que buscar/memorizar la IP — ver README → "Nombre en la
    # red en vez de IP". Si hay más de un equipo local en la misma red,
    # cada uno necesita un VISOR_WEB_MDNS_NOMBRE distinto.
    VISOR_WEB_MDNS_ACTIVO = _booleano("VISOR_WEB_MDNS_ACTIVO", True)
    VISOR_WEB_MDNS_NOMBRE = os.environ.get("VISOR_WEB_MDNS_NOMBRE", "sstbavaria-camaras")

    @classmethod
    def validar(cls):
        if not cls.API_KEY:
            raise ValueError(
                "Falta API_KEY. Créala desde el dashboard (Sistema → Equipo local) "
                "o en el admin de Django (/admin/camaras_ia/equipolocal/add/) "
                "y configúrala como variable de entorno."
            )
