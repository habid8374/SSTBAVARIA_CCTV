# SSTBAVARIA_CCTV — Módulo de Videovigilancia con IA

Monorepo del módulo de Cámaras IA: backend Django (raíz del repo) + dashboard
Next.js (`frontend/`). Se despliegan por separado — el backend en Railway, el
frontend en Vercel — pero viven en el mismo repositorio.

- **Fase 1** (completa): modelo de datos + panel de administración para
  registrar lo levantado en la visita a planta (cámaras, zonas restringidas,
  horarios de alerta).
- **Fase 2** (completa, solo el lado del backend): cruce zona+horario,
  disparo de alerta (stub con logging) y sincronización de reglas para el
  equipo local. La conexión ONVIF/RTSP/PTZ real contra las cámaras en sitio
  es un desarrollo aparte del lado del equipo local, no de este backend —
  ver "Qué hace este módulo" en `CLAUDE_CAMARAS.md`.
- **Dashboard** (login + gestión de usuarios, completo): panel Next.js con
  login corporativo, navegación por sidebar (sin URLs sueltas por sección) y
  gestión de usuarios con roles (Administrador/Operador). Las secciones de
  Cámaras, Zonas y Alertas están en el sidebar como "Pronto" — la Fase 4
  (dibujar zonas, tablero de indicadores) todavía no se ha construido.

Ver `CLAUDE_CAMARAS.md` para el contexto completo del proyecto.

## Estructura

- `core/` — modelo `Empresa` (tenant), autenticación del dashboard (login
  por token, perfil, gestión de usuarios con rol) — ver endpoints abajo.
- `camaras_ia/` — modelos `Camara`, `EquipoLocal`, `ZonaRestringida`,
  `ReglaAlerta`, `EventoDetectado`; lógica de negocio en `services.py`
  (`punto_en_poligono`, `evaluar_zona_horario`, `disparar_alerta`); y los
  endpoints de API descritos abajo.
- `frontend/` — dashboard Next.js (App Router + TypeScript + Tailwind),
  instalable como PWA. Ver su propia sección más abajo.

## Backend — correr en local

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

Admin en `http://127.0.0.1:8000/admin/`. En `DEBUG=True` el backend ya
acepta llamadas CORS desde `http://localhost:3000` (el frontend) sin
configurar nada más.

### Login del dashboard, perfil y gestión de usuarios

Estos endpoints los usa el frontend — no el equipo local (que usa su propia
API key, ver más abajo). El primer usuario (`createsuperuser`) recibe
automáticamente el rol **Administrador**; todo usuario creado después desde
el dashboard o el admin recibe **Operador** por defecto y el administrador
le puede cambiar el rol.

- **`POST /api/auth/login/`** — `{"username", "password"}` → `{"token", "usuario"}`.
- **`POST /api/auth/logout/`** — invalida el token actual (header `Authorization: Token <token>`).
- **`GET /api/auth/perfil/`** — datos del usuario autenticado (incluye `rol`).
- **`GET /api/auth/resumen/`** — conteos para la pantalla inicial (cámaras activas, eventos nuevos, alertas hoy).
- **`GET/POST /api/auth/usuarios/`** y **`GET/PATCH/DELETE /api/auth/usuarios/<id>/`** —
  gestión de usuarios. Solo Administradores; un usuario no puede desactivarse
  ni eliminarse a sí mismo.

Todos (salvo login) requieren el header `Authorization: Token <token>`.

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

## Frontend — correr en local

Requiere Node.js 20+. El dashboard es una SPA con sidebar (no hay rutas por
sección: `/login` y `/dashboard` son las únicas dos páginas reales).

```bash
cd frontend
npm install
cp .env.example .env.local
# .env.local: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 (o la URL de Railway)
npm run dev
```

Abre `http://localhost:3000` (redirige a `/login`). Con el backend corriendo
en local (`DEBUG=True`), el login ya funciona con el superusuario que hayas
creado ahí.

- **Roles**: el primer usuario (`createsuperuser`) es Administrador y ve la
  sección "Usuarios" en el sidebar; desde ahí crea al resto del equipo con
  su rol (Administrador u Operador) — no hay pantalla de registro público.
- **Responsive**: sidebar fijo y colapsable en desktop, drawer deslizante en
  móvil/tablet (botón de menú en el header).
- **PWA**: `manifest.json` + `sw.js` (`frontend/public/`) hacen el dashboard
  instalable en el celular ("Agregar a pantalla de inicio" / prompt de
  instalación de Chrome). El service worker solo cachea páginas y estáticos
  propios — las llamadas a la API del backend nunca se sirven desde cache,
  siempre van a la red.

## Desplegar el backend en Railway

1. Crear un proyecto nuevo en Railway (plan Trial para probar) y conectarlo
   a este repositorio. **Root Directory**: dejar el default (raíz del repo)
   — el backend vive ahí, `frontend/` no le afecta.
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
   | `CORS_ALLOWED_ORIGINS` | el dominio de Vercel del frontend, ej. `https://sstbavaria-cctv.vercel.app` (agrega también el dominio de preview si lo vas a usar) |
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

   Este es tu único usuario Administrador de arranque — desde el dashboard
   (sección Usuarios) creas a todo el resto del equipo con su rol.
6. Entrar a `https://<dominio>/admin/` y cargar ahí las cámaras, zonas y
   reglas levantadas en la visita a planta.

## Desplegar el frontend en Vercel

1. Importar el mismo repositorio de GitHub como un proyecto nuevo en Vercel.
2. En la configuración del proyecto (**Settings → General → Root
   Directory**), cambiarlo a `frontend` — es el paso que le dice a Vercel
   que el Next.js está en un subdirectorio, no en la raíz del repo. Vercel
   detecta Next.js automáticamente y no hace falta tocar build/install
   command.
3. Variables de entorno del proyecto (Settings → Environment Variables):

   | Variable | Valor |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | la URL pública del backend en Railway, ej. `https://sstbavaria-cctv-production.up.railway.app` (sin barra al final) |

4. Deploy. Vercel te da un dominio `https://<proyecto>.vercel.app` — ese es
   el que hay que poner en `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS`
   del backend en Railway (paso anterior) para que el login funcione en
   producción. Si luego agregas un dominio propio en Vercel, súmalo también
   ahí.
5. Entra a `https://<tu-dominio-vercel>/login` con el superusuario creado en
   el paso 5 de Railway.

**Orden recomendado**: despliega primero el backend en Railway (para tener
su dominio), después el frontend en Vercel con `NEXT_PUBLIC_API_URL`
apuntando a ese dominio, y por último vuelve a Railway a completar
`CORS_ALLOWED_ORIGINS`/`CSRF_TRUSTED_ORIGINS` con el dominio de Vercel ya
generado.

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
