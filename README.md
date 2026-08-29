# SSTBAVARIA_CCTV — Módulo de Videovigilancia con IA

Backend Django (proyecto independiente) del módulo de Cámaras IA. Fase 1:
modelo de datos + panel de administración para registrar lo levantado en la
visita a planta (cámaras, zonas restringidas, horarios de alerta). Todavía
**sin conexión real a cámaras** — eso es la Fase 2.

Ver `CLAUDE_CAMARAS.md` para el contexto completo del proyecto.

## Apps

- `core/` — modelo `Empresa` (tenant).
- `camaras_ia/` — `Camara`, `EquipoLocal`, `ZonaRestringida`, `ReglaAlerta`,
  `EventoDetectado`, y el endpoint stub `POST /api/camaras-ia/eventos/`.

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

### Probar el endpoint stub

El endpoint valida la API key del `EquipoLocal` por el header `X-API-Key` y
responde `201` (todavía no guarda el evento ni evalúa zona/horario — eso es
Fase 2).

```bash
curl -X POST http://127.0.0.1:8000/api/camaras-ia/eventos/ \
  -H "X-API-Key: <api_key de un EquipoLocal creado en el admin>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Sin API key válida responde `401`.

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

El disco de Railway no es persistente entre despliegues. Para Fase 1 (sin
eventos reales todavía) esto no es un problema; antes de que el endpoint
real de Fase 2 empiece a recibir snapshots en producción, hay que decidir
un storage externo (S3 u otro) — es una decisión de alcance/costo aparte,
no un default de esta fase.
