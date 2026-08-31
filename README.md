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
- **Dashboard** (completo): panel Next.js con login corporativo, navegación
  por sidebar (sin URLs sueltas por sección) y gestión de usuarios con roles
  (Administrador/Operador). Incluye ya la Fase 4 (panel en el dashboard):
  Tablero de indicadores, Cámaras IA con overlays de zona sobre el último
  snapshot, editor visual de Zonas y horarios (dibujar el polígono haciendo
  clic sobre el encuadre de referencia), y la bandeja de Alertas.
- **Contratistas y Declaración de Método** (completo): dos módulos de
  cumplimiento SST para el personal de empresas contratistas, digitalizando
  el proceso manual (Excel/PDF) que ya usa el cliente:
  - **Contratistas**: empresas contratistas, su personal (con EPS/ARL/AFP y
    cursos Safety Academy) y la radicación mensual del soporte de pago de
    seguridad social (planilla PILA), con aprobación/rechazo por un
    interventor.
  - **Declaración de Método**: formulario dinámico de secuencia de
    actividades con evaluación de riesgo por el método Kinney
    (R = Probabilidad × Frecuencia × Impacto, antes y después de mitigación),
    permisos de trabajo requeridos y **firmas electrónicas** — basado en el
    formato real `REG.MAZ.SAFE.2.5.2` que ya usa el cliente.
  - Ambos módulos, además: vencimiento de la planilla PILA visible con
    badge (Vigente/Por vencer/Vencida) y banner de aviso agregado; correo
    automático (Brevo) al contacto de la empresa contratista al
    aprobar/rechazar una radicación o una declaración de método; no se
    puede aprobar una declaración sin al menos una firma vigente;
    exportación a Excel de las radicaciones (`openpyxl`) y a PDF de la
    declaración de método completa (`xhtml2pdf`).
  - **Firma electrónica de la Declaración de Método**: cada firma queda
    ligada a la cuenta autenticada que la ejecutó (`FirmaMetodo.firmante_usuario`,
    tomado de `request.user` — nunca del cliente) más un consentimiento
    explícito (`consiento_firma`) y una huella sha256 del contenido de la
    declaración en ese momento (`calcular_hash_declaracion`). Si la
    declaración se edita después de firmada, la firma queda marcada
    `documento_modificado_despues_de_firmar` y bloquea la aprobación hasta
    que se vuelva a firmar sobre la versión actual.
- **Política de privacidad / Habeas Data** (borrador): el registro de un
  trabajador exige marcar la autorización de tratamiento de sus datos
  personales (Ley 1581 de 2012), con fecha registrada
  (`Trabajador.autorizacion_datos`/`autorizacion_datos_en`). El texto de la
  política es público, sin necesidad de sesión, en `/politica-privacidad`
  (enlazado desde el formulario de trabajador y desde el login) — es un
  borrador técnico: le faltan los datos propios de la empresa (NIT, razón
  social, contacto) y revisión legal antes de considerarse definitivo.

Ver `CLAUDE_CAMARAS.md` para el contexto completo del proyecto.

## Estructura

- `core/` — modelo `Empresa` (tenant), autenticación del dashboard (login
  por token, perfil, gestión de usuarios con rol) — ver endpoints abajo.
- `camaras_ia/` — modelos `Camara`, `EquipoLocal`, `ZonaRestringida`,
  `ReglaAlerta`, `EventoDetectado`; lógica de negocio en `services.py`
  (`punto_en_poligono`, `evaluar_zona_horario`, `disparar_alerta`); y los
  endpoints de API descritos abajo.
- `contratistas/` — modelos `EmpresaContratista`, `Trabajador`,
  `RadicacionSeguridadSocial`, `DeclaracionMetodo`, `ActividadMetodo`
  (con el cálculo de riesgo Kinney), `FirmaMetodo`; endpoints descritos abajo.
- `frontend/` — dashboard Next.js (App Router + TypeScript + Tailwind),
  instalable como PWA. Ver su propia sección más abajo.
- `equipo_local/` — programa Python independiente (no es una app Django) que
  corre en el PC del DVR/NVR en sitio: se conecta por RTSP a cada cámara,
  detecta personas con YOLOv8n y reporta eventos al backend de arriba. Corre
  como servicio en segundo plano. También graba a disco (con retención
  automática) y expone un visor web local (cámaras en vivo + grabaciones,
  `http://<ip-del-pc>:8090`, solo accesible en la red de la planta). Ver
  `equipo_local/README.md`.

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

