"use client";

import { useState, type ReactNode } from "react";

import type { Rol } from "@/lib/api";

function P({ children }: { children: ReactNode }) {
  return <p className="text-sm leading-relaxed text-corp-navy">{children}</p>;
}

function Sub({ children }: { children: ReactNode }) {
  return <h3 className="mt-5 text-sm font-semibold uppercase tracking-wide text-corp-muted">{children}</h3>;
}

function Ul({ children }: { children: ReactNode }) {
  return <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-corp-navy">{children}</ul>;
}

function Ol({ children }: { children: ReactNode }) {
  return <ol className="list-decimal space-y-1.5 pl-5 text-sm leading-relaxed text-corp-navy">{children}</ol>;
}

function Mono({ children }: { children: ReactNode }) {
  return <code className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs text-corp-navy">{children}</code>;
}

function Nota({ children, tipo = "info" }: { children: ReactNode; tipo?: "info" | "aviso" }) {
  return (
    <div
      className={`rounded-lg border px-4 py-3 text-sm leading-relaxed ${
        tipo === "aviso"
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-corp-blue/30 bg-corp-blue-light text-corp-navy"
      }`}
    >
      {children}
    </div>
  );
}

type Tema = {
  id: string;
  titulo: string;
  soloAdmin?: boolean;
  contenido: ReactNode;
};

