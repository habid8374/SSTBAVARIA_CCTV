"""Imprime el estado del dataset acumulado para destilar la IA a un modelo
local. Uso:  python manage.py analizar_dataset_ia
"""

from django.core.management.base import BaseCommand

from camaras_ia.dataset_ia import UMBRAL_ENTRENABLE, UMBRAL_INSUFICIENTE, resumen_dataset


class Command(BaseCommand):
    help = "Analiza cuántos ejemplos etiquetados por la IA hay para entrenar un modelo local (destilación)."

    def handle(self, *args, **opciones):
        r = resumen_dataset()

        def linea(texto=""):
            self.stdout.write(texto)

        linea("=" * 56)
        linea("  Análisis del dataset de IA (destilación)")
        linea("=" * 56)

        if r["fecha_primero"] and r["fecha_ultimo"]:
            dias = (r["fecha_ultimo"] - r["fecha_primero"]).days + 1
            linea(f"Rango: {r['fecha_primero']:%Y-%m-%d} a {r['fecha_ultimo']:%Y-%m-%d}  ({dias} días)")
        linea()
        linea(f"Eventos totales ........... {r['total_eventos']:>7}")
        linea(f"  Con foto (entrenables) .. {r['con_foto']:>7}")
        linea(f"  Analizados por IA ....... {r['analizados_por_ia']:>7}")
        linea(f"    - con error de IA ..... {r['con_error_ia']:>7}")
        linea(f"  Etiquetados útiles ...... {r['etiquetados_utiles']:>7}")
        linea(f"    - positivos (≥1 clase)  {r['positivos']:>7}   <- lo valioso")
        linea(f"    - negativos (sin nov.)  {r['negativos']:>7}")
        linea()
        linea("Positivos por clase:")
        if not r["por_clase"]:
            linea("  (todavía no hay clases/eventos clasificados)")
        for fila in r["por_clase"]:
            n = fila["n"]
            if n >= UMBRAL_ENTRENABLE:
                marca = "✓ listo"
            elif n >= UMBRAL_INSUFICIENTE:
                marca = "~ justo"
            else:
                marca = "✗ faltan"
            linea(f"  {fila['nombre'][:34]:<34} {n:>6}   {marca}")
        linea()

        listas = [f for f in r["por_clase"] if f["n"] >= UMBRAL_ENTRENABLE]
        linea("Veredicto:")
        if listas:
            nombres = ", ".join(f["nombre"] for f in listas)
            linea(f"  Ya se puede entrenar un primer modelo para: {nombres}")
        else:
            linea(f"  Aún no hay ninguna clase con {UMBRAL_ENTRENABLE}+ ejemplos: conviene seguir acumulando.")
        linea("=" * 56)
