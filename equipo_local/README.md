# Equipo local de Cámaras IA

Programa Python independiente (no es parte de la app Django/Next.js) que
corre en el PC del DVR/NVR en la planta: se conecta por RTSP a cada cámara,
detecta personas con un modelo liviano de IA (YOLOv8n) y, cuando alguien
aparece dentro de una zona restringida, reporta el evento al backend —que
decide si hay una regla de horario vigente y dispara la alerta (correo, hoy;
WhatsApp, cuando se conecte un proveedor).

Corre como **servicio en segundo plano**: arranca solo con el PC, sin
ventana ni intervención manual, igual que un NVR/DVR real.

## Cómo funciona

1. Al arrancar, y cada `INTERVALO_SYNC_SEGUNDOS` (60s por defecto), pide al
   backend `GET /api/camaras-ia/reglas-activas/` — la lista de cámaras
   activas de su empresa, cada una con su URL RTSP ya resuelta, su snapshot
   de referencia y sus zonas (con el polígono en píxeles de esa referencia).
2. Por cada cámara activa mantiene un hilo (`CamaraMonitor`) que:
   - Se conecta al stream RTSP y lee frames.
   - Cada `INTERVALO_DETECCION_SEGUNDOS` (0.4s por defecto — no hace falta
     analizar los 25-30 fps del video) corre el detector de personas.
   - Por cada persona detectada, escala su posición del tamaño del frame
     RTSP al tamaño del snapshot de referencia (para que las coordenadas
     coincidan con las de los polígonos de zona dibujados en el dashboard),
     y revisa si cae dentro de alguna zona conocida.
   - Si cae dentro de una zona y ya pasó el `COOLDOWN_ZONA_SEGUNDOS` (60s
     por defecto) desde el último reporte de esa misma zona, reporta el
     evento: `POST /api/camaras-ia/eventos/` con el punto detectado y un
     snapshot JPEG del frame.
3. El backend decide si el punto realmente cae en una zona activa con
   horario vigente y dispara la alerta — acá no se duplica esa lógica, el
   equipo local solo pre-filtra localmente para no gastar ancho de banda
   subiendo snapshots de detecciones obviamente fuera de cualquier zona.
4. Si una cámara se desactiva o se le borra alguna zona desde el dashboard,
   el siguiente ciclo de sincronización lo refleja solo, sin reiniciar el
   programa.

## Requisitos del PC

- Python 3.10+.
- CPU con algo de músculo — YOLOv8n corre bien en CPU en un PC de escritorio
  normal (no hace falta GPU, aunque si hay una, ultralytics la aprovecha
  sola si está bien configurado CUDA/PyTorch).
- Acceso de red a las cámaras (RTSP, puerto 554 típicamente) y al backend
  (HTTPS saliente).

## Instalación

```bash
cd equipo_local
python -m venv venv

# Linux/Mac
source venv/bin/activate
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

> **Nota sobre `ultralytics`**: trae `opencv-python` (con GUI) como
> dependencia propia, que puede pisar el `opencv-python-headless` de este
> `requirements.txt` al instalar. No es un problema funcional — si se quiere
> evitar el peso extra de los bindings de GUI en un servidor sin pantalla,
> reinstalar después con `pip install --force-reinstall opencv-python-headless`.

## Configuración

1. Crear el registro de este equipo en el admin de Django:
   `/admin/camaras_ia/equipolocal/add/` — nombre descriptivo (ej. "NVR Planta
   Tocancipá") y guardar. Django genera la `api_key` sola; copiarla.
2. Copiar `.env.example` a `.env` en esta misma carpeta y completar:

   | Variable | Valor |
   |---|---|
   | `API_BASE_URL` | URL del backend en Railway (sin `/` final) |
   | `API_KEY` | la que generó el paso 1 |

   El resto de variables (intervalos, cooldown, confianza mínima, modelo,
   nivel de log) tienen defaults razonables — ver `config.py` y
   `.env.example` si hace falta ajustarlas.
3. Configurar cada cámara desde el dashboard (sección **Cámaras**): IP,
   usuario/contraseña ONVIF (se reutilizan como credenciales RTSP), y opcio-
   nalmente una **URL RTSP** explícita si la cámara no es Dahua o no sigue
   el patrón estándar (`rtsp://usuario:pass@ip:554/cam/realmonitor?channel=1&subtype=1`,
   que es lo que se usa por defecto si el campo queda vacío — ver
   `Camara.rtsp_url_efectiva` en el backend, y la nota sobre la Dahua Picoo
   A2 en `CLAUDE_CAMARAS.md`).
