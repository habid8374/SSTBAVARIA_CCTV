"""Lógica de negocio del módulo: cruce zona+horario y disparo de alertas.

Nada de esto habla con cámaras — recibe un punto ya detectado (por el
equipo local, vía ONVIF/análisis propio de la cámara) y decide si cae
dentro de una zona restringida y si hay una regla de horario vigente.
"""

import logging

from django.utils import timezone

logger = logging.getLogger("camaras_ia.alertas")


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


def _regla_vigente(regla, momento):
    """True si `regla` está activa para el día/hora de `momento`.

    Maneja horarios que cruzan medianoche (ej. 22:00–06:00): en ese caso el
    día que manda es el del inicio del turno, no el de la hora actual.
    """
    hora = momento.time()
    dia_hoy = momento.weekday()

    if regla.hora_inicio <= regla.hora_fin:
        return dia_hoy in regla.dias_semana and regla.hora_inicio <= hora <= regla.hora_fin

    if hora >= regla.hora_inicio:
        return dia_hoy in regla.dias_semana
    if hora <= regla.hora_fin:
        dia_anterior = (dia_hoy - 1) % 7
        return dia_anterior in regla.dias_semana
    return False


def evaluar_zona_horario(camara, punto, momento=None):
    """Cruza un punto detectado en `camara` contra sus zonas restringidas
    activas y las reglas de alerta vigentes en `momento` (por defecto ahora).

    Devuelve (zona, regla):
    - (None, None) si el punto no cae en ninguna zona activa de la cámara.
    - (zona, None) si cae en una zona pero ninguna de sus reglas activas
      aplica en este momento (fuera de horario).
    - (zona, regla) si cae en una zona y hay una regla vigente ahora mismo.
    """
    momento = momento or timezone.localtime()

    for zona in camara.zonas.filter(activa=True).prefetch_related("reglas"):
        if not punto_en_poligono(punto, zona.poligono):
            continue
        for regla in zona.reglas.filter(activa=True):
            if _regla_vigente(regla, momento):
                return zona, regla
        return zona, None

    return None, None


def disparar_alerta(evento, regla):
    """Dispara la notificación de una alerta.

    Stub por ahora: solo registra el intento en el log, con todo lo que
    necesitaría un envío real (canal, destinatario, evento, zona). Conectar
    un proveedor real de WhatsApp/correo es una decisión de proveedor aparte
    que todavía no se ha tomado.
    """
    logger.warning(
        "ALERTA disparada: evento_id=%s camara=%s zona=%s canal=%s destinatario=%s",
        evento.pk,
        evento.camara_id,
        regla.zona_id,
        regla.canal_notificacion,
        regla.destinatario,
    )
