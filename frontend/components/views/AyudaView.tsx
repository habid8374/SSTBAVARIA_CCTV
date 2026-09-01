"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";

import { Mono, Nota, Ol, P, Sub, Ul } from "@/components/DocTexto";
import type { Rol } from "@/lib/api";

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
          SST Bavaria — Cámaras IA tiene tres roles de usuario: <strong>Administrador</strong> (ve y edita
          todo, incluida la sección Sistema y Usuarios), <strong>Operador</strong> (ve el día a día — cámaras,
          alertas, contratistas — pero no puede crear/editar zonas, reglas, ni gestionar usuarios o el equipo
          local) y <strong>Contratista</strong> (el portal de la empresa contratista — ver el tema
          &quot;Portal de contratistas&quot; para el detalle de qué puede hacer).
        </P>
        <Sub>El menú de la izquierda</Sub>
        <P>Cada ítem del menú es una sección independiente — no hay direcciones web sueltas que recordar. Un
          usuario con rol Contratista solo ve Contratistas (su propia empresa, de solo lectura), Declaración
          de Método, Autorización de Ingreso (de solo lectura) y Ayuda — el resto de ítems son para el
          personal interno de SST/interventoría:</P>
        <Ul>
          <li><strong>Tablero</strong>: resumen general (KPIs y gráfico).</li>
          <li><strong>Cámaras</strong>: alta y estado de cada cámara.</li>
          <li><strong>Zonas y horarios</strong>: dibujar zonas restringidas y configurar cuándo alertan.</li>
          <li><strong>Alertas</strong>: bandeja de eventos detectados, para revisar.</li>
          <li><strong>Notificaciones</strong>: historial de correos enviados + configuración de reglas.</li>
          <li><strong>Contratistas</strong>: empresas, trabajadores y radicación de seguridad social.</li>
          <li><strong>Declaración de Método</strong>: formulario de riesgo (método Kinney) por trabajo.</li>
          <li><strong>Autorización de Ingreso</strong>: quién queda autorizado a entrar a planta, cuándo y en
            qué área — con inclusiones y exclusiones de trabajadores.</li>
          <li><strong>Funcionarios firmantes</strong> (personal interno): padrón de quién puede firmar cada
            rol de la Declaración de Método.</li>
          <li><strong>Indicadores</strong> (personal interno): panel comparativo entre todas las empresas
            contratistas.</li>
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
    id: "portal-contratistas",
    titulo: "Portal de contratistas",
    contenido: (
      <>
        <P>
          Es el mismo dashboard y el mismo login — no hay una app ni una dirección web aparte — pero un
          usuario con rol <strong>Contratista</strong> ve un menú reducido y casi todo en modo de solo
          lectura, scopeado siempre a su propia empresa.
        </P>
        <Sub>Qué puede ver y hacer</Sub>
        <Ul>
          <li><strong>Declaración de Método</strong>: acceso completo — es la única sección donde puede
            escribir. Puede crear, editar, enviar a revisión y firmar como Supervisor de Seguridad del
            Contratista.</li>
          <li><strong>Contratistas</strong>: ve los datos de su propia empresa y sus trabajadores (EPS/ARL/AFP,
            radicaciones de seguridad social) — de solo lectura, no puede editar ni cargar radicaciones.</li>
          <li><strong>Autorización de Ingreso</strong>: ve sus autorizaciones de ingreso vigentes y puede
            descargar el PDF — de solo lectura.</li>
          <li><strong>Ayuda</strong>: este manual.</li>
        </Ul>
        <P>
          Todo lo demás (Tablero, Cámaras, Zonas, Alertas, Notificaciones, Funcionarios firmantes,
          Indicadores, Sistema, Usuarios) es exclusivo del personal interno de SST/interventoría y no aparece
          en su menú.
        </P>
        <Sub>Cómo se da de alta</Sub>
        <P>
          Un Administrador crea la cuenta desde Usuarios, eligiendo el rol Contratista y la empresa a la que
          representa (ver el tema &quot;Usuarios&quot;). Es <strong>una cuenta por empresa</strong>, que
          comparten todos sus contactos — no una cuenta por persona.
        </P>
        <Sub>El flujo de la Declaración de Método</Sub>
        <P>
          Ver el tema &quot;Declaración de Método&quot; para el detalle completo del ciclo enviar → revisar →
          aprobar/rechazar → subsanar, que es el corazón del portal.
        </P>
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
            cursos de Safety Academy — los cursos marcados con <span className="text-amber-700">*</span>{" "}
            son obligatorios (se configuran en Sistema → Reglas de contratistas); si a un trabajador activo
            le falta alguno, aparece un aviso ⚠ junto a su nombre en la lista.</li>
          <li><strong>Radicación de seguridad social</strong>: por cada trabajador y mes, se sube el
            comprobante de pago (PDF o foto) con número de planilla y fecha de vencimiento.</li>
        </Ol>
        <Sub>Aprobar o rechazar una radicación</Sub>
        <P>
          Desde el panel de radicaciones de un trabajador, botones <strong>Aprobar</strong>/
          <strong>Rechazar</strong> — piden observaciones (obligatorias al rechazar, opcionales al aprobar) en
          un cuadro propio de la app, no una ventana del navegador. Al aprobar o rechazar, se le avisa por
          correo automáticamente al contacto de la empresa contratista (si tiene correo registrado).
        </P>
        <Sub>Vencimiento de la seguridad social</Sub>
        <P>
          Cada radicación muestra un badge junto a su estado: <strong>Vigente</strong> (verde),{" "}
          <strong>Vence en N días</strong> (ámbar, a 15 días o menos de vencer) o <strong>Vencida</strong>{" "}
          (roja). Si hay alguna vencida o por vencer, aparece un aviso arriba de toda la vista de Contratistas
          con el conteo — para no tener que revisar radicación por radicación.
        </P>
        <Sub>Exportar a Excel</Sub>
        <P>
          Botón <strong>&quot;Exportar radicaciones (Excel)&quot;</strong> arriba de la vista: descarga todas
          las radicaciones con contratista, trabajador, planilla, vencimiento y estado — útil para reportes o
          auditoría fuera de la app.
        </P>
        <Sub>Vencimiento de examen médico y certificación de alturas</Sub>
        <P>
          En el formulario de cada trabajador hay dos campos opcionales — <strong>vencimiento del examen
          médico ocupacional</strong> y <strong>vencimiento de la certificación de trabajo en alturas</strong>{" "}
          — pensados solo para trabajadores que hacen trabajo en altura (el SOP del cliente exige examen
          vigente hace menos de 1 año y recertificación de alturas cada 2 años). Igual que con la seguridad
          social, si alguno queda vencido o vence en 15 días o menos aparece un aviso ⚠ junto al nombre del
          trabajador en la lista, y un conteo en el banner de arriba de toda la vista de Contratistas.
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
          <li>Equipo de protección personal (EPP) requerido por actividad (casco, gafas, arnés, etc.) — se
            marca igual que los permisos de trabajo, con casillas por actividad.</li>
          <li>Altura de trabajo y profundidad de excavación por actividad (metros) — campos opcionales, sin
            obligación de diligenciarlos, que habilitan alertas automáticas más precisas cuando se llenan
            (ver el tema &quot;Alertas automáticas&quot; más abajo).</li>
          <li>Firmas electrónicas por rol (supervisor del contratista, delegado ABI, seguridad de planta,
            etc.) y estado general del documento (borrador / enviada / aprobada / rechazada).</li>
        </Ul>
        <Sub>Importar desde Excel — para no retipear una declaración que ya existe</Sub>
        <P>
          Al crear una declaración nueva (antes de guardarla por primera vez) aparece un botón{" "}
          <strong>&quot;Importar desde Excel&quot;</strong> para subir el libro de Excel que ya usa el cliente
          para diligenciar declaraciones de método a mano. El sistema lee el archivo y precarga
          automáticamente los datos generales, la secuencia de actividades y sus riesgos, los permisos de
          trabajo y el EPP marcados. Después de importar, <strong>toda la información queda editable</strong>{" "}
          — se revisa y se ajusta lo que haga falta, igual que si se hubiera escrito a mano, y{" "}
          <strong>no se guarda nada hasta hacer clic en &quot;Crear declaración&quot;</strong>.
        </P>
        <P>
          Por diseño, el Excel <strong>nunca</strong> define la empresa contratista (se sigue eligiendo del
          desplegable de siempre) ni crea firmas — una firma solo se puede crear firmando de verdad desde la
          cuenta autenticada. Si el sistema no reconoce algún permiso o EPP marcado en el Excel (por ejemplo,
          porque el catálogo cambió), lo indica con un aviso ⚠ para agregarlo a mano.
        </P>
        <P>
          El archivo que se sube queda guardado junto con la declaración — una vez creada aparece el botón{" "}
          <strong>&quot;Ver Excel original&quot;</strong> al lado de &quot;Descargar PDF&quot;/&quot;Descargar
          Excel&quot;, para que quien revisa pueda abrir el documento tal como llegó y compararlo contra lo
          que quedó cargado en el formulario.
        </P>
        <P>
          En una declaración importada, la tabla larga con el detalle de cada actividad (Kinney, permisos,
          EPP) <strong>queda oculta por defecto</strong> — en su lugar se ve solo un resumen (cuántas
          actividades se importaron) con un enlace <strong>&quot;Ver detalle de actividades&quot;</strong>{" "}
          para desplegarla si hace falta corregir algo puntual. Así lo que queda a la vista de una vez es lo
          que de verdad hay que revisar: Datos generales, Alertas automáticas, Firmas electrónicas y el
          Excel original — sin tener que bajar por 20+ tarjetas de actividad ya cargadas. Los datos siguen
          ahí y se guardan igual, se despliegue o no la tabla. Esto no aplica a una declaración que se llena
          a mano desde cero (sin Excel de origen) — ahí el detalle de actividades siempre está a la vista,
          porque es justo lo que se está diligenciando.
        </P>
        <Sub>Firmas electrónicas — no son solo un nombre escrito</Sub>
        <P>
          Al firmar, además del nombre de la persona hay que marcar una casilla de consentimiento explícito
          (&quot;confirmo que firmo electrónicamente...&quot;). El sistema registra <strong>qué cuenta del
          dashboard</strong> ejecutó esa firma (no se puede firmar a nombre de otra cuenta) y guarda una
          huella (hash) del contenido de la declaración en ese momento.
        </P>
        <P>
          Si la declaración se edita después de que alguien firmó, esa firma queda marcada como
          &quot;documento modificado después de firmar&quot; (aviso en amarillo) y el sistema{" "}
          <strong>no deja aprobar</strong> hasta que esa persona vuelva a firmar sobre la versión actual —
          así una firma nunca queda vinculada a un contenido distinto al que realmente se firmó.
        </P>
        <Sub>Aprobar exige al menos una firma vigente</Sub>
        <P>
          El sistema no deja marcar una declaración como &quot;Aprobada&quot; si todavía no tiene ninguna
          firma registrada, o si alguna firma quedó desactualizada por una edición posterior — evita aprobar
          un documento vacío o distinto al que se firmó.
        </P>
        <Sub>Notificación y descarga en PDF o Excel</Sub>
        <P>
          Al aprobar o rechazar, se le avisa por correo al contacto de la empresa contratista (si tiene correo
          registrado) — igual que en Contratistas. Botón <strong>&quot;Descargar PDF&quot;</strong> (arriba
          del formulario, una vez la declaración está guardada) genera el documento completo — datos
          generales, actividades con su evaluación de riesgo y firmas — listo para archivar o imprimir.
        </P>
        <P>
          Botón <strong>&quot;Descargar Excel&quot;</strong>, al lado del PDF. Si la declaración se creó
          importando un Excel, descarga <strong>ese mismo archivo original</strong> (mismo formato con el
          que lo diligenció el contratista, sin reconstruirlo) con una hoja &quot;Decisión SST&quot; agregada
          al final — estado, fecha de la decisión y las observaciones/motivo de la revisión — así el archivo
          que se sube y el que se descarga quedan en el mismo formato. Si la declaración se llenó a mano (sin
          Excel de origen), genera en su lugar el libro propio de 5 hojas que usa la empresa contratista para
          sus propias declaraciones (Declaración de Método, Firmas/Permisos/EPP, Catálogo de Peligros,
          Evaluación según Kinney y Control del Documento).
        </P>
        <Sub>Alertas automáticas — solo son un aviso, nunca deciden</Sub>
        <P>
          Al abrir una declaración para revisarla, el personal de SST/interventoría ve un panel amarillo
          con alertas automáticas cuando alguna actividad no cumple con reglas tomadas de los procedimientos
          de seguridad del cliente (SOP &quot;Safety to Sustain&quot;) — por ejemplo, un permiso de trabajo
          en altura marcado sin el EPP contra caídas correspondiente, una excavación sin medidas de
          mitigación detalladas, un riesgo que sigue alto después de mitigar, o una tarea SIF sin firma de
          Seguridad de Planta. Cada alerta cita de qué procedimiento sale y trae un botón <strong>&quot;Usar
          como motivo de rechazo&quot;</strong> que solo copia un texto sugerido al campo Observaciones —{" "}
          <strong>el sistema nunca aprueba ni rechaza por sí solo</strong>: las alertas son un apoyo para
          decidir, no reemplazan el criterio de quien revisa, y no bloquean aprobar aunque haya alertas
          pendientes. El rol Contratista no ve este panel — es solo para quien revisa.
        </P>
        <P>
          Si en una actividad se diligencian los campos opcionales de altura de trabajo o profundidad de
          excavación (en metros), se habilitan alertas adicionales con los umbrales exactos de las SOP: más
          de 1.8 m sin el permiso de altura marcado, más de 4 m (exige aprobación previa de Zone Safety),
          más de 1.2 m de excavación (exige salida de emergencia), más de 1.3 m (exige retén exterior) y más
          de 5 m (exige andamiaje). Si esos campos quedan vacíos, esas alertas puntuales simplemente no
          aplican — no se asume nada en su ausencia.
        </P>
        <P>
          Cada alerta trae, debajo del botón de motivo de rechazo, un pequeño cuadro para{" "}
          <strong>dejar una nota</strong> sobre esa alerta en particular — por ejemplo, por qué se descartó o
          qué se validó en sitio con el contratista antes de decidir. Las notas quedan con el nombre de quien
          las escribió y la fecha, y se ven ahí mismo cada vez que alguien vuelva a abrir la declaración; no
          reemplazan el campo Observaciones general ni cambian el estado de la declaración por sí solas.
        </P>
        <Sub>Eliminar una declaración</Sub>
        <P>
          En la lista de declaraciones, cada fila tiene un enlace <strong>&quot;Eliminar&quot;</strong> — solo
          visible para el rol Administrador — que pide confirmación con el modal del sistema antes de borrar
          nada (acción irreversible). Queda registrada en Auditoría igual que cualquier otra eliminación.
        </P>
        <Sub>El ciclo enviar → revisar → aprobar/rechazar → subsanar</Sub>
        <P>
          Este es el único formulario en el que el rol Contratista puede escribir (el resto de la app es de
          solo lectura para ese rol). El flujo completo:
        </P>
        <Ol>
          <li>El contratista crea la declaración desde su portal y la deja en estado <strong>Enviada</strong>{" "}
            (o la guarda primero como <strong>Borrador</strong> mientras la termina).</li>
          <li>Al quedar Enviada, se avisa al personal de SST/interventoría por dos canales: la campanita de
            notificaciones del dashboard (siempre) y un correo al <Mono>correo_revisor</Mono> configurado en
            Sistema → Reglas de contratistas (si está configurado) — ver el tema &quot;Notificaciones
            internas&quot;.</li>
          <li>El personal interno la revisa y decide: <strong>Aprobada</strong> (exige al menos una firma
            vigente, como se explica arriba) o <strong>Rechazada</strong> — el sistema exige escribir el
            motivo del rechazo en &quot;Observaciones&quot;, no se puede rechazar sin explicar por qué.</li>
          <li>El contratista ve el motivo del rechazo apenas abre la declaración (aviso en rojo arriba del
            formulario), corrige lo que haga falta y vuelve a poner el estado en Enviada — así las veces que
            haga falta hasta que quede Aprobada. Cada corrección reenviada avisa otra vez, distinguida de una
            declaración nueva (&quot;corregida y reenviada&quot; en vez de &quot;pendiente de revisión&quot;),
            para que quien revisa sepa de un vistazo si ya la había visto.</li>
        </Ol>
        <Nota>
          Solo el personal de SST/interventoría puede poner una declaración en Aprobada o Rechazada — un
          usuario del portal de contratistas no tiene esa opción en su selector de Estado. Tampoco puede
          elegir la empresa contratista al crear o editar: siempre queda fijada a la suya. Al firmar, el
          portal de contratistas solo puede hacerlo como &quot;Supervisor de Seguridad del Contratista&quot;
          — las demás firmas (Delegado, Seguridad de Planta, Líder de Área, Dueño de Territorio) son del
          personal interno de Bavaria.
        </Nota>
      </>
    ),
  },
  {
    id: "autorizacion-ingreso",
    titulo: "Autorización de Ingreso",
    contenido: (
      <>
        <P>
          Formato de autorización de ingreso de personal contratista a la planta — quién queda autorizado a
          entrar, cuándo, en qué área y con qué responsable SISO a cargo del grupo.
        </P>
        <Ul>
          <li>Empresa contratista y área de trabajo.</li>
          <li><strong>Vigencia</strong> (fecha desde/hasta) y <strong>horario</strong> (hora desde/hasta) del
            ingreso autorizado.</li>
          <li><strong>Sitio de encuentro en caso de emergencia</strong> y datos del{" "}
            <strong>responsable SISO del grupo</strong> (nombre, cargo y teléfono).</li>
          <li>Estado del documento (borrador / enviada / aprobada / rechazada), igual que en Declaración de
            Método.</li>
        </Ul>
        <Sub>Inclusiones y exclusiones</Sub>
        <P>
          Al elegir la empresa contratista aparece la lista de sus trabajadores registrados; se marca cada uno
          que queda <strong>incluido</strong> (autorizado a ingresar). Si un trabajador queda{" "}
          <strong>excluido</strong> — se desmarca, o nunca se marca — el sistema exige indicar el motivo de la
          exclusión antes de guardar, para que quede constancia de por qué esa persona no entra.
        </P>
        <Nota>
          El badge &quot;Vigente&quot;/&quot;Fuera de vigencia&quot; en la lista se calcula al vuelo contra la
          fecha de hoy, comparándola con el rango de vigencia — no hay que actualizarlo a mano.
        </Nota>
        <Sub>Descargar PDF</Sub>
        <P>
          Botón <strong>&quot;Descargar PDF&quot;</strong> (arriba del formulario, una vez la autorización está
          guardada) genera el documento con el mismo formato del &quot;AUTORIZACION DE INGRESO PERSONAL
          CONTRATISTA — INCLUSIONES/EXCLUSIONES&quot; físico de la planta: encabezado con el código del
          documento, datos generales, la tabla de trabajadores incluidos (con EPS/ARL/AFP y fecha de inicio de
          contrato) y la de excluidos (con motivo), y las líneas en blanco para firma y sello de la empresa
          contratista y del interventor — listo para imprimir y archivar junto con los demás soportes.
        </P>
      </>
    ),
  },
  {
    id: "funcionarios",
    titulo: "Funcionarios firmantes",
    contenido: (
      <>
        <P>
          Padrón de personas de la empresa autorizadas a firmar declaraciones de método en cada rol interno
          (Delegado, Seguridad de Planta, Líder de Área, Dueño de Territorio) — no incluye al supervisor del
          contratista, porque ese cambia por proyecto y se sigue escribiendo libre al firmar.
        </P>
        <Ul>
          <li>Nombre, cargo, correo y teléfono — se puede desactivar sin borrar el historial.</li>
          <li>
            En el formulario de firma de una declaración, si hay funcionarios activos para el rol elegido,
            aparece un desplegable con sus nombres (más la opción &quot;Otro (escribir manualmente)&quot;)
            en vez de un campo de texto libre — así queda un padrón de quién puede firmar cada rol, aunque
            el sistema siga sin darle una cuenta propia a cada uno.
          </li>
        </Ul>
        <Nota tipo="aviso">
          Solo Administrador puede eliminar un funcionario; cualquier usuario puede crear/editar. Eliminar
          uno no borra las firmas que ya haya hecho — esas quedan con el nombre que se guardó al firmar.
        </Nota>
      </>
    ),
  },
  {
    id: "indicadores-contratistas",
    titulo: "Indicadores",
    contenido: (
      <>
        <P>
          Panel de indicadores de Contratistas y Declaración de Método — cumplimiento por contratista,
          riesgo Kinney, tiempos de aprobación y tendencia mensual. Todo se calcula al vuelo contra los
          datos actuales, no hay resúmenes guardados que se puedan desactualizar.
        </P>
        <Ul>
          <li>Contratistas y trabajadores activos, riesgo Kinney promedio (sin vs. con mitigación), tiempo
            promedio de aprobación de declaraciones y cuántos trabajadores activos tienen algún curso
            Safety Academy obligatorio pendiente (se pone en amarillo si es mayor a cero).</li>
          <li>Radicaciones y declaraciones por estado, en barras.</li>
          <li>Tendencia de los últimos 6 meses (declaraciones y radicaciones creadas por mes).</li>
          <li>Cumplimiento por contratista (trabajadores, radicaciones y declaraciones pendientes) y el
            top 5 de actividades con mayor riesgo sin mitigar.</li>
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
        <P>Solo Administrador. Cuatro pestañas:</P>
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
        <Sub>Reglas de contratistas</Sub>
        <P>
          Catálogos que antes estaban fijos en el código, ahora editables acá: los <strong>cursos Safety
          Academy</strong> que aparecen al registrar un trabajador, los <strong>permisos de trabajo /
          certificados requeridos</strong> y el <strong>equipo de protección personal (EPP)</strong> que
          aparecen en las actividades de una declaración de método, y
          los <strong>días de alerta de vencimiento</strong> (a cuántos días de vencer una planilla se
          considera &quot;por vencer&quot; en el banner de Contratistas), y el <strong>correo para avisos
          de revisión pendiente</strong>. Se pueden desactivar sin borrar el historial de
          trabajadores/actividades que ya los tenían marcados.
        </P>
        <Sub>Aviso al radicar/enviar (no solo al aprobar/rechazar)</Sub>
        <P>
          Si se configura el correo de revisión, además del aviso que ya se manda al contacto de la
          empresa contratista al aprobar o rechazar, ahora también se avisa a ese correo{" "}
          <strong>apenas queda algo pendiente de revisar</strong>: al radicar seguridad social (queda en
          &quot;Pendiente&quot;) y al pasar una declaración de método a &quot;Enviada&quot;. Así quien
          revisa no tiene que estar entrando al sistema a cada rato para enterarse de que hay algo nuevo.
        </P>
        <Sub>Auditoría</Sub>
        <P>
          Traza de solo lectura de quién creó, editó o eliminó cada registro crítico de cumplimiento: empresas
          contratistas, trabajadores, radicaciones de seguridad social, declaraciones de método, autorizaciones
          de ingreso y funcionarios firmantes. Cada fila muestra fecha, tipo de acción, qué registro fue y qué
          usuario lo hizo; en{" "}
          <strong>&quot;Ver cambios&quot;</strong> se ve exactamente qué campos cambiaron y sus valores antes/
          después. Se puede filtrar por tipo de registro. Un registro se guarda aunque el registro original se
          elimine después (para no perder el rastro), y nada acá se puede editar ni borrar.
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
        <Sub>Dar de alta un usuario del portal de contratistas</Sub>
        <P>
          Al elegir el rol <strong>Contratista</strong> (al crear un usuario nuevo, o al cambiar el rol de uno
          existente desde el desplegable de la tabla) el sistema pide elegir a qué{" "}
          <strong>empresa contratista</strong> representa — es lo que define qué datos puede ver y editar ese
          usuario. Es <strong>un usuario por empresa</strong>, no uno por persona: si varios contactos de la
          misma empresa necesitan entrar al portal, comparten esa misma cuenta.
        </P>
        <Nota>No puedes desactivarte ni eliminarte a ti mismo — esos botones aparecen deshabilitados en tu
          propia fila.</Nota>
      </>
    ),
  },
  {
    id: "notificaciones-internas",
    titulo: "Notificaciones internas",
    contenido: (
      <>
        <P>
          El ícono de campana en la parte de arriba del panel (junto al título de cada sección) es una
          bandeja propia, dentro del dashboard, para el personal de SST/interventoría — no depende de revisar
          el correo ni de que Brevo esté configurado. Muestra un contador de cuántas cosas hay pendientes por
          revisar.
        </P>
        <Sub>Qué avisa</Sub>
        <Ul>
          <li><strong>Declaración pendiente de revisión</strong>: una declaración de método nueva quedó en
            estado Enviada.</li>
          <li><strong>Declaración corregida y reenviada</strong>: un contratista subsanó una declaración que
            se le había rechazado y la volvió a enviar — distinto del caso anterior, para que sea obvio de un
            vistazo que ya se había revisado antes.</li>
          <li><strong>Radicación pendiente de revisión</strong>: se radicó seguridad social de un
            trabajador.</li>
        </Ul>
        <P>
          Al hacer clic en una notificación, se marca como leída y te lleva directo a la sección
          correspondiente (Declaración de Método o Contratistas) para revisarla. El botón &quot;Marcar todas
          leídas&quot; vacía el contador de un solo golpe.
        </P>
        <Nota>
          Es un segundo canal, no un reemplazo del correo: los mismos eventos también avisan por correo al{" "}
          <Mono>correo_revisor</Mono> configurado en Sistema → Reglas de contratistas, si está configurado.
          La bandeja de la campana funciona siempre, tenga correo configurado o no.
        </Nota>
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
    id: "politica-privacidad",
    titulo: "Política de privacidad",
    contenido: (
      <>
        <P>
          El módulo de Contratistas guarda datos personales de los trabajadores, incluidos datos de
          afiliación a seguridad social (EPS, ARL, AFP) — datos sensibles bajo la Ley 1581 de 2012
          (&quot;Habeas Data&quot;) en Colombia. El módulo de Cámaras IA también trata datos personales:
          las imágenes que captura cuando detecta una condición de riesgo.
        </P>
        <Ul>
          <li>
            Al registrar un trabajador nuevo, el formulario exige marcar que se cuenta con su autorización
            para tratar esos datos — sin eso, el sistema no deja guardar el registro. Queda la fecha exacta
            de esa autorización.
          </li>
          <li>
            El formulario también permite adjuntar la evidencia (foto o PDF del formato firmado por el
            trabajador) — es opcional, pero respalda la casilla con un documento real en vez de depender
            solo de la palabra de quien registra. Se puede subir al crear el trabajador o después, editando
            su ficha.
          </li>
          <li>
            El texto completo de la política — qué datos se recogen, para qué, cuánto se conservan y cómo
            ejercer los derechos de acceso/corrección/eliminación — está publicado y es de acceso público
            (sin necesidad de iniciar sesión) en{" "}
            <Link href="/politica-privacidad" target="_blank" className="text-corp-blue hover:underline">
              /politica-privacidad
            </Link>
            , y enlazado también desde la pantalla de inicio de sesión.
          </li>
          <li>
            Para las cámaras, el mecanismo de consentimiento es distinto al de los trabajadores: en vez de
            un formulario, la norma exige un <strong>aviso físico visible</strong> en cada zona monitoreada
            (&quot;Zona vigilada por cámaras con IA&quot;), porque cualquier persona que entre a esa zona —
            no solo trabajadores registrados en el sistema — puede quedar captada. Hay un cartel listo para
            imprimir en{" "}
            <Link href="/politica-privacidad/cartel" target="_blank" className="text-corp-blue hover:underline">
              /politica-privacidad/cartel
            </Link>
            , también enlazado desde la sección Cámaras.
          </li>
        </Ul>
        <Nota tipo="aviso">
          El texto de la política y el cartel son un borrador técnico — todavía tienen datos de la empresa
          (NIT, razón social, contacto) pendientes por completar y una revisión legal pendiente antes de
          considerarse definitivos.
        </Nota>
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
