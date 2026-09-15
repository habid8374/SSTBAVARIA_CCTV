import { Mono, Nota, Ol, P, Sub, Ul } from "@/components/DocTexto";

/** Contenido de la política de tratamiento de datos personales (Habeas Data,
 * Ley 1581 de 2012 y Decreto 1377 de 2013). Es un borrador técnico: los datos
 * propios de la empresa (NIT, razón social, representante legal, contacto)
 * están marcados como [placeholder] y deben ser completados y revisados por
 * el área legal/jurídica del cliente antes de considerarse vinculante. */

function Placeholder({ children }: { children: string }) {
  return (
    <span className="rounded bg-amber-100 px-1 py-0.5 font-mono text-xs text-amber-800">[{children}]</span>
  );
}

export default function PoliticaPrivacidadContenido() {
  return (
    <div className="space-y-2">
      <Nota tipo="aviso">
        Este documento es un <strong>borrador técnico</strong> generado como parte del sistema SST Bavaria
        Cámaras IA. Los campos marcados como <Placeholder>dato pendiente</Placeholder> deben completarse con
        la información real de la empresa, y el texto completo debe ser revisado por el área jurídica o un
        abogado antes de publicarse como política definitiva y vinculante.
      </Nota>

      <Sub>1. Responsable del tratamiento</Sub>
      <P>
        <Placeholder>Razón social de la empresa</Placeholder>, identificada con NIT{" "}
        <Placeholder>NIT</Placeholder>, con domicilio en <Placeholder>ciudad / dirección</Placeholder>, es
        responsable del tratamiento de los datos personales que se recolectan a través del sistema SST
        Bavaria Cámaras IA, en los términos de la Ley 1581 de 2012, el Decreto 1377 de 2013 y las demás
        normas que los reglamenten o sustituyan.
      </P>
      <P>
        Datos de contacto para asuntos de protección de datos:{" "}
        <Placeholder>correo de contacto</Placeholder> — <Placeholder>teléfono de contacto</Placeholder>.
      </P>

      <Sub>2. Datos personales que se recolectan</Sub>
      <P>El sistema recolecta y almacena, según el módulo:</P>
      <Ul>
        <li>
          <strong>Trabajadores de empresas contratistas:</strong> nombres, apellidos, documento de
          identidad, tipo de vinculación, fecha de inicio de contrato, cursos de seguridad realizados
          (Safety Academy) y afiliación a <strong>EPS, ARL y AFP</strong> (seguridad social).
        </li>
        <li>
          <strong>Radicaciones de seguridad social:</strong> soportes de pago (PILA) que pueden contener
          datos de afiliación y aportes.
        </li>
        <li>
          <strong>Usuarios del sistema:</strong> nombre de usuario, correo electrónico y rol asignado.
        </li>
        <li>
          <strong>Cámaras de videovigilancia (IA):</strong> imágenes (snapshots) capturadas únicamente
          cuando se detecta un evento de riesgo definido en las reglas de zona (por ejemplo, ausencia de
          casco o presencia en zona restringida). El sistema <strong>no</strong> transmite ni almacena video
          continuo en la nube — el procesamiento de video en vivo ocurre en el equipo local, dentro de la
          red de la planta.
        </li>
      </Ul>
      <Nota>
        Los datos de afiliación a EPS, ARL y AFP se consideran <strong>datos sensibles</strong> por estar
        relacionados con la salud y la seguridad social, por lo que reciben un tratamiento reforzado bajo la
        Ley 1581 de 2012.
      </Nota>

      <Sub>3. Finalidad del tratamiento</Sub>
      <P>Los datos personales se usan exclusivamente para:</P>
      <Ul>
        <li>Verificar el cumplimiento de requisitos de Seguridad y Salud en el Trabajo (SST) de los trabajadores de contratistas antes de autorizar su ingreso a las instalaciones.</li>
        <li>Controlar la vigencia de la afiliación a seguridad social y las radicaciones mensuales de pago (PILA).</li>
        <li>Elaborar y aprobar declaraciones de método y evaluaciones de riesgo para trabajos específicos.</li>
        <li>Generar alertas automáticas de seguridad a partir del análisis de video (por ejemplo, uso de elementos de protección personal), con el fin de prevenir accidentes laborales.</li>
        <li>Administrar los usuarios que acceden al sistema y su nivel de permisos.</li>
        <li>Notificar por correo electrónico decisiones sobre radicaciones y declaraciones de método a los contratistas correspondientes.</li>
      </Ul>
      <P>Los datos no se usan para fines distintos a los aquí descritos, ni se venden ni se ceden a terceros con fines comerciales.</P>

      <Sub>4. Autorización</Sub>
      <P>
        Al registrar un trabajador en el sistema, la persona que radica la información (representante de la
        empresa contratista) declara contar con la autorización previa, expresa e informada del trabajador
        para el tratamiento de sus datos personales, incluidos los datos sensibles de afiliación a seguridad
        social, conforme a esta política. Esta autorización queda registrada en el sistema con fecha y hora,
        y opcionalmente puede respaldarse adjuntando la evidencia (foto o PDF del formato firmado por el
        trabajador).
      </P>

      <Sub>5. Derechos del titular (Habeas Data)</Sub>
      <P>Como titular de los datos, toda persona tiene derecho a:</P>
      <Ul>
        <li>Conocer, actualizar y rectificar sus datos personales.</li>
        <li>Solicitar prueba de la autorización otorgada.</li>
        <li>Ser informado sobre el uso que se le ha dado a sus datos.</li>
        <li>Presentar quejas ante la Superintendencia de Industria y Comercio (SIC) por infracciones a la ley.</li>
        <li>Revocar la autorización y/o solicitar la supresión (eliminación) del dato, cuando no exista un deber legal o contractual que obligue a conservarlo.</li>
        <li>Acceder de forma gratuita a sus datos personales que hayan sido objeto de tratamiento.</li>
      </Ul>

      <Sub>6. Cómo ejercer estos derechos</Sub>
      <P>Las solicitudes relacionadas con el ejercicio de estos derechos pueden presentarse a través de:</P>
      <Ol>
        <li>
          Correo electrónico a <Placeholder>correo de contacto</Placeholder>, indicando nombre completo,
          documento de identidad y la solicitud puntual.
        </li>
        <li>Comunicación escrita dirigida a <Placeholder>dirección física / responsable SST</Placeholder>.</li>
      </Ol>
      <P>
        La solicitud será atendida dentro de los términos establecidos por la ley (consultas: máximo 10 días
        hábiles; reclamos: máximo 15 días hábiles, prorrogable una vez por 8 días hábiles adicionales).
      </P>

      <Sub>7. Seguridad y conservación de los datos</Sub>
      <P>
        Los datos se almacenan en una base de datos con acceso restringido por autenticación y roles de
        usuario (Administrador / Operador). Las comunicaciones con el sistema viajan cifradas (HTTPS). Los
        datos se conservan mientras sean necesarios para las finalidades descritas y mientras exista una
        relación contractual vigente con la empresa contratista, salvo que la ley exija un período de
        conservación distinto (por ejemplo, obligaciones laborales o de seguridad social).
      </P>

      <Sub>8. Encargados del tratamiento y transferencia a terceros</Sub>
      <P>
        Para el envío de notificaciones por correo electrónico (por ejemplo, aviso de aprobación o rechazo
        de una radicación), el sistema utiliza el servicio de terceros <Mono>Brevo</Mono> (proveedor de
        correo transaccional), que actúa como encargado del tratamiento únicamente para el envío de esos
        mensajes. Los datos de video procesados por el módulo de Cámaras IA se analizan localmente, dentro
        de la red de la planta, y solo se envían a la nube los metadatos del evento y, cuando aplica, una
        imagen puntual (snapshot) del momento de la alerta — nunca el video en vivo ni grabaciones continuas.
      </P>
      <P>El sistema no transfiere datos personales a terceros distintos de los aquí mencionados, salvo requerimiento de autoridad competente.</P>

      <Sub>9. Vigencia</Sub>
      <P>
        Esta política rige a partir de su publicación en el sistema y podrá ser modificada en cualquier
        momento para reflejar cambios normativos o del sistema. La versión vigente siempre estará disponible
        en esta misma dirección.
      </P>
      <p className="text-xs text-corp-muted">
        Última actualización del borrador: <Placeholder>fecha de revisión legal</Placeholder>.
      </p>
    </div>
  );
}
