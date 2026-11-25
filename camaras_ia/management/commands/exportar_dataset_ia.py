"""Exporta un ZIP con las fotos de una clase (positivos) + una muestra de
negativos, listo para entrenar un clasificador local (destilación).

Ejemplos:
  python manage.py exportar_dataset_ia --clase "Guarda"
  python manage.py exportar_dataset_ia --clase "Guarda" --max-negativos 400
  python manage.py exportar_dataset_ia --clase "Guarda" --salida /tmp/guardas.zip

Sin --salida, el ZIP se sube al almacenamiento (R2/S3) y se imprime la URL de
descarga.
"""

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from camaras_ia.dataset_ia import construir_zip_dataset, slug_clase


class Command(BaseCommand):
    help = "Exporta a un ZIP las fotos etiquetadas de una clase (positivos + negativos) para entrenar."

    def add_arguments(self, parser):
        parser.add_argument("--clase", required=True, help="Nombre (o parte) de la clase a exportar.")
        parser.add_argument(
            "--max-negativos", type=int, default=0, help="Cuántos negativos incluir (0 = el doble de positivos)."
        )
        parser.add_argument("--salida", default="", help="Ruta local del ZIP. Vacío = subir al almacenamiento.")

    def handle(self, *args, **opciones):
        try:
            datos, stats = construir_zip_dataset(opciones["clase"], opciones["max_negativos"] or None)
        except ValueError as err:
            raise CommandError(str(err)) from err

        self.stdout.write(f"Clase: {stats['clase']}")
        self.stdout.write(
            f"Positivos: {stats['positivos']}   Negativos: {stats['negativos']}   "
            f"Fotos no descargables: {stats['fallidos']}"
        )
        self.stdout.write(f"Tamaño del ZIP: {len(datos) // 1024} KB")

        if stats["positivos"] == 0:
            raise CommandError("No se exportó ningún positivo — revisa el nombre de la clase o que tengan foto.")

        if opciones["salida"]:
            with open(opciones["salida"], "wb") as archivo:
                archivo.write(datos)
            self.stdout.write(self.style.SUCCESS(f"Guardado en {opciones['salida']}"))
        else:
            ruta = f"datasets/{slug_clase(stats['clase'])}_{timezone.now():%Y%m%d_%H%M}.zip"
            nombre = default_storage.save(ruta, ContentFile(datos))
            self.stdout.write(self.style.SUCCESS(f"Subido al almacenamiento: {nombre}"))
            try:
                self.stdout.write(f"URL de descarga: {default_storage.url(nombre)}")
            except Exception:
                self.stdout.write("(El almacenamiento no genera URL directa — descárgalo desde el panel de R2.)")
