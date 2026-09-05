# Equipo local de Cámaras IA

Programa Python independiente (no es parte de la app Django/Next.js) que
corre en **un PC dedicado en la planta** (no hace falta un DVR/NVR — sirve
cualquier PC o mini-PC común que se deje prendido, conectado a la misma red
que las cámaras IP, por cable o WiFi): se conecta por RTSP a cada cámara,
detecta personas con un modelo liviano de IA (YOLOv8n) y, cuando alguien
aparece dentro de una zona restringida, reporta el evento al backend —que
decide si hay una regla de horario vigente y dispara la alerta (correo, hoy;
WhatsApp, cuando se conecte un proveedor).

Corre como **servicio en segundo plano**: arranca solo con el PC, sin
ventana ni intervención manual — una vez instalado, nadie tiene que volver a
tocarlo.

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
   - Cada frame leído también se guarda a disco (si `GRABAR_VIDEO=true`,
     por defecto) y se cachea como "último frame" para el visor web en
     vivo — ver [Grabaciones y visor en vivo](#grabaciones-y-visor-en-vivo).
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
- Disco libre para las grabaciones — ver [Grabaciones y visor en
  vivo](#grabaciones-y-visor-en-vivo) para el cálculo de espacio.

## Instalación con un clic (recomendado)

Pensado para que lo pueda hacer alguien **sin conocimientos técnicos**,
siempre que el PC ya tenga Python instalado (una sola vez, ver abajo).

1. En el dashboard: sección **Sistema → Equipo local** → **"+ Nuevo
   equipo"** → ponerle un nombre (ej. "Cámaras Planta Tocancipá").
2. En la fila de ese equipo recién creado, botón **"Descargar equipo_local
   (.zip)"** — no hace falta acceso al repositorio de código, y el `.zip`
   ya trae un archivo `.env` completo (URL del backend + `api_key` de ese
   equipo en particular) — no hay que editar ni pegar nada a mano.
3. En el PC de la planta, descomprimir el `.zip` (clic derecho → "Extraer
   todo" en Windows) en cualquier ubicación cómoda.
4. **Windows**: doble clic en **`instalar.bat`**. Va a pedir permiso de
   Administrador (normal, aceptar) y, si es la primera vez, puede tardar
   varios minutos instalando — no hay que hacer nada más, ni cerrar la
   ventana hasta que diga "LISTO".
   **Linux/Mac**: abrir una terminal parado en esta carpeta y correr
   `./instalar.sh`.
5. Con eso queda instalado, corriendo, **y arrancando solo cada vez que se
   prenda el PC** — nadie tiene que volver a tocarlo ni abrir nada
   manualmente. Si alguna vez se necesita reinstalar (ej. después de mover
   la carpeta o cambiar el `.env`), correr el mismo instalador otra vez es
   seguro, no duplica nada.

**Único requisito, de una sola vez en ese PC**: tener Python 3.10+
instalado. Si no lo tiene, el instalador lo avisa con un link de descarga —
en el instalador de Python hay que marcar la casilla *"Add python.exe to
PATH"* antes de darle a Instalar, y después volver a correr `instalar.bat`.

Sigue faltando un paso, que es del dashboard y no de este instalador: dar de
alta cada cámara y dibujar sus zonas restringidas — ver [Configurar las
cámaras y zonas](#configurar-las-cámaras-y-zonas-dashboard) abajo.

## Configurar las cámaras y zonas (dashboard)

1. Cada cámara desde el dashboard (sección **Cámaras**): IP, usuario/
   contraseña ONVIF (se reutilizan como credenciales RTSP), y opcionalmente
   una **URL RTSP** explícita si la cámara no es Dahua o no sigue el patrón
   estándar (`rtsp://usuario:pass@ip:554/cam/realmonitor?channel=1&subtype=1`,
   que es lo que se usa por defecto si el campo queda vacío — ver
   `Camara.rtsp_url_efectiva` en el backend, y la nota sobre la Dahua Picoo
   A2 en `CLAUDE_CAMARAS.md`).
2. Subir el **snapshot de referencia** y dibujar las **zonas restringidas**
   de cada cámara desde el dashboard (sección Cámaras → Zonas y horarios) —
   sin esto el equipo local no tiene contra qué comparar las detecciones.

## Instalación manual / diagnóstico (avanzado)

Para quien prefiera hacerlo paso a paso a mano (o si el instalador de un
clic falla y hace falta ver qué pasa).

### Instalar dependencias

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

### Conseguir el `.env` a mano

Copiar `.env.example` a `.env` en esta misma carpeta y completar
`API_BASE_URL` (URL del backend en Railway, sin `/` final) y `API_KEY`
(botón "Copiar" en Sistema → Equipo local del dashboard, o crear el
registro directo en `/admin/camaras_ia/equipolocal/add/`).

El resto de variables (intervalos, cooldown, confianza mínima, modelo,
grabación, visor web, nivel de log) tienen defaults razonables — ver
`config.py` y `.env.example` si hace falta ajustarlas.

### Probar en primer plano (antes de instalarlo como servicio)

```bash
python -m equipo_local.main
```

La primera vez descarga el modelo `yolov8n.pt` (unos 6MB) automáticamente.
Con logs en `INFO` se debería ver la sincronización inicial, la conexión a
cada cámara y, al caminar alguien por una zona restringida, el reporte del
evento — y aparecer casi al instante en la bandeja de Alertas del dashboard.
`Ctrl+C` para detenerlo limpio.

### Instalar como servicio a mano (arranca solo con el PC)

#### Linux (systemd)

```bash
sudo mkdir -p /opt/sstbavaria-camaras
sudo cp -r . /opt/sstbavaria-camaras/equipo_local
sudo cp .env /opt/sstbavaria-camaras/equipo_local/.env
cd /opt/sstbavaria-camaras/equipo_local && sudo python -m venv venv && sudo ./venv/bin/pip install -r requirements.txt

sudo cp equipo_local/systemd/equipo-local-camaras.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now equipo-local-camaras
sudo systemctl status equipo-local-camaras
journalctl -u equipo-local-camaras -f   # logs en vivo
```

Ajustar las rutas y el `User=` del `.service` si se instala en otro lugar
(`instalar.sh` ya hace este ajuste solo).

#### Windows (Tarea Programada)

1. Instalar y configurar como en "Instalar dependencias"/"Conseguir el
   `.env` a mano" arriba, parado dentro de la carpeta `equipo_local`.
2. Abrir PowerShell **como Administrador** en esa carpeta y correr:

   ```powershell
   .\windows\instalar_tarea_programada.ps1
   ```

3. Esto registra la tarea "SSTBavaria-EquipoLocalCamaras", que arranca sola
   con Windows (sin ventana) y se reinicia sola si el proceso se cae.
   Para iniciarla ya, sin reiniciar el PC: `Start-ScheduledTask -TaskName
   SSTBavaria-EquipoLocalCamaras`. Para ver que esté corriendo: Administrador
   de tareas → pestaña Detalles → buscar `pythonw.exe`.

## Grabaciones y visor en vivo

Además de reportar eventos al backend, el equipo local graba lo que ven las
cámaras en el disco del propio PC (no en la nube — mismo criterio que el
resto del proyecto: nunca sale video crudo a internet) y expone una páginita
web local para verlas en vivo y revisar/borrar lo grabado.

### Dónde quedan las grabaciones

```
equipo_local/grabaciones/<id-de-la-cámara>/<YYYY-MM-DD>/HH-MM-SS.mp4
```

Cada clip dura `GRABACIONES_DURACION_CLIP_MINUTOS` (1 hora por defecto) — así
un archivo nunca crece indefinidamente y es fácil ubicar/borrar lo de un día
puntual. La carpeta base se puede mover a otro disco con `GRABACIONES_DIR`
(ej. un disco externo con más espacio).

**Retención automática**: una vez al día se borran solas las carpetas de
fecha más viejas que `GRABACIONES_RETENCION_DIAS` (15 días por defecto) —
para que el disco no se llene solo. También se puede borrar manualmente por
fecha (y opcionalmente por cámara) desde el visor web, con el botón
"Eliminar por fecha".

**Cálculo de espacio** (orientativo, con los defaults): la grabación usa la
misma frecuencia de captura que la detección (`INTERVALO_DETECCION_SEGUNDOS`,
~2.5 fps), no los 25-30fps del video original — así que el peso por cámara
es bajo. Como referencia, a 3fps y calidad media, una cámara ronda **1-2 GB
por día**; con 10 cámaras y 15 días de retención, calcula unos **150-300 GB**
de uso simultáneo. Ajustar `GRABACIONES_RETENCION_DIAS` (menos días) o
`GRABACIONES_FPS` (menos fps) si el disco del PC es más chico, o desactivar
la grabación por completo con `GRABAR_VIDEO=false` si solo interesan los
eventos/alertas.

### Ver las cámaras en vivo y navegar las grabaciones

Con el equipo local corriendo, abrir en un navegador (desde el mismo PC o
cualquier otro en la misma red de la planta):

```
http://<ip-del-pc-del-equipo-local>:8090
```

(el puerto es `VISOR_WEB_PUERTO`, 8090 por defecto). La página muestra una
grilla con la imagen en vivo de cada cámara activa, y más abajo un buscador
de grabaciones por cámara/fecha con enlace para ver/descargar cada clip y el
botón para eliminar por fecha.

**No sale a internet**: el equipo local no expone puertos públicos — esto
solo es alcanzable desde la red local (o por VPN/escritorio remoto a ese PC
si hace falta verlo desde afuera).

### Nombre en la red en vez de IP

Para no tener que buscar/memorizar la IP cada vez, el equipo local anuncia
un nombre fijo en la red (mDNS/Bonjour, activado por defecto):

```
http://sstbavaria-camaras.local:8090
```

(el nombre es `VISOR_WEB_MDNS_NOMBRE`, configurable — necesario si hay más
de un equipo local en la misma red, cada uno con un nombre distinto).

Soporte según desde dónde se mire, sin instalar nada en el equipo local (la
diferencia es del lado de quien abre el navegador):
- **Mac** y la **mayoría de Linux de escritorio**: funciona directo.
- **Windows**: no resuelve `.local` de fábrica. Dos opciones:
  1. Instalar una vez ["Bonjour Print
     Services"](https://support.apple.com/kb/DL999) (gratis, de Apple) en
     el PC desde el que se va a mirar — después `.local` funciona normal.
  2. Sin instalar nada: usar el **nombre del PC en la red** en vez del
     `.local` — `http://NOMBRE-DEL-PC:8090` suele resolver solo entre
     equipos Windows de la misma red (vía NetBIOS), sin configuración
     adicional. El nombre del PC se ve en Configuración → Sistema → Acerca
     de, o con `hostname` en una consola.

Si ninguna de las dos aplica (o hay dudas), la IP directa siempre funciona
— se consulta en el PC del equipo local con `ipconfig` (Windows) o
`ip addr` (Linux). Para desactivar el anuncio por mDNS:
`VISOR_WEB_MDNS_ACTIVO=false`.

**Autenticación**: si se configuran `VISOR_WEB_USUARIO`/`VISOR_WEB_PASSWORD`
en el `.env`, el visor pide usuario/contraseña (HTTP Basic) antes de dejar
ver nada. Si se dejan vacíos (default), el visor queda abierto a quien esté
en la misma red — solo recomendable si esa red ya es de confianza (la
consola arranca con una advertencia si quedan vacíos, para no pasarlo por
alto). Para desactivar el visor por completo: `VISOR_WEB_ACTIVO=false`.

## Pruebas automatizadas

```bash
cd .. # a la raíz del repo
python -m unittest discover -s equipo_local/tests -t .
```

Cubren la geometría (punto-en-polígono, escalado de coordenadas), el cliente
HTTP (mockeado), la lógica de cooldown/zona de `CamaraMonitor`, la
reconciliación de cámaras activas de `SincronizadorCamaras`, la grabación en
disco y retención (`grabador.py`, con un escritor de video inyectado en los
tests), las rutas del visor web (`visor_web.py`, vía el test client de
Flask) y el anuncio mDNS (`mdns.py`, con `Zeroconf`/`ServiceInfo` mockeados)
— todo sin necesitar cámara, RTSP ni el modelo de IA reales. Lo que sí
requiere hardware/red real para verificar (no se puede probar en este
entorno de desarrollo): conexión RTSP real, calidad de la detección con la
cámara instalada, que el offset de escalado de coordenadas quede bien
calibrado con la resolución real del stream vs. la del snapshot de
referencia, que la codificación de video (`mp4v`) sea compatible con el
códec disponible en el PC de destino, y que `<nombre>.local` resuelva de
verdad en la red de la planta (depende del sistema operativo de quien
mira — ver "Nombre en la red en vez de IP" arriba).

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
