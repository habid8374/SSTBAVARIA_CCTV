# SSTBAVARIA_CCTV — Módulo de Videovigilancia con IA

Backend Django (proyecto independiente) del módulo de Cámaras IA.

- **Fase 1** (completa): modelo de datos + panel de administración para
  registrar lo levantado en la visita a planta (cámaras, zonas restringidas,
  horarios de alerta).
- **Fase 2** (completa, solo el lado del backend): cruce zona+horario,
  disparo de alerta (stub con logging) y sincronización de reglas para el
  equipo local. La conexión ONVIF/RTSP/PTZ real contra las cámaras en sitio
  es un desarrollo aparte del lado del equipo local, no de este backend —
  ver "Qué hace este módulo" en `CLAUDE_CAMARAS.md`.

Ver `CLAUDE_CAMARAS.md` para el contexto completo del proyecto.

## Apps

- `core/` — modelo `Empresa` (tenant).
- `camaras_ia/` — modelos `Camara`, `EquipoLocal`, `ZonaRestringida`,
  `ReglaAlerta`, `EventoDetectado`; lógica de negocio en `services.py`
  (`punto_en_poligono`, `evaluar_zona_horario`, `disparar_alerta`); y los
  endpoints de API descritos abajo.

## Correr en local

Sin `.env`: todo se exporta a mano en la terminal antes de levantar el
proyecto.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="una-clave-cualquiera-para-desarrollo"
export DEBUG=True
export ALLOWED_HOSTS="localhost,127.0.0.1"
# Sin DATABASE_URL usa sqlite3 local automáticamente.
# Para usar Postgres local:
# export DATABASE_URL="postgres://usuario:password@localhost:5432/camaras_ia"

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Admin en `http://127.0.0.1:8000/admin/`.

### Endpoints de API (autenticados por API key de `EquipoLocal`)

Ambos endpoints validan el header `X-API-Key` contra un `EquipoLocal` activo
y responden `401` si falta o es inválida.

**`POST /api/camaras-ia/eventos/`** — el equipo local reporta un evento de
movimiento: a qué cámara, en qué punto (mismo sistema de coordenadas del
polígono de la zona) y opcionalmente una foto. El backend cruza el punto
contra las zonas restringidas de la cámara y las reglas de horario vigentes
en este momento; si aplica una regla, marca el evento como disparo de
alerta y llama a `disparar_alerta` (por ahora solo registra el intento en
el log — sin proveedor real de WhatsApp/correo todavía).

```bash
curl -X POST http://127.0.0.1:8000/api/camaras-ia/eventos/ \
  -H "X-API-Key: <api_key de un EquipoLocal creado en el admin>" \
  -F "camara=<id de la cámara>" \
  -F "punto_x=120" \
  -F "punto_y=340" \
  -F "snapshot=@foto.jpg"
```

Responde `201` con `{"id", "zona", "disparo_alerta"}`. Si la cámara no
pertenece a la empresa del equipo, responde `403`.

**`GET /api/camaras-ia/reglas-activas/`** — el equipo local consulta esto
periódicamente para sincronizar qué cámaras/zonas/horarios debe vigilar,
sin tocar el equipo físicamente. Devuelve solo cámaras, zonas y reglas
activas de la empresa del equipo (incluye credenciales ONVIF de cada
cámara, que el equipo local necesita para conectarse).

```bash
curl http://127.0.0.1:8000/api/camaras-ia/reglas-activas/ \
  -H "X-API-Key: <api_key de un EquipoLocal creado en el admin>"
```

## Desplegar en Railway

1. Crear un proyecto nuevo en Railway (plan Trial para probar) y conectarlo
   a este repositorio.
2. Agregar un servicio PostgreSQL desde el marketplace de Railway — Railway
   inyecta `DATABASE_URL` automáticamente al servicio web si quedan en el
   mismo proyecto.
3. En el servicio web, configurar estas variables de entorno (Settings →
   Variables):

   | Variable | Valor |
   |---|---|
   | `SECRET_KEY` | una clave secreta larga y aleatoria (generar una nueva, no reusar la de local) |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | el dominio que asigna Railway, ej. `sstbavaria-cctv-production.up.railway.app` |
   | `CSRF_TRUSTED_ORIGINS` | `https://<mismo-dominio-de-arriba>` |
   | `DATABASE_URL` | la inyecta Railway automáticamente al agregar Postgres |

4. Railway detecta `railway.json` (build con Nixpacks) y corre
   automáticamente `migrate`, `collectstatic` y levanta `gunicorn` según el
   `startCommand` definido ahí. El `Procfile` queda como alternativa si se
   despliega el mismo repo en otra plataforma tipo Heroku.
5. Crear el superusuario en producción una sola vez desde la consola de
   Railway del servicio:

   ```bash
   python manage.py createsuperuser
   ```

6. Entrar a `https://<dominio>/admin/` y cargar ahí las cámaras, zonas y
   reglas levantadas en la visita a planta.

### Nota sobre `media/` (fotos de eventos)

El disco de Railway no es persistente entre despliegues. Ahora que el
endpoint de eventos ya guarda snapshots de verdad, antes de recibir eventos
reales en producción hay que decidir un storage externo (S3 u otro) — es
una decisión de alcance/costo aparte, no un default de esta fase.

### Nota sobre `disparar_alerta`

Por ahora es un stub: registra el intento de notificación en el log
(`camaras_ia.alertas`) pero no envía WhatsApp/correo de verdad. Conectar un
proveedor real (o el sistema de notificaciones del proyecto principal, vía
API) es una decisión de proveedor aparte, todavía no tomada.