**Tests**: siempre con las apps explícitas —
`python manage.py test camaras_ia contratistas core` — nunca
`python manage.py test` a secas. Sin argumentos, Django descubre tests en
todo el árbol del proyecto (no solo en `INSTALLED_APPS`), lo que incluye
`equipo_local/tests/`, un programa Python aparte con sus propias
dependencias (`requests`, `opencv`, etc.) que no están en el venv de Django
— y el intento de importarlas revienta la corrida. `equipo_local/` tiene su
propia suite, independiente (ver `equipo_local/README.md`).

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

### Endpoints del dashboard en `camaras_ia` (autenticados por token de usuario)

Todos requieren `Authorization: Token <token>` (el que devuelve el login).
Zonas y reglas son de solo lectura para Operador — escribir (crear, editar,
eliminar) requiere rol Administrador.

| Endpoint | Qué hace |
|---|---|
| `GET /api/camaras-ia/dashboard/indicadores/` | KPIs del Tablero: cámaras activas/total, alertas hoy, disponibilidad (cámaras activas ÷ total — no es monitoreo de conectividad real) |
| `GET /api/camaras-ia/dashboard/eventos-por-zona/` | Conteo de eventos de los últimos 7 días agrupados por zona, para el gráfico del Tablero |
| `GET /api/camaras-ia/dashboard/eventos/` | Bandeja de Alertas; filtros `?estado=&disparo_alerta=&camara=` |
| `PATCH /api/camaras-ia/dashboard/eventos/<id>/` | Marcar un evento como revisado (o de vuelta a nuevo) |
| `GET /api/camaras-ia/dashboard/camaras/` | Cámaras con sus zonas y el último evento — usado por Cámaras IA y por el editor de Zonas |
| `POST /api/camaras-ia/dashboard/camaras/<id>/snapshot-referencia/` | Sube/reemplaza el encuadre fijo sobre el que se dibujan las zonas (multipart, campo `snapshot_referencia`) |
| `GET/POST /api/camaras-ia/dashboard/zonas/`, `GET/PATCH/DELETE /api/camaras-ia/dashboard/zonas/<id>/` | CRUD de `ZonaRestringida` — el polígono se dibuja haciendo clic sobre el snapshot de referencia, en las mismas coordenadas de píxel de esa imagen |
| `GET/POST /api/camaras-ia/dashboard/reglas/`, `GET/PATCH/DELETE /api/camaras-ia/dashboard/reglas/<id>/` | CRUD de `ReglaAlerta` (horario/días/canal/destinatario) de una zona |

### Endpoints de `contratistas` (autenticados por token de usuario)

| Endpoint | Qué hace |
|---|---|
| `GET /api/contratistas/catalogos/` | Listas fijas para los formularios: cursos Safety Academy, permisos de trabajo, roles de firma |
| `GET/POST /api/contratistas/empresas/`, `GET/PATCH/DELETE /api/contratistas/empresas/<id>/` | CRUD de `EmpresaContratista` |
| `GET/POST /api/contratistas/trabajadores/`, `GET/PATCH/DELETE /api/contratistas/trabajadores/<id>/` | CRUD de `Trabajador`; filtro `?contratista=` |
| `GET/POST /api/contratistas/radicaciones/`, `GET/PATCH/DELETE /api/contratistas/radicaciones/<id>/` | CRUD de `RadicacionSeguridadSocial` (multipart para el soporte de pago); filtros `?trabajador=&contratista=&estado=` |
| `POST /api/contratistas/radicaciones/<id>/aprobar/`, `POST .../rechazar/` | Decisión del interventor sobre una radicación (`observaciones` opcional) |
| `GET/POST /api/contratistas/declaraciones/`, `GET/PATCH/DELETE /api/contratistas/declaraciones/<id>/` | `DeclaracionMetodo` con sus `actividades` anidadas (se reemplazan todas en cada guardado) |
| `POST /api/contratistas/declaraciones/<id>/firmar/` | Agrega/reemplaza la firma de un rol (`rol`, `nombre_firmante`) |

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

- **Secciones del sidebar**: Tablero, Cámaras, Zonas y horarios, Alertas,
  Contratistas, Declaración de Método — para todos los roles — y Usuarios,
  solo para Administrador. Ninguna tiene URL propia; son secciones dentro de
  `/dashboard` manejadas por estado.
- **Roles**: el primer usuario (`createsuperuser`) es Administrador y ve la
  sección "Usuarios" en el sidebar; desde ahí crea al resto del equipo con
  su rol (Administrador u Operador) — no hay pantalla de registro público.
  Operador puede ver todo pero no editar zonas/reglas ni gestionar usuarios.
