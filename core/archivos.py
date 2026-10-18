import uuid
from pathlib import PurePosixPath


def ruta_no_adivinable(carpeta, filename):
    """Ruta de un archivo subido con una carpeta aleatoria de por medio
    (`carpeta/<32 hex>/<nombre original>`): si el almacenamiento queda con
    URLs públicas (R2_PUBLIC_BASE_URL), nadie puede adivinar la dirección de
    un documento de seguridad social o de la foto de un evento con solo
    probar nombres como "planilla.pdf". Se conserva el nombre original para
    que la descarga se vea igual."""
    return f"{carpeta}/{uuid.uuid4().hex}/{PurePosixPath(filename).name}"
