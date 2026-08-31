"""Configuración del equipo local, leída de variables de entorno.

Se pensó para correr como servicio en el PC del DVR/NVR, así que todo se
configura por variable de entorno (systemd Environment=, o el .env que carga
main.py con python-dotenv) — nada de credenciales en el código.
"""

import os


def _entero(nombre, default):
    valor = os.environ.get(nombre)
    return int(valor) if valor else default


def _flotante(nombre, default):
    valor = os.environ.get(nombre)
    return float(valor) if valor else default


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

    @classmethod
    def validar(cls):
        if not cls.API_KEY:
            raise ValueError(
                "Falta API_KEY. Créala desde el dashboard (Sistema → Equipo local) "
                "o en el admin de Django (/admin/camaras_ia/equipolocal/add/) "
                "y configúrala como variable de entorno."
            )