- **Editor de zonas**: en "Zonas y horarios", selecciona una cámara, sube su
  snapshot de referencia si no tiene, y haz clic sobre la imagen para ir
  agregando los vértices del polígono (mínimo 3). Las coordenadas se
  guardan en el sistema de píxeles naturales de esa imagen — el mismo que
  debe usar el equipo local al reportar `punto_x`/`punto_y` de un evento.
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
   | `BREVO_API_KEY` | API key de [Brevo](https://app.brevo.com) (Settings → SMTP & API → API Keys) — opcional: también se puede digitar desde el dashboard (Sistema → Brevo), que tiene prioridad sobre esta variable; sin ninguna de las dos, las alertas por correo quedan registradas como error pero no rompen nada |
   | `BREVO_REMITENTE_EMAIL` | correo remitente verificado en Brevo (Settings → Senders) — también configurable desde el dashboard |
   | `BREVO_REMITENTE_NOMBRE` | nombre que aparece como remitente, ej. `SST Bavaria — Cámaras IA` — también configurable desde el dashboard |

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

Canal **correo**: envío real vía la API HTTP de Brevo (`camaras_ia/notificaciones.py`,
sin SDK ni dependencias nuevas — una sola llamada REST con `urllib`). La API
key y el remitente se leen primero de `ConfiguracionNotificaciones` (fila
única editable desde el dashboard en Sistema → Brevo) y si está vacía, caen
de vuelta a `settings.BREVO_*` (variables de entorno). El resultado (éxito
o el motivo del error) queda en
`EventoDetectado.notificacion_enviada`/`notificacion_detalle`, visible en
Notificaciones → Envíos del dashboard. Si falta la API key en ambos lados o
Brevo responde con error, se registra el error y sigue sin romper
`recibir_evento_camara`.

Canal **whatsapp**: sigue siendo un stub — solo registra el intento en el
log (`camaras_ia.alertas`). Conectar un proveedor real de WhatsApp (o el
sistema de notificaciones del proyecto principal, vía API) es una decisión
de proveedor aparte, todavía no tomada.

## Seguridad (OWASP Top 10)

Controles aplicados, con su categoría OWASP correspondiente:

- **A05 Configuración de seguridad**: `SECRET_KEY` ya no tiene un valor por
  defecto conocido en producción — si `DEBUG=False` y falta la variable de
  entorno, el arranque falla explícitamente en vez de correr con un secreto
  público. Cabeceras HTTP de refuerzo activas siempre
  (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`) y
  HSTS en producción; el frontend agrega las mismas cabeceras equivalentes
  vía `next.config.ts` (Vercel ya agrega HSTS por su cuenta).
- **A01 Control de acceso roto**: `DEFAULT_PERMISSION_CLASSES` es
  `IsAuthenticated` (no `AllowAny`) — cualquier vista nueva queda protegida
  por defecto. Los dos endpoints del equipo local (que se autentican con su
  propia API key, no con el login de usuario) declaran `AllowAny`
  explícitamente. Eliminar contratistas, trabajadores, radicaciones y
  declaraciones de método requiere rol Administrador
  (`EsAdministradorParaEliminar`) — crear/editar sigue abierto a cualquier
  usuario autenticado, para no frenar el trabajo operativo diario.
- **A07 Fallas de identificación y autenticación**: el login tiene límite de
  intentos por IP (`core.throttling.LoginRateThrottle`, 10/min) para
  dificultar fuerza bruta de contraseñas — solo en ese endpoint, no en el
  resto de la API, para no interferir con el polling normal del equipo
  local.
- **A04/A05 Archivos subidos**: el soporte de pago de seguridad social
  (`RadicacionSeguridadSocial.soporte_pago`) valida extensión permitida
  (pdf/jpg/jpeg/png) y tamaño máximo (10 MB, `core.validators`). Los
  snapshots de cámara ya se validaban como imagen real (Pillow, vía
  `ImageField`); ahora también tienen tope de tamaño.
- **A03/A06**: sin SQL crudo en todo el proyecto (solo ORM), sin
  `eval`/`exec`/deserialización insegura. `pip-audit` y `npm audit` no
  reportan vulnerabilidades conocidas en las dependencias actuales.

Pendiente, fuera de alcance de este pase (se puede retomar cuando haga
falta): tokens de sesión con expiración (DRF `TokenAuthentication` no expira
por defecto), Content-Security-Policy en el frontend, y cifrado en reposo de
`password_onvif` (hoy se guarda en texto plano porque el equipo local
necesita leerlo para conectarse a la cámara).