const TEMAS: Tema[] = [
  {
    id: "primeros-pasos",
    titulo: "Primeros pasos",
    contenido: (
      <>
        <P>
          SST Bavaria — Cámaras IA tiene dos roles de usuario: <strong>Administrador</strong> (ve y edita todo,
          incluida la sección Sistema y Usuarios) y <strong>Operador</strong> (ve el día a día — cámaras,
          alertas, contratistas — pero no puede crear/editar zonas, reglas, ni gestionar usuarios o el equipo
          local).
        </P>
        <Sub>El menú de la izquierda</Sub>
        <P>Cada ítem del menú es una sección independiente — no hay direcciones web sueltas que recordar:</P>
        <Ul>
          <li><strong>Tablero</strong>: resumen general (KPIs y gráfico).</li>
          <li><strong>Cámaras</strong>: alta y estado de cada cámara.</li>
          <li><strong>Zonas y horarios</strong>: dibujar zonas restringidas y configurar cuándo alertan.</li>
          <li><strong>Alertas</strong>: bandeja de eventos detectados, para revisar.</li>
          <li><strong>Notificaciones</strong>: historial de correos enviados + configuración de reglas.</li>
          <li><strong>Contratistas</strong>: empresas, trabajadores y radicación de seguridad social.</li>
          <li><strong>Declaración de Método</strong>: formulario de riesgo (método Kinney) por trabajo.</li>
          <li><strong>Sistema</strong> (solo Administrador): credenciales de Brevo y equipos locales.</li>
          <li><strong>Usuarios</strong> (solo Administrador): quién tiene acceso y con qué rol.</li>
          <li><strong>Ayuda</strong>: esta sección.</li>
        </Ul>
        <Nota>
          El botón de colapsar menú (abajo del todo) deja solo los íconos — útil en pantallas chicas. En
          celular, el menú se abre con el ícono de las tres rayas arriba a la izquierda.
        </Nota>
      </>
    ),
  },
  {
    id: "tablero",
    titulo: "Tablero",
    contenido: (
      <>
        <P>La primera pantalla al entrar — un resumen rápido de cómo está todo hoy.</P>
        <Ul>
          <li><strong>Cámaras activas / total</strong>: cuántas están habilitadas de las registradas.</li>
          <li><strong>Alertas hoy</strong>: cuántos eventos dispararon alerta en las últimas 24h.</li>
          <li><strong>Disponibilidad</strong>: proporción de cámaras activas — no mide si están conectadas de
            verdad en este momento, solo si están marcadas como habilitadas.</li>
          <li><strong>Gráfico de eventos por zona</strong>: qué zonas han tenido más movimiento en los
            últimos 7 días — útil para ver dónde se concentra la actividad.</li>
        </Ul>
      </>
    ),
  },
  {
    id: "camaras",
    titulo: "Cámaras",
    contenido: (
      <>
        <P>Acá se registra cada cámara física para que el equipo local sepa a cuáles conectarse.</P>
        <Sub>Agregar una cámara</Sub>
        <Ol>
          <li>Botón <strong>+ Nueva cámara</strong> (solo Administrador).</li>
          <li>Nombre descriptivo (ej. &quot;Cámara Bodega Principal&quot;), IP y ubicación.</li>
          <li>Usuario y contraseña ONVIF — las mismas credenciales de fábrica de la cámara (se reutilizan
            también como credenciales de video).</li>
          <li>Si la cámara no sigue el patrón estándar (no es Dahua, o el técnico dio otra URL), se puede
            escribir la <strong>URL RTSP</strong> completa a mano; si se deja vacío, el sistema arma la URL
            sola con la IP y las credenciales de arriba.</li>
        </Ol>
        <Sub>Encuadre de referencia</Sub>
        <P>
          Cada cámara necesita una foto fija (&quot;snapshot de referencia&quot;) sobre la cual se dibujan las
          zonas restringidas — se sube desde <strong>Zonas y horarios</strong>, no desde acá. Sin esa foto, no
          se pueden dibujar zonas para esa cámara.
        </P>
        <Nota>
          Activar/desactivar una cámara (en vez de eliminarla) es la forma de pausarla temporalmente sin
          perder sus zonas y reglas configuradas.
        </Nota>
      </>
    ),
  },
  {
    id: "zonas",
    titulo: "Zonas y horarios",
    contenido: (
      <>
        <P>
          Acá se dibuja, sobre la foto de cada cámara, el área exacta donde no debería haber nadie (zona
          restringida), y se configura cuándo eso dispara una alerta.
        </P>
        <Sub>Dibujar una zona</Sub>
        <Ol>
          <li>Elegir la cámara. Si todavía no tiene foto de referencia, subirla primero (botón en esta
            misma vista).</li>
          <li>Clic sobre la imagen para ir marcando los vértices del polígono — con 3 o más puntos ya se
            puede cerrar la zona.</li>
          <li>Ponerle un nombre a la zona (ej. &quot;Zona de carga&quot;).</li>
        </Ol>
        <Sub>Reglas de horario</Sub>
        <P>Cada zona puede tener una o varias reglas — cada regla define:</P>
        <Ul>
          <li><strong>Horario y días</strong>: cuándo esa zona debe estar vacía (ej. de noche, o fines de
            semana).</li>
          <li><strong>Canal</strong>: correo o WhatsApp (WhatsApp todavía no tiene proveedor conectado — el
            canal activo hoy es correo, vía Brevo).</li>
          <li><strong>Destinatario</strong>: a quién avisar.</li>
        </Ul>
        <P>
          Si alguien aparece en la zona <strong>fuera</strong> de esos horarios, no pasa nada (no hay regla
          vigente). Si aparece <strong>dentro</strong> del horario configurado, se genera una alerta y se
          envía la notificación por el canal elegido.
        </P>
      </>
    ),
  },
  {
    id: "alertas",
    titulo: "Alertas",
    contenido: (
      <>
        <P>
          Bandeja con todos los eventos que las cámaras reportaron — tengan o no alerta asociada — cada uno
          con su foto. Es la vista de <strong>triage</strong>: revisar qué pasó, no el estado del envío de
          notificación (eso está en Notificaciones).
        </P>
        <Ul>
          <li><strong>Alerta / Normal</strong>: si el evento cayó dentro de una zona con regla vigente en ese
            momento.</li>
          <li><strong>Nuevo / Revisado</strong>: marca manual para llevar control de qué ya se atendió —
            botón &quot;Marcar revisado&quot;.</li>
          <li>Filtros por estado y por si disparó alerta o no, arriba a la derecha.</li>
          <li>Clic en la foto para verla en grande.</li>
        </Ul>
      </>
    ),
  },
  {
    id: "notificaciones",
    titulo: "Notificaciones",
    contenido: (
      <>
        <P>Dos pestañas:</P>
        <Sub>Envíos</Sub>
        <P>
          Historial de cada notificación enviada por una alerta: cámara, zona, fecha, canal, y su estado —{" "}
          <strong>Enviada</strong> (verde), <strong>Error</strong> (rojo, con el motivo al pasar el mouse) o{" "}
          <strong>N/D</strong> (canal WhatsApp, todavía sin proveedor conectado). Filtrable por canal.
        </P>
        <Sub>Configuración</Sub>
        <P>
          La misma tabla de reglas (horario/canal/destinatario por zona) que se ve desde Zonas y horarios —
          está duplicada acá para no tener que ir y volver entre secciones al ajustar a quién avisar.
        </P>
      </>
    ),
  },
  {
    id: "contratistas",
    titulo: "Contratistas",
    contenido: (
      <>
        <P>Gestión de contratistas y su seguridad social al día — tres niveles:</P>
        <Ol>
          <li><strong>Empresa contratista</strong>: nombre, NIT, contactos, responsable SST.</li>
          <li><strong>Trabajadores</strong> de esa empresa: documento, EPS/ARL/AFP, tipo de vinculación,
            cursos de Safety Academy.</li>
          <li><strong>Radicación de seguridad social</strong>: por cada trabajador y mes, se sube el
            comprobante de pago (PDF o foto) con número de planilla y fecha de vencimiento.</li>
        </Ol>
        <Sub>Aprobar o rechazar una radicación</Sub>
        <P>
          Desde el panel de radicaciones de un trabajador, botones <strong>Aprobar</strong>/
          <strong>Rechazar</strong> — piden observaciones (obligatorias al rechazar, opcionales al aprobar) en
          un cuadro propio de la app, no una ventana del navegador.
        </P>
      </>
    ),
  },
  {
    id: "declaracion-metodo",
    titulo: "Declaración de Método",
    contenido: (
      <>
        <P>
          Formulario de análisis de riesgo por trabajo (método Kinney: Probabilidad × Frecuencia × Impacto)
          que un contratista diligencia antes de una labor puntual.
        </P>
        <Ul>
          <li>Datos generales: contratista, área/planta, número de pedido, fechas, descripción del trabajo.</li>
          <li>Una fila por actividad, con el riesgo <strong>sin</strong> medidas de mitigación y{" "}
            <strong>con</strong> ellas aplicadas — el nivel de riesgo (bajo/medio/alto/crítico) se calcula
            solo según el puntaje.</li>
          <li>Permisos de trabajo requeridos por actividad (altura, caliente, espacio confinado, etc.).</li>
          <li>Firmas por rol (supervisor del contratista, delegado ABI, seguridad de planta, etc.) y estado
            general del documento (borrador / enviada / aprobada / rechazada).</li>
        </Ul>
      </>
    ),
  },
  {
    id: "sistema",
    titulo: "Sistema",
    soloAdmin: true,
    contenido: (
      <>
        <P>Solo Administrador. Dos pestañas:</P>
        <Sub>Brevo (correo)</Sub>
        <P>
          Acá se digita la API key de Brevo (el proveedor que envía los correos de alerta) y el remitente —
          sin necesidad de tocar nada en Railway. La API key nunca se vuelve a mostrar una vez guardada (por
          seguridad); el badge indica si hay una configurada o no.
        </P>
        <Sub>Equipo local</Sub>
        <P>
          Acá se registra cada PC/DVR físico que corre el programa <Mono>equipo_local</Mono> en sitio. Botón{" "}
          <strong>&quot;Descargar .env&quot;</strong>: descarga un archivo ya listo con la conexión al backend
          y la clave de ese equipo — solo hay que arrastrarlo a la carpeta del programa en ese PC, sin editar
          nada a mano. El badge <strong>Conectado</strong> se pone verde cuando ese equipo sincronizó hace
          menos de 5 minutos. Ver el tema <strong>&quot;El equipo local&quot;</strong> más abajo para el flujo
          completo de cómo se conecta a las cámaras y cómo ver el video en vivo.
        </P>
      </>
    ),
  },
  {
    id: "usuarios",
    titulo: "Usuarios",
    soloAdmin: true,
    contenido: (
      <>
        <P>Solo Administrador. Quién tiene acceso al panel y con qué rol.</P>
        <Ul>
          <li><strong>+ Nuevo usuario</strong>: usuario, correo, contraseña y rol inicial.</li>
          <li>Cambiar el rol de un usuario existente con el desplegable de la tabla.</li>
          <li><strong>Desactivar</strong> en vez de eliminar, para revocar el acceso sin perder su historial
            de acciones.</li>
        </Ul>
        <Nota>No puedes desactivarte ni eliminarte a ti mismo — esos botones aparecen deshabilitados en tu
          propia fila.</Nota>
      </>
    ),
  },
  {
    id: "equipo-local",
    titulo: "El equipo local (el programa del PC en planta)",
    contenido: (
      <>
        <P>
          Además del dashboard (lo que ves en el navegador), hay un segundo programa —{" "}
          <Mono>equipo_local</Mono> — que corre en un PC físico dentro de la planta, junto a las cámaras. Este
          tema explica cómo encajan las dos piezas.
        </P>
        <Sub>Los 3 actores</Sub>
        <Ol>
          <li><strong>Las cámaras</strong>: en la red de la planta, cada una con su IP.</li>
          <li><strong>El equipo local</strong>: un PC en esa misma red, corriendo el programa que vigila
            las cámaras — es el &quot;DVR/NVR&quot; del sistema.</li>
          <li><strong>La nube</strong>: este dashboard + el backend en Railway, alcanzable desde cualquier
            lado por internet.</li>
        </Ol>
        <Sub>Cómo se conectan las cámaras al equipo local</Sub>
        <P>No es cableado — es configuración, así:</P>
        <Ol>
          <li>Registras la cámara acá en el dashboard (sección Cámaras): IP y credenciales.</li>
          <li>El equipo local, al arrancar y cada 60 segundos, le pregunta al backend en la nube qué
            cámaras vigilar y con qué configuración (esto es la &quot;sincronización&quot;).</li>
          <li>El backend le contesta con la URL de video (RTSP) de cada cámara.</li>
          <li>El equipo local se conecta <strong>directo a la cámara</strong>, dentro de la misma red de la
            planta — ahí procesa el video con IA para detectar personas.</li>
          <li>Si detecta a alguien en una zona restringida con regla vigente, le avisa al backend en la
            nube — mandando solo una foto del momento, nunca el video.</li>
        </Ol>
        <Nota>
          Tú configuras la cámara acá en el dashboard (nube), pero la conexión de video real es directa entre
          la cámara y el PC del equipo local (red local). El backend nunca ve el video en sí.
        </Nota>
        <Sub>Ver las cámaras en vivo y las grabaciones</Sub>
        <P>
          El equipo local también graba lo que ve cada cámara (con borrado automático de lo viejo) y levanta
          su propia página web para verlo — completamente aparte del dashboard, para que el video nunca tenga
          que subir a internet. Se accede desde un navegador <strong>en la misma red de la planta</strong>:
        </P>
        <p className="rounded-md bg-zinc-100 px-3 py-2 font-mono text-xs text-corp-navy">
          http://sstbavaria-camaras.local:8090
        </p>
        <Ul>
          <li>Funciona directo en Mac y en la mayoría de Linux de escritorio.</li>
          <li>En Windows no resuelve ese nombre de fábrica — o se instala una vez &quot;Bonjour Print
            Services&quot; (gratis, de Apple), o se usa el nombre del PC en la red en su lugar (ej.{" "}
            <Mono>http://NOMBRE-DEL-PC:8090</Mono>).</li>
          <li>Si nada de eso funciona, la IP directa del PC siempre sirve como respaldo.</li>
        </Ul>
        <Sub>Cómo saber que todo está funcionando</Sub>
        <Ul>
          <li><strong>Cámara conectada</strong>: en Cámaras, el último snapshot se actualiza solo.</li>
          <li><strong>Equipo local conectado</strong>: en Sistema → Equipo local, el badge está en verde
            (&quot;Conectado&quot;).</li>
          <li><strong>Eventos llegando</strong>: aparecen registros nuevos en Alertas/Notificaciones cuando
            corresponde.</li>
          <li><strong>Visor en vivo accesible</strong>: la URL de arriba abre y se ve el video moviéndose.</li>
        </Ul>
        <P>
          Si el badge nunca se pone verde, el problema está en el equipo local (no está corriendo, o su clave
          no es correcta, o no tiene salida a internet). Si el badge está verde pero el visor no abre por
          nombre, el problema es solo de resolución de nombre en esa red — la IP directa debe seguir
          funcionando.
        </P>
      </>
    ),
  },
  {
    id: "preguntas-frecuentes",
    titulo: "Preguntas frecuentes",
    contenido: (
      <>
        <Sub>No me llegan los correos de alerta</Sub>
        <P>
          Revisa Sistema → Brevo: que el badge diga &quot;API key configurada&quot;. Si lo está, revisa
          Notificaciones → Envíos — la columna Detalle explica el motivo exacto de cada error (credenciales
          inválidas, remitente no verificado en Brevo, etc.).
        </P>
        <Sub>No veo cámaras en vivo</Sub>
        <P>
          Primero confirma que el equipo local esté &quot;Conectado&quot; en Sistema → Equipo local — si no
          lo está, el problema es de ese PC, no del visor. Si está conectado pero{" "}
          <Mono>sstbavaria-camaras.local</Mono> no abre, prueba con la IP directa del PC (ver el tema
          &quot;El equipo local&quot;).
        </P>
        <Sub>Elimina cosas por accidente</Sub>
        <P>
          Toda acción destructiva (eliminar usuario, zona, regla, equipo local) pide confirmación en un cuadro
          propio de la app antes de ejecutarse — nunca se borra nada con un solo clic.
        </P>
        <Sub>¿Dónde está el panel técnico (admin de Django)?</Sub>
        <P>
          Botón &quot;Admin de Django&quot; abajo del menú (solo Administrador) — abre en una pestaña nueva.
          Es una vista más técnica, pensada para soporte/mantenimiento, no para el uso diario.
        </P>
      </>
    ),
  },
];

export default function AyudaView({ rol }: { rol: Rol | null }) {
  const temasVisibles = TEMAS.filter((tema) => !tema.soloAdmin || rol === "administrador");
  const [temaId, setTemaId] = useState(temasVisibles[0]?.id);
  const tema = temasVisibles.find((t) => t.id === temaId) ?? temasVisibles[0];

  return (
    <div>
      <p className="text-sm text-corp-muted">
        Manual de uso del panel y del equipo local — se actualiza cada vez que se agrega o cambia algo en el
        sistema.
      </p>

      <div className="mt-6 flex flex-col gap-6 lg:flex-row">
        <nav className="shrink-0 lg:w-64">
          <ul className="space-y-1">
            {temasVisibles.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => setTemaId(t.id)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                    t.id === tema?.id
                      ? "bg-corp-blue text-white"
                      : "text-corp-navy hover:bg-corp-blue-light"
                  }`}
                >
                  {t.titulo}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {tema && (
          <div className="min-w-0 flex-1 rounded-xl border border-corp-border bg-white p-6">
            <h2 className="text-lg font-semibold text-corp-navy">{tema.titulo}</h2>
            <div className="mt-4 space-y-3">{tema.contenido}</div>
          </div>
        )}
      </div>
    </div>
  );
}
