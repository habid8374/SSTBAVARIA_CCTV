# Entrenar el modelo local de guardas (destilación)

Convierte las fotos que Claude ya clasificó en un modelo local que detecta
**«guarda / puerta de seguridad abierta»** sin gastar API. Una vez bueno, el
equipo local lo usa y Claude queda solo para lo raro.

## 1. Conseguir el dataset
En el servidor (terminal de Coolify):

```
python manage.py exportar_dataset_ia --clase "Guarda" --max-negativos 350
```

Da una **URL de descarga** (vence en 1 hora). Descarga ese `.zip` a tu PC.

## 2. Entrenar en Google Colab (recomendado: GPU gratis, no toca la planta)
1. Abre <https://colab.research.google.com> → **Nuevo notebook**.
2. Menú **Entorno de ejecución → Cambiar tipo de entorno → GPU** (T4) → Guardar.
3. Sube el `.zip` (panel izquierdo, ícono de carpeta → subir) y sube también
   `entrenar_guardas.py` (este archivo, de esta carpeta).
4. En una celda, corre:
   ```
   !pip install ultralytics
   !python entrenar_guardas.py --zip guarda_o_puerta_de_seguridad_abierta_*.zip
   ```
   (ajusta el nombre del zip al que subiste)
5. Tarda ~10-20 min. Al terminar, descarga el modelo:
   `runs/classify/guardas/weights/best.pt`

## 3. Entrenar en un PC con GPU (alternativa)
```
pip install ultralytics
python entrenar_guardas.py --zip guarda_....zip
```
El PC de planta (RTX 3050) sirve; mejor de noche o fin de semana para no
competir con la vigilancia.

## 4. Leer los resultados
En `runs/classify/guardas/` quedan:
- **`weights/best.pt`** → el modelo (esto es lo que se integra al equipo local).
- **`confusion_matrix.png`** → cuántas guardas acertó / falló en validación.
- **`results.png`** → curvas de entrenamiento.

Mándame la **matriz de confusión** y la **accuracy** de validación: con eso
decidimos si el modelo ya está para ponerlo en «modo sombra» (corre junto a
Claude y comparamos) o si hay que ajustar / juntar más ejemplos.

## Notas
- El ZIP trae `positivos/` y `negativos/`; el script los reparte solo en
  train/val (80/20).
- 372 positivos + 350 negativos es un primer dataset razonable; si la accuracy
  queda floja, se acumulan más semanas y se reentrena (el comando de exportar
  se vuelve a correr y ya).