4. Subir el **snapshot de referencia** y dibujar las **zonas restringidas**
   de cada cámara desde el dashboard (sección Cámaras → Zonas y horarios) —
   sin esto el equipo local no tiene contra qué comparar las detecciones.

## Probar en primer plano (antes de instalarlo como servicio)

```bash
python -m equipo_local.main
```

La primera vez descarga el modelo `yolov8n.pt` (unos 6MB) automáticamente.
Con logs en `INFO` se debería ver la sincronización inicial, la conexión a
cada cámara y, al caminar alguien por una zona restringida, el reporte del
evento — y aparecer casi al instante en la bandeja de Alertas del dashboard.
`Ctrl+C` para detenerlo limpio.

## Instalar como servicio (arranca solo con el PC)

### Linux (systemd)

```bash
sudo mkdir -p /opt/sstbavaria-camaras
sudo cp -r . /opt/sstbavaria-camaras/equipo_local
sudo cp .env /opt/sstbavaria-camaras/.env
cd /opt/sstbavaria-camaras && sudo python -m venv venv && sudo ./venv/bin/pip install -r equipo_local/requirements.txt

sudo cp equipo_local/systemd/equipo-local-camaras.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now equipo-local-camaras
sudo systemctl status equipo-local-camaras
journalctl -u equipo-local-camaras -f   # logs en vivo
```

Ajustar las rutas y el `User=` del `.service` si se instala en otro lugar.

### Windows (Tarea Programada)

1. Instalar y configurar como en "Instalación"/"Configuración" arriba,
   parado dentro de la carpeta `equipo_local`.
2. Abrir PowerShell **como Administrador** en esa carpeta y correr:

   ```powershell
   .\windows\instalar_tarea_programada.ps1
   ```

3. Esto registra la tarea "SSTBavaria-EquipoLocalCamaras", que arranca sola
   con Windows (sin ventana) y se reinicia sola si el proceso se cae.
   Para iniciarla ya, sin reiniciar el PC: `Start-ScheduledTask -TaskName
   SSTBavaria-EquipoLocalCamaras`. Para ver que esté corriendo: Administrador
   de tareas → pestaña Detalles → buscar `pythonw.exe`.

## Pruebas automatizadas

```bash
cd .. # a la raíz del repo
python -m unittest discover -s equipo_local/tests -t .
```

Cubren la geometría (punto-en-polígono, escalado de coordenadas), el cliente
HTTP (mockeado), la lógica de cooldown/zona de `CamaraMonitor`, y la
reconciliación de cámaras activas de `SincronizadorCamaras` — todo sin
necesitar cámara, RTSP ni el modelo de IA reales. Lo que sí requiere hardware
real para verificar (no se puede probar en este entorno de desarrollo):
conexión RTSP real, calidad de la detección con la cámara instalada, y que
el offset de escalado de coordenadas quede bien calibrado con la resolución
real del stream vs. la del snapshot de referencia.

## Notas de diseño

- **Por qué no ONVIF**: la investigación sobre la Dahua Picoo A2 (ver
  `CLAUDE_CAMARAS.md`) encontró que probablemente no soporta ONVIF — por
  eso el equipo local usa RTSP directo en vez de comandos ONVIF, y el campo
  `rtsp_url` de `Camara` existe para poder anular el patrón por defecto si
  se usa otra marca.
- **subtype=1 (substream)** por defecto en la URL RTSP: menor resolución y
  bitrate que el canal principal, mucho más liviano para correr detección
  en tiempo real. Se puede forzar el canal principal con una `rtsp_url`
  explícita si hace falta más detalle.
- **Por qué el backend decide zona+horario, no el equipo local**: esa
  lógica (`evaluar_zona_horario` en `camaras_ia/services.py`) ya existía y
  está testeada; duplicarla acá sería mantener la misma regla en dos
  lenguajes/lugares. El equipo local pre-filtra localmente solo para no
  desperdiciar ancho de banda, no como fuente de verdad.
