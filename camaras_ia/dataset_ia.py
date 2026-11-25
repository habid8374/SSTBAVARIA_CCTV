"""Análisis del dataset acumulado para destilar la IA (Claude) a un modelo
local (YOLO/clasificador).

Cada EventoDetectado con foto (`snapshot`) y ya analizado por Claude
(`ia_analizado_en`, `tipos_ia`) es un ejemplo etiquetado "gratis": la foto es
la entrada y lo que Claude detectó es la etiqueta. Esta función cuenta cuántos
ejemplos hay, cuántos son positivos de cada clase y cómo está el balance, para
decidir si ya se puede entrenar un primer modelo o si falta acumular.
"""

from .models import EventoDetectado, TipoEventoIA

# Mínimo de ejemplos positivos por clase para intentar un primer modelo. Es una
# guía práctica (no una ley): con menos, el modelo casi no generaliza.
UMBRAL_ENTRENABLE = 200
UMBRAL_INSUFICIENTE = 100


def _con_foto(qs):
    """Eventos con snapshot de verdad (no vacío ni nulo) — los únicos que
    sirven para entrenar."""
    return qs.exclude(snapshot="").exclude(snapshot__isnull=True)


def resumen_dataset():
    """Devuelve un dict con el estado del dataset de destilación."""
    eventos = EventoDetectado.objects.all()
    total = eventos.count()

    con_foto = _con_foto(eventos)
    n_con_foto = con_foto.count()

    analizados = con_foto.filter(ia_analizado_en__isnull=False)
    n_analizados = analizados.count()
    n_con_error = analizados.exclude(ia_error="").count()

    # Etiquetados útiles = analizados sin error (su etiqueta es confiable).
    etiquetados = analizados.filter(ia_error="")
    n_etiquetados = etiquetados.count()

    # Positivos: al menos una clase detectada. Negativos ("sin novedad"): cero.
    n_positivos = etiquetados.filter(tipos_ia__isnull=False).distinct().count()
    n_negativos = n_etiquetados - n_positivos

    # Positivos por clase — lo que de verdad decide si se puede entrenar. Se
    # cuenta sobre los etiquetados útiles (con foto y sin error). Son pocas
    # clases, así que una consulta por clase es simple y suficiente.
    por_clase = [
        {"nombre": tipo.nombre, "n": etiquetados.filter(tipos_ia=tipo).distinct().count()}
        for tipo in TipoEventoIA.objects.all()
    ]
    por_clase.sort(key=lambda fila: -fila["n"])

    primero = con_foto.order_by("timestamp").values_list("timestamp", flat=True).first()
    ultimo = con_foto.order_by("-timestamp").values_list("timestamp", flat=True).first()

    return {
        "total_eventos": total,
        "con_foto": n_con_foto,
        "analizados_por_ia": n_analizados,
        "con_error_ia": n_con_error,
        "etiquetados_utiles": n_etiquetados,
        "positivos": n_positivos,
        "negativos": n_negativos,
        "por_clase": por_clase,
        "fecha_primero": primero,
        "fecha_ultimo": ultimo,
    }
