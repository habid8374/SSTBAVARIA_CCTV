"""Geometría pura, sin dependencias — copia intencional de
camaras_ia/services.py:punto_en_poligono. El equipo local corre en otra
máquina, fuera del entorno Django, así que no puede importar ese módulo; se
duplica esta función chica en vez de acoplar los dos proyectos por un import
entre repos/entornos separados.
"""


def punto_en_poligono(punto, poligono):
    """Ray casting clásico: True si `punto` (x, y) cae dentro de `poligono`
    (lista de [x, y]). Polígonos de menos de 3 vértices nunca contienen nada.
    """
    if len(poligono) < 3:
        return False

    x, y = punto
    dentro = False
    x1, y1 = poligono[-1]
    for x2, y2 in poligono:
        if (y1 > y) != (y2 > y):
            x_interseccion = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_interseccion:
                dentro = not dentro
        x1, y1 = x2, y2
    return dentro


def punto_en_circulo(punto, centro, radio_px):
    """True si `punto` (x, y) cae dentro del círculo de centro `centro`
    (x, y) y radio `radio_px`, ya en píxeles. `radio_px` None o <= 0 nunca
    contiene nada (ej. cámara sin calibrar)."""
    if radio_px is None or radio_px <= 0:
        return False
    x, y = punto
    cx, cy = centro
    return (x - cx) ** 2 + (y - cy) ** 2 <= radio_px**2


def punto_en_zona(punto, zona, px_por_metro=None):
    """Copia intencional de camaras_ia/services.py:punto_en_zona — dispatch
    según zona["tipo"]: polígono (por defecto) o punto+radio real (necesita
    que la cámara esté calibrada, `px_por_metro` no None)."""
    if zona.get("tipo") == "punto_radio":
        centro_x, centro_y, radio_metros = zona.get("centro_x"), zona.get("centro_y"), zona.get("radio_metros")
        if centro_x is None or centro_y is None or radio_metros is None or not px_por_metro:
            return False
        radio_px = radio_metros * px_por_metro
        return punto_en_circulo(punto, (centro_x, centro_y), radio_px)
    return punto_en_poligono(punto, zona.get("poligono") or [])


def escalar_punto(punto, tamano_origen, tamano_destino):
    """Reescala `punto` (x, y) detectado en un frame de tamaño
    `tamano_origen` (ancho, alto) al sistema de coordenadas de
    `tamano_destino` — necesario porque el video en vivo (RTSP) casi nunca
    tiene la misma resolución que el snapshot de referencia sobre el que se
    dibujaron los polígonos de zona en el dashboard."""
    ancho_origen, alto_origen = tamano_origen
    ancho_destino, alto_destino = tamano_destino
    if ancho_origen <= 0 or alto_origen <= 0:
        raise ValueError("tamano_origen debe tener ancho y alto positivos.")
    x, y = punto
    return (
        x * ancho_destino / ancho_origen,
        y * alto_destino / alto_origen,
    )
