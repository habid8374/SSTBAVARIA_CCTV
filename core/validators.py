from django.core.exceptions import ValidationError

MAX_UPLOAD_MB = 10


def validar_tamano_archivo(archivo):
    """Evita que un archivo subido agote disco/memoria (abuso de
    almacenamiento o denegación de servicio) — se aplica además de la
    validación de tipo/contenido que ya hace ImageField/FileExtensionValidator."""
    limite = MAX_UPLOAD_MB * 1024 * 1024
    if archivo.size > limite:
        raise ValidationError(
            f"El archivo no debe superar los {MAX_UPLOAD_MB} MB "
            f"(tiene {archivo.size / 1024 / 1024:.1f} MB)."
        )
