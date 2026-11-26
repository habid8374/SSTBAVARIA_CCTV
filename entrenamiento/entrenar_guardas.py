"""Entrena un clasificador local «guarda abierta: sí/no» destilado de Claude.

La idea (ver camaras_ia/dataset_ia.py): cada foto que Claude ya clasificó es un
ejemplo etiquetado. Con ese dataset entrenamos un modelo local que, una vez
bueno, hace el trabajo sin gastar API.

Se usa YOLOv8 en modo CLASIFICACIÓN (ultralytics) a propósito: es la misma
librería que ya corre el equipo local, así que el modelo .pt resultante se
carga ahí sin adaptar nada.

Uso (en Google Colab o en cualquier PC con Python y, ojalá, GPU):

    pip install ultralytics
    python entrenar_guardas.py --zip guarda_....zip

Al terminar, el modelo queda en:
    runs/classify/guardas/weights/best.pt

El dataset del ZIP (carpetas positivos/ y negativos/) se reparte solo en
train/ y val/ (80/20) con la estructura que ultralytics espera.
"""

import argparse
import random
import shutil
import zipfile
from pathlib import Path


def preparar_dataset(zip_path, destino, val_frac=0.2, semilla=42):
    """Descomprime el ZIP y reorganiza positivos/ y negativos/ en
    train/<clase> y val/<clase>, como pide `yolo classify`."""
    destino = Path(destino)
    if destino.exists():
        shutil.rmtree(destino)
    crudo = destino / "_crudo"
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(crudo)

    random.seed(semilla)
    resumen = {}
    for clase in ("positivos", "negativos"):
        fotos = sorted((crudo / clase).glob("*.jpg"))
        random.shuffle(fotos)
        n_val = max(1, int(len(fotos) * val_frac)) if fotos else 0
        for i, foto in enumerate(fotos):
            split = "val" if i < n_val else "train"
            carpeta = destino / split / clase
            carpeta.mkdir(parents=True, exist_ok=True)
            shutil.copy(foto, carpeta / foto.name)
        resumen[clase] = {"total": len(fotos), "val": n_val, "train": len(fotos) - n_val}

    shutil.rmtree(crudo, ignore_errors=True)
    return destino, resumen


def main():
    parser = argparse.ArgumentParser(description="Entrena el clasificador de guardas (destilación).")
    parser.add_argument("--zip", required=True, help="Ruta del ZIP exportado (positivos/ y negativos/).")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--img", type=int, default=224, help="Tamaño de imagen (224 va bien para clasificar).")
    parser.add_argument("--modelo-base", default="yolov8n-cls.pt", help="Modelo base de ultralytics.")
    args = parser.parse_args()

    datos, resumen = preparar_dataset(args.zip, "dataset_guardas")
    print("Dataset preparado:")
    for clase, n in resumen.items():
        print(f"  {clase:<10} total={n['total']}  train={n['train']}  val={n['val']}")
    print(f"Carpeta: {datos.resolve()}\n")

    from ultralytics import YOLO  # noqa: PLC0415 (import perezoso: solo hace falta al entrenar)

    modelo = YOLO(args.modelo_base)
    modelo.train(
        data=str(datos.resolve()),
        epochs=args.epochs,
        imgsz=args.img,
        name="guardas",
        project="runs/classify",
    )
    print("\n=== LISTO ===")
    print("Modelo entrenado en: runs/classify/guardas/weights/best.pt")
    print("Métricas y matriz de confusión en: runs/classify/guardas/")


if __name__ == "__main__":
    main()
