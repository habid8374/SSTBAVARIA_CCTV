# CLAUDE_CAMARAS.md — Módulo de Videovigilancia con IA

Contexto del proyecto de cámaras para Claude Code. Léeme antes de generar código.

**Repositorio**: https://github.com/habid8374/SSTBAVARIA_CCTV (vacío, arrancamos
desde cero).

Este es un **proyecto Django independiente**, con su propio repo y su propio
despliegue en Railway — no una carpeta dentro del proyecto de Radicación/
Declaración de Método. Se comunica con el sistema principal por API (por
ejemplo, para reutilizar el envío de alertas WhatsApp/correo si se decide
centralizarlo ahí), no compartiendo código directamente. Si más adelante
conviene fusionarlos en un solo backend, es una decisión a tomar con datos
reales de uso, no un default de arranque.

## Qué hace este módulo

Conecta 10 cámaras PTZ y detecta automáticamente cuándo hay una persona en una
zona restringida durante un horario configurado, generando una alerta. Dos partes
que no se mezclan:

- **En el sitio (equipo local, junto a las cámaras)**: conexión a cámaras,
  detección (propia de la cámara o modelo local), cruce zona+horario, control PTZ.
- **En la nube (este backend)**: configuración de zonas/horarios, recepción de
  eventos, historial, alertas, dashboard. **Nunca recibe video crudo, solo eventos
  con una foto.**

## Cámara de referencia (pendiente de confirmar en sitio)

Hikvision DS-2DE2C400MWG-E — 4MP, PoE, ONVIF/ISAPI/SDK confirmado por el
fabricante, analítico ACUSENSE Lite (detección de humano/vehículo **por
movimiento simple, no por zona ni intrusión**). Esto significa que la lógica de
"¿cayó dentro del polígono restringido?" la resolvemos nosotros en el backend,
cruzando el evento de movimiento de la cámara contra `ZonaRestringida` — la
cámara no define zonas internamente.

## Proyecto Django

Proyecto nuevo (no una app dentro de otro proyecto). Apps internas:
- `camaras_ia/` — modelos y lógica del módulo
- `core/` — lo mínimo propio: autenticación, tenant (`Empresa`), sin duplicar
  todo lo que ya existe en el proyecto principal

## Stack y despliegue (mismo patrón que el proyecto principal)

- Django + Django REST Framework, PostgreSQL
- Configuración 100% por variables de entorno (`os.environ` + `dj-database-url`),
  **sin `.env`**
- Despliegue en Railway (plan Trial para probar, Hobby para dejarlo corriendo
  después de los 30 días de crédito inicial)
- `requirements.txt`, `Procfile`/`railway.json`, `gunicorn`, `whitenoise`,
  `ALLOWED_HOSTS`/`DEBUG` por variable de entorno — igual que se dejó armado el
  proyecto principal

## Modelos clave

- `Camara`: nombre, IP, credenciales ONVIF, ubicación, empresa (tenant)
- `EquipoLocal`: identifica el mini-PC/equipo en sitio que reporta eventos —
  autenticado por API key propia, no por usuario/clave de persona
- `ZonaRestringida`: FK a Camara, polígono (lista de coordenadas), nombre
- `ReglaAlerta`: FK a ZonaRestringida, horario de inicio/fin, días de la semana,
  canal de notificación (WhatsApp/correo), destinatario
- `EventoDetectado`: FK a Camara y ZonaRestringida (si aplica), timestamp,
  snapshot (imagen), si disparó alerta o no, estado (nuevo/revisado)

## Funciones/servicios clave

| Función | Responsabilidad |
|---|---|
| `recibir_evento_camara(payload)` | Endpoint que recibe el evento del equipo local (foto + metadata), valida la API key |
| `evaluar_zona_horario(evento)` | Cruza el evento contra `ZonaRestringida` y `ReglaAlerta` vigentes para decidir si dispara alerta |
| `disparar_alerta(evento, regla)` | Envía la notificación (WhatsApp/correo) reutilizando el sistema de notificaciones del proyecto principal |
| `obtener_reglas_activas(equipo_id)` | Endpoint que el equipo local consulta periódicamente para sincronizar zonas/horarios sin tocar el equipo físicamente |
| `registrar_camara(datos)` | Alta de una cámara nueva y su(s) zona(s) desde el panel |

## Frontend / UX

Dashboard propio (Next.js), con el mismo criterio de navegación por sidebar de
botones (sin rutas separadas) definido en el proyecto principal. Si más adelante
se decide unificar ambos dashboards en una sola interfaz para el cliente, es un
paso de integración posterior — no bloquea arrancar cada uno por su lado:

- **Cámaras IA**: alta/edición de cámaras, dibujar zonas restringidas sobre un
  snapshot de referencia, configurar horarios por zona
- **Alertas**: bandeja de eventos disparados, con foto y estado
- **Tablero de indicadores**: cámaras activas, alertas por día, eventos por zona
  (ver el mockup ya aprobado por el cliente)

## Fases de entrega (del alcance cotizado al cliente)

1. **Análisis de zonas y reglas** — visita/levantamiento de qué cámara ve qué
   zona y en qué horario aplica cada alerta. Esta fase es la que arrancamos
   ahora: modelo de datos + panel de administración para registrar lo que se
   levante en la visita, todavía sin conexión real a cámaras.
2. Integración con las cámaras (ONVIF/RTSP reales)
3. Motor de detección y reglas funcionando end-to-end
4. Panel en el dashboard (zonas dibujadas, tablero de indicadores)
5. Pruebas en sitio y ajustes de producción

No adelantar trabajo de una fase sin cerrar la anterior — el cliente prueba y
aprueba cada una antes de seguir.

## Convenciones (heredadas del proyecto principal)

- Español para modelos/campos visibles al usuario.
- Configuración 100% por variables de entorno (`os.environ`), sin `.env` —
  mismo Railway del proyecto principal.
- `EquipoLocal` se autentica con API key propia, nunca con credenciales de un
  usuario humano — es un dispositivo, no una persona.
- El backend nunca recibe ni almacena video en streaming, solo eventos puntuales
  con una imagen — si en algún punto se propone guardar video, es una decisión
  de alcance/costo aparte, no un default de esta arquitectura.
