"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import { useDialog } from "@/components/DialogProvider";
import {
  ApiError,
  calificarCapacitacion,
  descargarCertificadoCapacitacion,
  eliminarRegistroCapacitacion,
  enviarCapacitacionesAprobadasExcel,
  exportarCapacitacionesAprobadasExcel,
  iniciarCapacitacion,
  listarContratistas,
  listarPreguntasCapacitacion,
  listarRegistrosCapacitacion,
  obtenerConfiguracionCapacitacion,
  type ConfiguracionCapacitacion,
  type EmpresaContratista,
  type PreguntaCapacitacion,
  type RegistroCapacitacion,
  type ResultadoCapacitacion,
  type Rol,
} from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20";

type Paso = "reporte" | "registro" | "video" | "evaluacion" | "resultado";

const ESTILOS_ESTADO: Record<string, string> = {
  en_curso: "bg-blue-100 text-blue-800",
  aprobado: "bg-emerald-100 text-emerald-800",
  no_aprobado: "bg-red-100 text-red-800",
};

function EstadoBadge({ registro }: { registro: RegistroCapacitacion }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${ESTILOS_ESTADO[registro.estado] ?? "bg-zinc-100 text-zinc-700"}`}>
      {registro.estado_display}
    </span>
  );
}

export default function CapacitacionView({ token, rol }: { token: string; rol: Rol | null }) {
  // El rol Visitante/Auditor (visitas externas/auditorías a planta, cuenta
  // genérica compartida) solo puede tomar el curso — el backend le corta el
  // reporte de registros y el listado de empresas contratistas (ver
  // core.middleware.RestringirVisitanteMiddleware), así que acá ni se piden.
  const esVisitante = rol === "visitante";
  const esInterno = rol !== "contratista" && !esVisitante;
  const esAdmin = rol === "administrador";
  const { confirmar, pedirTexto } = useDialog();
  const [paso, setPaso] = useState<Paso>(esVisitante ? "registro" : "reporte");
  const [registros, setRegistros] = useState<RegistroCapacitacion[] | null>(null);
  const [contratistas, setContratistas] = useState<EmpresaContratista[] | null>(null);
  const [config, setConfig] = useState<ConfiguracionCapacitacion | null>(null);
  const [preguntas, setPreguntas] = useState<PreguntaCapacitacion[] | null>(null);
  const [registroActivo, setRegistroActivo] = useState<RegistroCapacitacion | null>(null);
  const [resultado, setResultado] = useState<ResultadoCapacitacion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [exportando, setExportando] = useState(false);
  const [enviandoListado, setEnviandoListado] = useState(false);
  const [descargandoCertificado, setDescargandoCertificado] = useState<number | null>(null);
  const [eliminando, setEliminando] = useState<number | null>(null);

  function cargarRegistros() {
    if (esVisitante) return;
    listarRegistrosCapacitacion(token)
      .then(setRegistros)
      .catch(() => setError("No se pudo cargar el reporte de capacitación."));
  }

  useEffect(cargarRegistros, [token, esVisitante]);
  useEffect(() => {
    if (esInterno) listarContratistas(token).then(setContratistas).catch(() => {});
  }, [token, esInterno]);
  useEffect(() => {
    obtenerConfiguracionCapacitacion(token).then(setConfig).catch(() => {});
    listarPreguntasCapacitacion(token).then(setPreguntas).catch(() => {});
  }, [token]);

  // Para un visitante no hay "reporte" al que volver — cierra el intento
  // actual y deja lista la pantalla de registro para la próxima persona.
  function volverAlReporte() {
    setRegistroActivo(null);
    setResultado(null);
    if (esVisitante) {
      setPaso("registro");
      return;
    }
    setPaso("reporte");
    cargarRegistros();
  }

  async function exportarAprobados() {
    setExportando(true);
    try {
      await exportarCapacitacionesAprobadasExcel(token);
    } catch {
      setError("No se pudo exportar el Excel de aprobados.");
    } finally {
      setExportando(false);
    }
  }

  async function enviarListadoAprobados() {
    const texto = await pedirTexto({
      titulo: "Enviar listado a portería",
      mensaje:
        "El Excel de aprobados se manda como adjunto, junto con el total, a las direcciones que escribas — por ejemplo, la de portería, para que sepan quién tiene el acceso habilitado. Quedan guardadas para la próxima vez.",
      placeholder: "porteria@planta.com, seguridad@planta.com",
      opcional: false,
      valorInicial: config?.correos_porteria ?? "",
    });
    if (!texto) return;
    const lista = texto
      .split(/[,\n]/)
      .map((c) => c.trim())
      .filter(Boolean);
    if (lista.length === 0) return;

    setEnviandoListado(true);
    setError(null);
    setMensaje(null);
    try {
      const respuesta = await enviarCapacitacionesAprobadasExcel(token, lista);
      setConfig((previo) => (previo ? { ...previo, correos_porteria: lista.join(", ") } : previo));
      if (respuesta.errores.length > 0) {
        setError(respuesta.errores.map((e) => `${e.correo}: ${e.detail}`).join(" — "));
      } else {
        setMensaje(
          `Listado de ${respuesta.total_aprobados} aprobado${respuesta.total_aprobados === 1 ? "" : "s"} enviado a ${respuesta.enviados} destinatario${respuesta.enviados === 1 ? "" : "s"}.`
        );
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar el listado.");
    } finally {
      setEnviandoListado(false);
    }
  }

  async function descargarCertificado(id: number) {
    setDescargandoCertificado(id);
    try {
      await descargarCertificadoCapacitacion(token, id);
    } catch {
      setError("No se pudo descargar el certificado.");
    } finally {
      setDescargandoCertificado(null);
    }
  }

  async function eliminar(registro: RegistroCapacitacion) {
    const ok = await confirmar({
      titulo: "Eliminar capacitación",
      mensaje: `¿Eliminar el registro de "${registro.nombres}"? Esta acción no se puede deshacer.`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
    setEliminando(registro.id);
    try {
      await eliminarRegistroCapacitacion(token, registro.id);
      cargarRegistros();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar el registro.");
    } finally {
      setEliminando(null);
    }
  }

  // Si alguien se quedó a medias en la evaluación (cerró la pestaña, se le
  // fue la conexión), retoma directo en las preguntas — sin hacerlo ver de
  // nuevo el video ni volver a diligenciar el registro.
  function continuarEvaluacion(registro: RegistroCapacitacion) {
    setRegistroActivo(registro);
    setPaso("evaluacion");
  }

  if (paso === "registro") {
    return (
      <FormularioRegistro
        token={token}
        contratistas={contratistas ?? []}
        esInterno={esInterno}
        onCancelar={volverAlReporte}
        onIniciado={(registro) => {
          setRegistroActivo(registro);
          setPaso("video");
        }}
      />
    );
  }

  if (paso === "video" && registroActivo) {
    return (
      <PasoVideo config={config} onContinuar={() => setPaso("evaluacion")} onCancelar={volverAlReporte} />
    );
  }

  if (paso === "evaluacion" && registroActivo) {
    return (
      <PasoEvaluacion
        token={token}
        registro={registroActivo}
        preguntas={preguntas ?? []}
        onCalificado={(res) => {
          setResultado(res);
          setPaso("resultado");
        }}
        onCancelar={volverAlReporte}
      />
    );
  }

  if (paso === "resultado" && resultado) {
    return (
      <PasoResultado resultado={resultado} onVolver={volverAlReporte} onReintentar={() => setPaso("registro")} />
    );
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Inducción previa a ingreso: video de capacitación y evaluación de conocimientos. Queda habilitada por
          empresa contratista cuando tiene una Declaración de Método aprobada, o cuando un Administrador la
          habilita manualmente desde la ficha de la empresa en Contratistas.
        </p>
        <div className="flex shrink-0 flex-wrap gap-3">
          <button
            type="button"
            onClick={exportarAprobados}
            disabled={exportando}
            className="rounded-lg border border-corp-border px-4 py-2 text-sm font-medium text-corp-navy transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {exportando ? "Exportando…" : "Exportar aprobados (Excel)"}
          </button>
          {esAdmin && (
            <button
              type="button"
              onClick={enviarListadoAprobados}
              disabled={enviandoListado}
              className="rounded-lg border border-corp-border px-4 py-2 text-sm font-medium text-corp-navy transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {enviandoListado ? "Enviando…" : "Enviar listado a portería"}
            </button>
          )}
          <button
            type="button"
            onClick={() => setPaso("registro")}
            className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white"
          >
            + Nueva capacitación
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}
      {mensaje && (
        <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {mensaje}
        </div>
      )}

      {registros?.length === 0 && (
        <p className="mt-6 text-sm text-corp-muted">Todavía no hay capacitaciones registradas — usa el botón de arriba.</p>
      )}

      {registros && registros.length > 0 && (
        <div className="mt-6 overflow-x-auto rounded-xl border border-corp-border bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-corp-muted">
              <tr>
                <th className="px-4 py-2.5">Nombre</th>
                {esInterno && <th className="px-4 py-2.5">Empresa</th>}
                <th className="px-4 py-2.5">Documento</th>
                <th className="px-4 py-2.5">Trabajador vinculado</th>
                <th className="px-4 py-2.5">Calificación</th>
                <th className="px-4 py-2.5">Estado</th>
                <th className="px-4 py-2.5">Fecha</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-corp-border">
              {registros.map((r) => (
                <tr key={r.id}>
                  <td className="px-4 py-2.5 font-medium text-corp-navy">{r.nombres}</td>
                  {esInterno && <td className="px-4 py-2.5">{r.contratista_nombre}</td>}
                  <td className="px-4 py-2.5">{r.documento || "—"}</td>
                  <td className="px-4 py-2.5">{r.trabajador_nombre || "—"}</td>
                  <td className="px-4 py-2.5">{r.calificacion !== null ? `${r.calificacion}%` : "—"}</td>
                  <td className="px-4 py-2.5">
                    <EstadoBadge registro={r} />
                  </td>
                  <td className="px-4 py-2.5">{new Date(r.iniciado_en).toLocaleDateString("es-CO")}</td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex flex-wrap justify-end gap-x-3 gap-y-1">
                      {r.estado === "aprobado" && (
                        <button
                          type="button"
                          onClick={() => descargarCertificado(r.id)}
                          disabled={descargandoCertificado === r.id}
                          className="text-xs font-medium text-corp-gold hover:underline disabled:opacity-60"
                        >
                          {descargandoCertificado === r.id ? "Descargando…" : "Certificado"}
                        </button>
                      )}
                      {r.estado === "en_curso" && (
                        <button
                          type="button"
                          onClick={() => continuarEvaluacion(r)}
                          className="text-xs font-medium text-corp-gold hover:underline"
                        >
                          Continuar evaluación
                        </button>
                      )}
                      {esAdmin && (
                        <button
                          type="button"
                          onClick={() => eliminar(r)}
                          disabled={eliminando === r.id}
                          className="text-xs font-medium text-red-600 hover:underline disabled:opacity-60"
                        >
                          {eliminando === r.id ? "Eliminando…" : "Eliminar"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function FormularioRegistro({
  token,
  contratistas,
  esInterno,
  onCancelar,
  onIniciado,
}: {
  token: string;
  contratistas: EmpresaContratista[];
  esInterno: boolean;
  onCancelar: () => void;
  onIniciado: (registro: RegistroCapacitacion) => void;
}) {
  const [contratistaId, setContratistaId] = useState<number | "">("");
  const [nombres, setNombres] = useState("");
  const [correo, setCorreo] = useState("");
  const [documento, setDocumento] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const registro = await iniciarCapacitacion(token, {
        contratista: esInterno ? (contratistaId as number) : undefined,
        nombres,
        correo: correo || undefined,
        documento: documento || undefined,
      });
      onIniciado(registro);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar la capacitación.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div>
      <button type="button" onClick={onCancelar} className="text-sm font-medium text-corp-gold hover:underline">
        ← Volver
      </button>
      <div className="mx-auto mt-4 max-w-md rounded-2xl border border-corp-border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-corp-navy">Curso de capacitación</h2>
        <p className="mt-1 text-sm text-corp-muted">Registro del participante</p>
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          {esInterno && (
            <select
              required
              value={contratistaId}
              onChange={(e) => setContratistaId(Number(e.target.value))}
              className={INPUT}
            >
              <option value="">Empresa contratista…</option>
              {contratistas.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          )}
          <input
            required
            placeholder="Nombre completo"
            value={nombres}
            onChange={(e) => setNombres(e.target.value)}
            className={INPUT}
          />
          <input
            type="email"
            placeholder="Correo electrónico (opcional)"
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            className={INPUT}
          />
          <input
            placeholder="Documento de identidad (opcional)"
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            className={INPUT}
          />
          <p className="text-xs text-corp-muted">
            Si el documento coincide con un trabajador ya radicado, su ficha quedará marcada automáticamente al
            aprobar.
          </p>

          {error && (
            <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="w-full rounded-lg bg-corp-blue py-2.5 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {enviando ? "Cargando…" : "Iniciar curso"}
          </button>
        </form>
      </div>
    </div>
  );
}

function PasoVideo({
  config,
  onContinuar,
  onCancelar,
}: {
  config: ConfiguracionCapacitacion | null;
  onContinuar: () => void;
  onCancelar: () => void;
}) {
  const [terminado, setTerminado] = useState(false);
  const [avisoAdelanto, setAvisoAdelanto] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const maxAlcanzado = useRef(0);

  function manejarTimeUpdate() {
    const video = videoRef.current;
    if (!video) return;
    if (video.currentTime > maxAlcanzado.current) {
      maxAlcanzado.current = video.currentTime;
    }
  }

  // No se puede adelantar el video (arrastrando la barra o con el teclado):
  // si intenta saltar más allá de lo que ya vio, se regresa ahí mismo — solo
  // puede retroceder para repasar algo, no saltarse el resto.
  function manejarSeeking() {
    const video = videoRef.current;
    if (!video) return;
    if (video.currentTime > maxAlcanzado.current + 0.5) {
      video.currentTime = maxAlcanzado.current;
      setAvisoAdelanto(true);
      window.setTimeout(() => setAvisoAdelanto(false), 2500);
    }
  }

  return (
    <div>
      <button type="button" onClick={onCancelar} className="text-sm font-medium text-corp-gold hover:underline">
        ← Cancelar
      </button>
      <div className="mx-auto mt-4 max-w-2xl rounded-2xl border border-corp-border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-corp-navy">{config?.titulo_curso || "Video de Capacitación"}</h2>
        {config?.video_url ? (
          <video
            ref={videoRef}
            controls
            playsInline
            preload="metadata"
            controlsList="nodownload noplaybackrate"
            disablePictureInPicture
            onContextMenu={(e) => e.preventDefault()}
            onTimeUpdate={manejarTimeUpdate}
            onSeeking={manejarSeeking}
            onEnded={() => setTerminado(true)}
            className="mt-4 w-full rounded-lg bg-black"
          >
            <source src={config.video_url} type="video/mp4" />
            Tu navegador no soporta la reproducción de este video.
          </video>
        ) : (
          <p className="mt-4 text-sm text-corp-muted">Cargando video…</p>
        )}

        {avisoAdelanto && (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            No puedes adelantar el video — debes verlo completo de principio a fin.
          </div>
        )}

        <div
          className={`mt-4 rounded-lg px-3 py-2 text-sm ${
            terminado ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
          }`}
        >
          {terminado ? "¡Video terminado! Ya puedes continuar con la evaluación." : "Debes terminar el video para continuar."}
        </div>

        <button
          type="button"
          disabled={!terminado}
          onClick={onContinuar}
          className="mt-4 w-full rounded-lg bg-corp-blue py-2.5 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Continuar a evaluación
        </button>
      </div>
    </div>
  );
}

function PasoEvaluacion({
  token,
  registro,
  preguntas,
  onCalificado,
  onCancelar,
}: {
  token: string;
  registro: RegistroCapacitacion;
  preguntas: PreguntaCapacitacion[];
  onCalificado: (resultado: ResultadoCapacitacion) => void;
  onCancelar: () => void;
}) {
  const [respuestas, setRespuestas] = useState<Array<number | null>>(() => preguntas.map(() => null));
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  function elegir(indicePregunta: number, indiceOpcion: number) {
    setRespuestas((previas) => previas.map((valor, i) => (i === indicePregunta ? indiceOpcion : valor)));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (respuestas.some((r) => r === null)) {
      setError("Favor de responder todas las preguntas antes de enviar.");
      return;
    }
    setError(null);
    setEnviando(true);
    try {
      const resultado = await calificarCapacitacion(token, registro.id, respuestas as number[]);
      onCalificado(resultado);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo calificar la evaluación.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div>
      <button type="button" onClick={onCancelar} className="text-sm font-medium text-corp-gold hover:underline">
        ← Cancelar
      </button>
      <form onSubmit={handleSubmit} className="mx-auto mt-4 max-w-2xl space-y-5 rounded-2xl border border-corp-border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-corp-navy">Evaluación</h2>

        {preguntas.map((pregunta, indicePregunta) => (
          <div key={pregunta.id} className="border-b border-corp-border pb-4 last:border-0">
            <p className="text-sm font-semibold text-corp-navy">{pregunta.texto}</p>
            <div className="mt-2 space-y-1.5">
              {pregunta.opciones.map((opcion, indiceOpcion) => (
                <label key={indiceOpcion} className="flex items-center gap-2 text-sm text-corp-navy">
                  <input
                    type="radio"
                    name={`pregunta-${pregunta.id}`}
                    checked={respuestas[indicePregunta] === indiceOpcion}
                    onChange={() => elegir(indicePregunta, indiceOpcion)}
                    className="h-4 w-4 accent-corp-blue"
                  />
                  {opcion}
                </label>
              ))}
            </div>
          </div>
        ))}

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={enviando || preguntas.length === 0}
          className="w-full rounded-lg bg-corp-blue py-2.5 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {enviando ? "Calificando…" : "Enviar evaluación"}
        </button>
      </form>
    </div>
  );
}

function PasoResultado({
  resultado,
  onVolver,
  onReintentar,
}: {
  resultado: ResultadoCapacitacion;
  onVolver: () => void;
  onReintentar: () => void;
}) {
  const aprobado = resultado.estado === "aprobado";
  const fechaHoy = new Date().toLocaleDateString("es-CO");

  return (
    <div className="mx-auto max-w-2xl">
      <div className="rounded-2xl border border-corp-border bg-white p-6 text-center shadow-sm">
        <h2 className={`text-xl font-bold ${aprobado ? "text-emerald-700" : "text-red-700"}`}>
          {resultado.estado_display}
        </h2>
        <p className="mt-2 text-sm text-corp-muted">Respuestas correctas:</p>
        <p className="text-lg font-semibold text-corp-navy">
          {resultado.correctas} de {resultado.total}
        </p>
        <p className="mt-3 text-sm text-corp-muted">Calificación final:</p>
        <p className="text-4xl font-bold text-corp-navy">{resultado.calificacion}%</p>

        {aprobado ? (
          <div className="mt-6 rounded-xl border-2 border-corp-navy p-6">
            <h3 className="text-lg font-bold text-corp-navy">CERTIFICADO DE CAPACITACIÓN</h3>
            <p className="mt-2 text-sm text-corp-muted">
              GuardIA otorga el presente reconocimiento a:
            </p>
            <p className="mt-2 text-2xl font-semibold text-corp-navy">{resultado.nombres}</p>
            <p className="mt-2 text-sm text-corp-muted">
              Por haber completado y aprobado satisfactoriamente la inducción de:
            </p>
            <p className="text-sm font-semibold text-corp-navy">Seguridad y Salud Ocupacional</p>
            <p className="mt-3 text-xs text-corp-muted">Fecha de emisión: {fechaHoy}</p>
          </div>
        ) : null}

        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
          {aprobado ? (
            <button
              type="button"
              onClick={() => window.print()}
              className="rounded-lg bg-corp-navy px-4 py-2 text-sm font-semibold text-white hover:bg-corp-navy/90"
            >
              Imprimir / guardar certificado
            </button>
          ) : (
            <button
              type="button"
              onClick={onReintentar}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
            >
              Volver a intentar
            </button>
          )}
          <button
            type="button"
            onClick={onVolver}
            className="rounded-lg border border-corp-border px-4 py-2 text-sm font-medium text-corp-navy hover:bg-zinc-50"
          >
            Volver al reporte
          </button>
        </div>
      </div>
    </div>
  );
}
