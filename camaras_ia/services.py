"""Lógica de negocio del módulo: cruce zona+horario y disparo de alertas.

Nada de esto habla con cámaras — recibe un punto ya detectado (por el
equipo local, vía ONVIF/análisis propio de la cámara) y decide si cae
dentro de una zona restringida y si hay una regla de horario vigente.
"""

import logging

from django.utils import timezone

from .notificaciones import ErrorEnvioCorreo, enviar_correo_brevo

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

    Canal "correo": envío real vía Brevo, con el resultado (éxito o el
    motivo del error) guardado en evento.notificacion_enviada/_detalle para
    que se vea en la bandeja de Alertas del dashboard.
    Canal "whatsapp": sigue siendo un stub — solo el log de abajo. Conectar
    un proveedor real de WhatsApp es una decisión de proveedor aparte que
    todavía no se ha tomado.
    """
    logger.warning(
        "ALERTA disparada: evento_id=%s camara=%s zona=%s canal=%s destinatario=%s",
        evento.pk,
        evento.camara_id,
        regla.zona_id,
        regla.canal_notificacion,
        regla.destinatario,
    )

    if regla.canal_notificacion == "correo":  # ReglaAlerta.Canal.CORREO
        _enviar_notificacion_correo(evento, regla)


def _enviar_notificacion_correo(evento, regla):
    zona_nombre = evento.zona.nombre if evento.zona else "zona restringida"
    momento = timezone.localtime(evento.timestamp)
    asunto = f"Alerta SST Bavaria — {zona_nombre}"
    contenido_html = (
        f"<p>Se detectó una persona en <strong>{zona_nombre}</strong> "
        f"(cámara <strong>{evento.camara.nombre}</strong>) fuera del horario permitido.</p>"
        f"<p>Fecha y hora: {momento:%Y-%m-%d %H:%M:%S}</p>"
    )

    adjunto_bytes = None
    adjunto_nombre = None
    if evento.snapshot:
        try:
            evento.snapshot.open("rb")
            adjunto_bytes = evento.snapshot.read()
            adjunto_nombre = evento.snapshot.name.rsplit("/", 1)[-1]
        finally:
            evento.snapshot.close()

    try:
        enviar_correo_brevo(regla.destinatario, asunto, contenido_html, adjunto_bytes, adjunto_nombre)
    except ErrorEnvioCorreo as err:
        logger.error("No se pudo enviar la alerta por correo (evento_id=%s): %s", evento.pk, err)
        evento.notificacion_enviada = False
        evento.notificacion_detalle = str(err)[:255]
    else:
        evento.notificacion_enviada = True
        evento.notificacion_detalle = f"Correo enviado a {regla.destinatario}"[:255]
    evento.save(update_fields=["notificacion_enviada", "notificacion_detalle"])
