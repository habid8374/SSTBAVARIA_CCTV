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

## Cámara de referencia

Confirmada en sitio: **Dahua Picoo A2** — serie Wi-Fi de consumo/prosumer,
modelos `DH-P3AE-PV` (3MP) / `DH-P5AE-PV` (5MP), SKU internacional
`SD2A500HB-GN-AW-PV-S2`. Investigado por Claude (fuentes en el foro
IPCamTalk y el sitio de Dahua International, agosto 2026 — no es info
oficial verificada en sitio, confirmar con hardware real):

- Wi-Fi + Ethernet, movimiento motorizado pan/tilt (lente fijo de 4mm, **no
  es zoom óptico real** pese al nombre "PTZ" usado coloquialmente).
- Detección de humano/vehículo con IA propia de la cámara ("Smart Dual
  Light") — coincide con el plan ya documentado de "analítica propia de la
  cámara o modelo local, según hardware final".
- **RTSP sí soportado**: puerto 554, formato estándar Dahua
  `rtsp://usuario:password@IP:554/cam/realmonitor?channel=1&subtype=0`
  (`subtype=0` = stream principal, `subtype=1` = substream liviano).
- **ONVIF probablemente NO implementado en la serie Picoo** — consenso de
  comunidad (no confirmado por Dahua oficialmente); los modelos gemelos de
  la submarca Imou sí lo traen. Se configura principalmente por la app
  móvil DMSS (QR + nube P2P), no por un panel web tipo ONVIF/NVR
  empresarial.
- **Impacto en Fase 2 (equipo local, fuera de este repo)**: si de verdad no
  hay ONVIF, el equipo local no puede usar descubrimiento/eventos ONVIF
  como se asumía originalmente (heredado de la referencia Hikvision
  evaluada antes de confirmar el modelo real) — tendría que tomar el
  stream RTSP directo y correr la detección con un modelo propio en el
  mini-PC del sitio, en vez de recibir eventos nativos de la cámara.
  **Confirmar con el hardware físico** (ONVIF Device Manager u
  `onvif-cli` contra la IP real) antes de comprometerse a un enfoque.

Se mantiene el mismo supuesto de diseño de siempre: la detección de
movimiento la hace la cámara/equipo local, pero **la lógica de "¿cayó
dentro del polígono restringido?" la resuelve el backend**, cruzando el
punto detectado contra `ZonaRestringida` — la cámara no define zonas
internamente. Esto hace que el backend (Fase 2, ver abajo) sea agnóstico a
la marca/modelo exacto de cámara y al protocolo que use el equipo local
para capturar el punto: solo necesita un punto (x, y) en el mismo sistema
de coordenadas del encuadre de referencia usado para dibujar el polígono.

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

Dashboard propio (Next.js, en `frontend/` dentro de este mismo repo — no un
repo aparte), con el mismo criterio de navegación por sidebar de botones
(sin rutas separadas) definido en el proyecto principal. Si más adelante se
decide unificar ambos dashboards en una sola interfaz para el cliente, es un
paso de integración posterior — no bloquea arrancar cada uno por su lado.

**Ya construido**: login corporativo (autenticación real contra usuarios de
Django, sin registro público — el Administrador crea al resto del equipo) y
gestión de usuarios con rol (Administrador/Operador). Sidebar responsive
(colapsa en desktop, drawer en móvil/tablet) y PWA instalable en celular.
Solo hay dos rutas reales (`/login`, `/dashboard`); todo lo demás son
secciones dentro del sidebar manejadas por estado, no por URL.

También la Fase 4 completa (ver más abajo):

- **Tablero**: KPIs (cámaras activas/total, alertas hoy, disponibilidad) +
  gráfico de barras de eventos por zona (últimos 7 días).
- **Cámaras IA**: tarjeta por cámara con el último snapshot, el polígono de
  su zona dibujado encima (SVG) y un banner verde/rojo según si el último
  evento disparó alerta — el mismo estilo de las fotos de referencia del
  cliente (persona detectada en verde, alerta en rojo, zona en amarillo).
- **Zonas y horarios**: editor visual — seleccionar cámara, subir su
  snapshot de referencia, dibujar el polígono haciendo clic sobre la imagen
  (coordenadas en píxeles naturales de esa foto) y configurar sus reglas de
  horario (días, franja, canal, destinatario) sin tocar el admin de Django.
- **Alertas**: bandeja de `EventoDetectado` con foto, filtros por
  estado/disparo de alerta, y marcar revisado.

Operador ve las cuatro secciones pero no puede crear/editar/eliminar zonas
ni reglas (`EsAdministradorOSoloLectura` en el backend) ni gestionar
usuarios — solo Administrador.

## Fases de entrega (del alcance cotizado al cliente)

1. **Análisis de zonas y reglas** — visita/levantamiento de qué cámara ve qué
   zona y en qué horario aplica cada alerta. Modelo de datos + panel de
   administración para registrar lo levantado en la visita. **Completa.**
2. **Integración con las cámaras (ONVIF/RTSP reales)** — dividida en dos
   partes que no se mezclan (ver "Qué hace este módulo" arriba):
   - **Backend en la nube — completa**: `evaluar_zona_horario` (cruce punto
     detectado + polígono + horario, con ray casting y manejo de horarios
     que cruzan medianoche), `disparar_alerta` (stub con logging, sin
     proveedor de WhatsApp/correo real todavía), `recibir_evento_camara`
     (recibe cámara + punto + snapshot, valida ownership por empresa, crea
     `EventoDetectado`) y `obtener_reglas_activas` (el equipo local
     sincroniza cámaras/zonas/reglas activas de su empresa por API key).
   - **Equipo local en sitio (ONVIF/RTSP/PTZ real contra la Dahua PTZ Pico
     A2)** — pendiente, es un desarrollo aparte (posiblemente otro repo),
     no parte de este backend Django.
3. Motor de detección y reglas funcionando end-to-end (requiere el equipo
   local de sitio integrado con el backend de arriba)
4. **Panel en el dashboard (zonas dibujadas, tablero de indicadores) —
   completo** del lado del dashboard (Tablero, Cámaras IA, Zonas y
   horarios, Alertas). Sigue pendiente que datos *reales* del equipo local
   lleguen a poblarlo — hoy se probó con datos de prueba.
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
