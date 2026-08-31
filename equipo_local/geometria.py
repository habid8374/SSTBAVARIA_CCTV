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
