"""Cliente HTTP del backend (endpoints autenticados por API key en
camaras_ia/urls.py: /reglas-activas/ y /eventos/)."""

import logging

import requests

logger = logging.getLogger("equipo_local.cliente_api")


class ErrorApi(Exception):
    """Cualquier falla al hablar con el backend — red, timeout o HTTP != 2xx."""


class ClienteApi:
    def __init__(self, base_url, api_key, timeout_segundos=10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_segundos
        self._headers = {"X-API-Key": api_key}

    def obtener_reglas_activas(self):
        """Cámaras/zonas/horarios activos de la empresa de este equipo local."""
        url = f"{self.base_url}/api/camaras-ia/reglas-activas/"
        try:
            respuesta = requests.get(url, headers=self._headers, timeout=self.timeout)
            respuesta.raise_for_status()
        except requests.RequestException as err:
            raise ErrorApi(f"No se pudo obtener reglas-activas: {err}") from err
        return respuesta.json()

    def reportar_evento(self, camara_id, punto_x, punto_y, snapshot_jpeg=None):
        """Reporta una detección. El backend decide si cae en una zona
        activa con horario vigente (disparo_alerta) — acá no se duplica esa
        lógica, solo se reporta el punto detectado."""
        url = f"{self.base_url}/api/camaras-ia/eventos/"
        datos = {"camara": camara_id, "punto_x": punto_x, "punto_y": punto_y}
        archivos = {"snapshot": ("evento.jpg", snapshot_jpeg, "image/jpeg")} if snapshot_jpeg else None
        try:
            respuesta = requests.post(
                url, data=datos, files=archivos, headers=self._headers, timeout=self.timeout
            )
            respuesta.raise_for_status()
        except requests.RequestException as err:
            raise ErrorApi(f"No se pudo reportar el evento: {err}") from err
        return respuesta.json()
