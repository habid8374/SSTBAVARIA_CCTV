"""Análisis del dataset acumulado para destilar la IA (Claude) a un modelo
local (YOLO/clasificador).

Cada EventoDetectado con foto (`snapshot`) y ya analizado por Claude
(`ia_analizado_en`, `tipos_ia`) es un ejemplo etiquetado "gratis": la foto es
la entrada y lo que Claude detectó es la etiqueta. Esta función cuenta cuántos
ejemplos hay, cuántos son positivos de cada clase y cómo está el balance, para
decidir si ya se puede entrenar un primer modelo o si falta acumular.
"""

import csv
import io
import zipfile

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


def slug_clase(texto):
    """Nombre de carpeta/archivo seguro a partir del nombre de la clase."""
    limpio = "".join(c if c.isalnum() else "_" for c in texto.lower())
    return limpio.strip("_")[:40] or "clase"


def construir_zip_dataset(clase_nombre, max_negativos=None):
    """Arma en memoria un ZIP con las fotos POSITIVAS de la clase indicada y una
    muestra balanceada de NEGATIVOS (sin novedad), listo para entrenar un
    clasificador "¿<clase>: sí/no?". Estructura:
        positivos/evento_<id>.jpg
        negativos/evento_<id>.jpg
        manifiesto.csv   (evento_id, etiqueta, cámara, timestamp, archivo)

    Devuelve (bytes_del_zip, estadísticas). Cada foto se baja del almacenamiento
    (R2/S3); una que falle se cuenta como "fallida" y se omite, sin romper la
    exportación.
    """
    clase = TipoEventoIA.objects.filter(nombre__icontains=clase_nombre).first()
    if clase is None:
        raise ValueError(f"No hay ninguna clase de IA cuyo nombre contenga «{clase_nombre}».")

    etiquetados = _con_foto(EventoDetectado.objects.filter(ia_analizado_en__isnull=False, ia_error=""))
    positivos = list(etiquetados.filter(tipos_ia=clase).distinct().select_related("camara"))
    if max_negativos is None:
        max_negativos = len(positivos) * 2  # 2 negativos por cada positivo
    negativos = list(
        etiquetados.filter(tipos_ia__isnull=True).select_related("camara").order_by("?")[:max_negativos]
    )

    stats = {"clase": clase.nombre, "positivos": 0, "negativos": 0, "fallidos": 0}
    filas = []
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for etiqueta, grupo in (("positivos", positivos), ("negativos", negativos)):
            for evento in grupo:
                try:
                    evento.snapshot.open("rb")
                    datos = evento.snapshot.read()
                except Exception:
                    stats["fallidos"] += 1
                    continue
                finally:
                    try:
                        evento.snapshot.close()
                    except Exception:
                        pass
                if not datos:
                    stats["fallidos"] += 1
                    continue
                archivo = f"{etiqueta}/evento_{evento.pk}.jpg"
                zf.writestr(archivo, datos)
                filas.append(
                    [evento.pk, etiqueta, evento.camara.nombre, evento.timestamp.isoformat(), archivo]
                )
                stats[etiqueta] += 1

        manifiesto = io.StringIO()
        escritor = csv.writer(manifiesto)
        escritor.writerow(["evento_id", "etiqueta", "camara", "timestamp", "archivo"])
        escritor.writerows(filas)
        zf.writestr("manifiesto.csv", manifiesto.getvalue())

    buffer.seek(0)
    return buffer.getvalue(), stats
