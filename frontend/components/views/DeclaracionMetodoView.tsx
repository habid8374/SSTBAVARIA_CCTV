"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import {
  ApiError,
  actualizarDeclaracion,
  crearDeclaracion,
  descargarDeclaracionPdf,
  firmarDeclaracion,
  listarContratistas,
  listarDeclaraciones,
  obtenerCatalogosContratistas,
  type Catalogos,
  type DeclaracionMetodo,
  type EmpresaContratista,
  type EstadoDeclaracion,
  type FirmaMetodo,
  type NuevaActividadMetodo,
  type NuevaDeclaracion,
  type Rol,
  type RolFirma,
} from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20";
const TEXTAREA = `${INPUT} min-h-[70px] resize-y`;

const PROBABILIDADES = [
  { valor: 10, etiqueta: "10 — Esperado" },
  { valor: 6, etiqueta: "6 — Muy posible" },
  { valor: 3, etiqueta: "3 — Raro" },
  { valor: 1, etiqueta: "1 — Improbable pero posible" },
  { valor: 0.5, etiqueta: "0.5 — Concebible pero improbable" },
  { valor: 0.1, etiqueta: "0.1 — Casi improbable" },
];

const FRECUENCIAS = [
  { valor: 10, etiqueta: "10 — Continuamente" },
  { valor: 6, etiqueta: "6 — Regularmente / diario" },
  { valor: 3, etiqueta: "3 — De vez en cuando / semanal" },
  { valor: 2, etiqueta: "2 — Algunas veces / mensual" },
  { valor: 1, etiqueta: "1 — Rara vez / anual" },
  { valor: 0.5, etiqueta: "0.5 — Muy rara vez" },
];

const IMPACTOS = [
  { valor: 40, etiqueta: "40 — Catástrofe (varias fatalidades)" },
  { valor: 15, etiqueta: "15 — Muy serio (una fatalidad)" },
  { valor: 7, etiqueta: "7 — Serio (discapacidad)" },
  { valor: 3, etiqueta: "3 — Importante (lesión con baja)" },
  { valor: 1, etiqueta: "1 — Menor (lesión sin baja)" },
];

const ESTADOS: { valor: EstadoDeclaracion; etiqueta: string }[] = [
  { valor: "borrador", etiqueta: "Borrador" },
  { valor: "enviada", etiqueta: "Enviada" },
  { valor: "aprobada", etiqueta: "Aprobada" },
  { valor: "rechazada", etiqueta: "Rechazada" },
];

function nivelRiesgo(valor: number): { etiqueta: string; color: string } {
  if (valor > 400) return { etiqueta: "Muy alto", color: "bg-red-100 text-red-800" };
  if (valor > 200) return { etiqueta: "Alto", color: "bg-orange-100 text-orange-800" };
  if (valor > 70) return { etiqueta: "Considerable", color: "bg-amber-100 text-amber-800" };
  if (valor > 20) return { etiqueta: "Posible", color: "bg-yellow-100 text-yellow-800" };
  return { etiqueta: "Bajo", color: "bg-emerald-100 text-emerald-800" };
}

function riesgoMasAlto(declaracion: DeclaracionMetodo): number {
  return declaracion.actividades.reduce((max, a) => Math.max(max, a.riesgo_sin, a.riesgo_con), 0);
}

function EstadoBadge({ estado }: { estado: EstadoDeclaracion }) {
  const estilos: Record<EstadoDeclaracion, string> = {
    borrador: "bg-zinc-100 text-zinc-700",
    enviada: "bg-blue-100 text-blue-800",
    aprobada: "bg-emerald-100 text-emerald-800",
    rechazada: "bg-red-100 text-red-800",
  };
  const etiquetas: Record<EstadoDeclaracion, string> = {
    borrador: "Borrador",
    enviada: "Enviada",
    aprobada: "Aprobada",
    rechazada: "Rechazada",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${estilos[estado]}`}>{etiquetas[estado]}</span>
  );
}

export default function DeclaracionMetodoView({ token }: { token: string; rol: Rol | null }) {
  const [declaraciones, setDeclaraciones] = useState<DeclaracionMetodo[] | null>(null);
  const [contratistas, setContratistas] = useState<EmpresaContratista[] | null>(null);
  const [catalogos, setCatalogos] = useState<Catalogos | null>(null);
  const [seleccionada, setSeleccionada] = useState<DeclaracionMetodo | "nueva" | null>(null);
  const [error, setError] = useState<string | null>(null);

  function cargarDeclaraciones() {
    listarDeclaraciones(token)
      .then(setDeclaraciones)
      .catch(() => setError("No se pudo cargar la lista de declaraciones de método."));
  }

  useEffect(cargarDeclaraciones, [token]);
  useEffect(() => {
    listarContratistas(token)
      .then(setContratistas)
      .catch(() => {});
  }, [token]);
  useEffect(() => {
    obtenerCatalogosContratistas(token)
      .then(setCatalogos)
      .catch(() => {});
  }, [token]);

  if (seleccionada && catalogos) {
    return (
      <FormularioDeclaracion
        token={token}
        declaracionInicial={seleccionada === "nueva" ? null : seleccionada}
        contratistas={contratistas ?? []}
        catalogos={catalogos}
        onVolver={() => {
          setSeleccionada(null);
          cargarDeclaraciones();
        }}
      />
    );
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Declaración de método y evaluación de riesgo (Kinney) por trabajo puntual.
        </p>
        <button
          type="button"
          onClick={() => setSeleccionada("nueva")}
          disabled={!contratistas?.length}
          title={!contratistas?.length ? "Registra primero una empresa contratista en “Contratistas”" : undefined}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:cursor-not-allowed disabled:opacity-50"
        >
          + Nueva declaración
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {declaraciones?.length === 0 && (
        <p className="mt-6 text-sm text-corp-muted">
          Todavía no hay declaraciones de método registradas — usa el botón de arriba.
        </p>
      )}

      {declaraciones && declaraciones.length > 0 && (
        <div className="mt-6 overflow-x-auto rounded-xl border border-corp-border bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-corp-muted">
              <tr>
                <th className="px-4 py-2.5">Trabajo</th>
                <th className="px-4 py-2.5">Contratista</th>
                <th className="px-4 py-2.5">Planta / área</th>
                <th className="px-4 py-2.5">Fecha</th>
                <th className="px-4 py-2.5">Actividades</th>
                <th className="px-4 py-2.5">Riesgo más alto</th>
                <th className="px-4 py-2.5">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-corp-border">
              {declaraciones.map((d) => {
                const riesgo = riesgoMasAlto(d);
                const nivel = nivelRiesgo(riesgo);
                return (
                  <tr
                    key={d.id}
                    onClick={() => setSeleccionada(d)}
                    className="cursor-pointer hover:bg-corp-blue-light/40"
                  >
                    <td className="max-w-xs truncate px-4 py-2.5 font-medium text-corp-navy">
                      {d.descripcion_trabajo}
                    </td>
                    <td className="px-4 py-2.5">{d.contratista_nombre}</td>
                    <td className="px-4 py-2.5">{d.planta_area || "—"}</td>
                    <td className="px-4 py-2.5">{d.fecha_elaboracion}</td>
                    <td className="px-4 py-2.5">{d.actividades.length}</td>
                    <td className="px-4 py-2.5">
                      {d.actividades.length > 0 ? (
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${nivel.color}`}>
                          {nivel.etiqueta} ({riesgo})
                        </span>
                      ) : (
                        <span className="text-xs text-corp-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <EstadoBadge estado={d.estado} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

type ActividadForm = NuevaActividadMetodo & { clave: string };

function clave() {
  return Math.random().toString(36).slice(2);
}

function actividadVacia(orden: number): ActividadForm {
  return {
    clave: clave(),
    orden,
    secuencia: "",
    tecnicas_herramientas: "",
    descripcion_riesgo: "",
    probabilidad_sin: 3,
    frecuencia_sin: 3,
    impacto_sin: 1,
    medidas_mitigacion: "",
    probabilidad_con: 1,
    frecuencia_con: 3,
    impacto_con: 1,
    permisos_requeridos: [],
    tarea_sif: false,
  };
}

function FormularioDeclaracion({
  token,
  declaracionInicial,
  contratistas,
  catalogos,
  onVolver,
}: {
  token: string;
  declaracionInicial: DeclaracionMetodo | null;
  contratistas: EmpresaContratista[];
  catalogos: Catalogos;
  onVolver: () => void;
}) {
  const [declaracion, setDeclaracion] = useState<DeclaracionMetodo | null>(declaracionInicial);
  const [contratistaId, setContratistaId] = useState(
    String(declaracionInicial?.contratista ?? contratistas[0]?.id ?? "")
  );
  const [plantaArea, setPlantaArea] = useState(declaracionInicial?.planta_area ?? "");
  const [numeroPedido, setNumeroPedido] = useState(declaracionInicial?.numero_pedido ?? "");
  const [gerenteProyecto, setGerenteProyecto] = useState(declaracionInicial?.gerente_proyecto ?? "");
  const [contactoNombre, setContactoNombre] = useState(declaracionInicial?.contacto_nombre ?? "");
  const [contactoTelefono, setContactoTelefono] = useState(declaracionInicial?.contacto_telefono ?? "");
  const [fechaElaboracion, setFechaElaboracion] = useState(
    declaracionInicial?.fecha_elaboracion ?? new Date().toISOString().slice(0, 10)
  );
  const [duracionDias, setDuracionDias] = useState(String(declaracionInicial?.duracion_dias ?? 1));
  const [descripcionTrabajo, setDescripcionTrabajo] = useState(declaracionInicial?.descripcion_trabajo ?? "");
  const [estado, setEstado] = useState<EstadoDeclaracion>(declaracionInicial?.estado ?? "borrador");
  const [observaciones, setObservaciones] = useState(declaracionInicial?.observaciones ?? "");
  const [actividades, setActividades] = useState<ActividadForm[]>(
    declaracionInicial?.actividades.length
      ? declaracionInicial.actividades.map((a) => ({ ...a, clave: clave() }))
      : [actividadVacia(0)]
  );
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [descargandoPdf, setDescargandoPdf] = useState(false);

  async function descargarPdf() {
    if (!declaracion) return;
    setDescargandoPdf(true);
    try {
      await descargarDeclaracionPdf(token, declaracion.id);
    } catch {
      setError("No se pudo descargar el PDF.");
    } finally {
      setDescargandoPdf(false);
    }
  }

  function actualizarActividad(indice: number, cambios: Partial<ActividadForm>) {
    setActividades((actual) => actual.map((a, i) => (i === indice ? { ...a, ...cambios } : a)));
  }

  function agregarActividad() {
    setActividades((actual) => [...actual, actividadVacia(actual.length)]);
  }

  function quitarActividad(indice: number) {
    setActividades((actual) => actual.filter((_, i) => i !== indice));
  }

  function alternarPermiso(indice: number, permiso: string, marcado: boolean) {
    setActividades((actual) =>
      actual.map((a, i) => {
        if (i !== indice) return a;
        const permisos = marcado
          ? [...a.permisos_requeridos, permiso]
          : a.permisos_requeridos.filter((p) => p !== permiso);
        return { ...a, permisos_requeridos: permisos };
      })
    );
  }

  async function guardar(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMensaje(null);
    setEnviando(true);
    const payload: NuevaDeclaracion = {
      contratista: Number(contratistaId),
      planta_area: plantaArea,
      numero_pedido: numeroPedido,
      gerente_proyecto: gerenteProyecto,
      contacto_nombre: contactoNombre,
      contacto_telefono: contactoTelefono,
      fecha_elaboracion: fechaElaboracion,
      duracion_dias: Number(duracionDias) || 1,
      descripcion_trabajo: descripcionTrabajo,
      estado,
      observaciones,
      actividades: actividades.map((a, i) => ({
        orden: i,
        secuencia: a.secuencia,
        tecnicas_herramientas: a.tecnicas_herramientas,
        descripcion_riesgo: a.descripcion_riesgo,
        probabilidad_sin: a.probabilidad_sin,
        frecuencia_sin: a.frecuencia_sin,
        impacto_sin: a.impacto_sin,
        medidas_mitigacion: a.medidas_mitigacion,
        probabilidad_con: a.probabilidad_con,
        frecuencia_con: a.frecuencia_con,
        impacto_con: a.impacto_con,
        permisos_requeridos: a.permisos_requeridos,
        tarea_sif: a.tarea_sif,
      })),
    };
    try {
      const guardada = declaracion
        ? await actualizarDeclaracion(token, declaracion.id, payload)
        : await crearDeclaracion(token, payload);
      setDeclaracion(guardada);
      setActividades(guardada.actividades.map((a) => ({ ...a, clave: clave() })));
      setMensaje("Declaración guardada.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la declaración de método.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <button type="button" onClick={onVolver} className="text-sm font-medium text-corp-blue hover:underline">
          ← Volver a la lista
        </button>
        {declaracion && (
          <button
            type="button"
            onClick={descargarPdf}
            disabled={descargandoPdf}
            className="rounded-lg border border-corp-border px-3 py-1.5 text-xs font-semibold text-corp-navy transition hover:border-corp-blue disabled:opacity-60"
          >
            {descargandoPdf ? "Generando…" : "Descargar PDF"}
          </button>
        )}
      </div>

      <form onSubmit={guardar} className="mt-4 space-y-6">
        <div className="rounded-2xl border border-corp-border bg-white p-5">
          <h3 className="text-base font-semibold text-corp-navy">Datos generales</h3>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Campo label="Empresa contratista">
              <select
                required
                value={contratistaId}
                onChange={(e) => setContratistaId(e.target.value)}
                className={INPUT}
              >
                <option value="" disabled>
                  Selecciona una empresa
                </option>
                {contratistas.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo label="Planta / área">
              <input value={plantaArea} onChange={(e) => setPlantaArea(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Número de pedido">
              <input value={numeroPedido} onChange={(e) => setNumeroPedido(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Gerente de proyecto">
              <input
                value={gerenteProyecto}
                onChange={(e) => setGerenteProyecto(e.target.value)}
                className={INPUT}
              />
            </Campo>
            <Campo label="Contacto — nombre">
              <input value={contactoNombre} onChange={(e) => setContactoNombre(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Contacto — teléfono">
              <input
                value={contactoTelefono}
                onChange={(e) => setContactoTelefono(e.target.value)}
                className={INPUT}
              />
            </Campo>
            <Campo label="Fecha de elaboración">
              <input
                type="date"
                required
                value={fechaElaboracion}
                onChange={(e) => setFechaElaboracion(e.target.value)}
                className={INPUT}
              />
            </Campo>
            <Campo label="Duración (días)">
              <input
                type="number"
                min={1}
                value={duracionDias}
                onChange={(e) => setDuracionDias(e.target.value)}
                className={INPUT}
              />
            </Campo>
            <Campo label="Estado">
              <select value={estado} onChange={(e) => setEstado(e.target.value as EstadoDeclaracion)} className={INPUT}>
                {ESTADOS.map((e) => (
                  <option key={e.valor} value={e.valor}>
                    {e.etiqueta}
                  </option>
                ))}
              </select>
            </Campo>
          </div>
          <div className="mt-4">
            <Campo label="Describa el trabajo a realizar">
              <textarea
                required
                value={descripcionTrabajo}
                onChange={(e) => setDescripcionTrabajo(e.target.value)}
                className={TEXTAREA}
              />
            </Campo>
          </div>
          <div className="mt-4">
            <Campo label="Observaciones">
              <textarea value={observaciones} onChange={(e) => setObservaciones(e.target.value)} className={TEXTAREA} />
            </Campo>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-corp-navy">
              Secuencia de actividades y evaluación de riesgo (Kinney: R = P × F × I)
            </h3>
          </div>

          <div className="mt-4 space-y-4">
            {actividades.map((actividad, indice) => {
              const riesgoSin = actividad.probabilidad_sin * actividad.frecuencia_sin * actividad.impacto_sin;
              const riesgoCon = actividad.probabilidad_con * actividad.frecuencia_con * actividad.impacto_con;
              const nivelSin = nivelRiesgo(riesgoSin);
              const nivelCon = nivelRiesgo(riesgoCon);
              return (
                <div key={actividad.clave} className="rounded-2xl border border-corp-border bg-white p-5">
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-sm font-semibold text-corp-navy">Actividad {indice + 1}</span>
                    {actividades.length > 1 && (
                      <button
                        type="button"
                        onClick={() => quitarActividad(indice)}
                        className="text-xs font-semibold text-red-700 hover:underline"
                      >
                        Eliminar
                      </button>
                    )}
                  </div>

                  <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Campo label="Secuencia de la actividad">
                      <textarea
                        value={actividad.secuencia}
                        onChange={(e) => actualizarActividad(indice, { secuencia: e.target.value })}
                        className={TEXTAREA}
                      />
                    </Campo>
                    <Campo label="Técnicas / herramientas / equipos">
                      <textarea
                        value={actividad.tecnicas_herramientas}
                        onChange={(e) => actualizarActividad(indice, { tecnicas_herramientas: e.target.value })}
                        className={TEXTAREA}
                      />
                    </Campo>
                  </div>

                  <div className="mt-4">
                    <Campo label="Descripción del riesgo">
                      <textarea
                        value={actividad.descripcion_riesgo}
                        onChange={(e) => actualizarActividad(indice, { descripcion_riesgo: e.target.value })}
                        className={TEXTAREA}
                      />
                    </Campo>
                  </div>

                  <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="rounded-xl border border-corp-border p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-corp-muted">
                        Evaluación SIN mitigación
                      </p>
                      <div className="mt-2 grid grid-cols-1 gap-2">
                        <SelectorKinney
                          label="Probabilidad"
                          opciones={PROBABILIDADES}
                          valor={actividad.probabilidad_sin}
                          onChange={(v) => actualizarActividad(indice, { probabilidad_sin: v })}
                        />
                        <SelectorKinney
                          label="Frecuencia"
                          opciones={FRECUENCIAS}
                          valor={actividad.frecuencia_sin}
                          onChange={(v) => actualizarActividad(indice, { frecuencia_sin: v })}
                        />
                        <SelectorKinney
                          label="Impacto"
                          opciones={IMPACTOS}
                          valor={actividad.impacto_sin}
                          onChange={(v) => actualizarActividad(indice, { impacto_sin: v })}
                        />
                      </div>
                      <p className="mt-3 text-sm">
                        Riesgo:{" "}
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${nivelSin.color}`}>
                          {riesgoSin} — {nivelSin.etiqueta}
                        </span>
                      </p>
                    </div>

                    <div className="rounded-xl border border-corp-border p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-corp-muted">
                        Evaluación CON mitigación
                      </p>
                      <div className="mt-2 grid grid-cols-1 gap-2">
                        <SelectorKinney
                          label="Probabilidad"
                          opciones={PROBABILIDADES}
                          valor={actividad.probabilidad_con}
                          onChange={(v) => actualizarActividad(indice, { probabilidad_con: v })}
                        />
                        <SelectorKinney
                          label="Frecuencia"
                          opciones={FRECUENCIAS}
                          valor={actividad.frecuencia_con}
                          onChange={(v) => actualizarActividad(indice, { frecuencia_con: v })}
                        />
                        <SelectorKinney
                          label="Impacto"
                          opciones={IMPACTOS}
                          valor={actividad.impacto_con}
                          onChange={(v) => actualizarActividad(indice, { impacto_con: v })}
                        />
                      </div>
                      <p className="mt-3 text-sm">
                        Riesgo:{" "}
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${nivelCon.color}`}>
                          {riesgoCon} — {nivelCon.etiqueta}
                        </span>
                      </p>
                    </div>
                  </div>

                  <div className="mt-4">
                    <Campo label="Medidas de mitigación">
                      <textarea
                        value={actividad.medidas_mitigacion}
                        onChange={(e) => actualizarActividad(indice, { medidas_mitigacion: e.target.value })}
                        className={TEXTAREA}
                      />
                    </Campo>
                  </div>

                  <div className="mt-4">
                    <span className="text-sm font-medium text-corp-navy">
                      Permisos de trabajo / certificados requeridos
                    </span>
                    <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                      {catalogos.permisos_trabajo.map((permiso) => (
                        <label key={permiso} className="flex items-center gap-2 text-sm text-corp-navy">
                          <input
                            type="checkbox"
                            checked={actividad.permisos_requeridos.includes(permiso)}
                            onChange={(e) => alternarPermiso(indice, permiso, e.target.checked)}
                            className="h-4 w-4 rounded border-corp-border accent-corp-blue"
                          />
                          {permiso}
                        </label>
                      ))}
                    </div>
                  </div>

                  <label className="mt-4 flex items-center gap-2 text-sm text-corp-navy">
                    <input
                      type="checkbox"
                      checked={actividad.tarea_sif}
                      onChange={(e) => actualizarActividad(indice, { tarea_sif: e.target.checked })}
                      className="h-4 w-4 rounded border-corp-border accent-corp-blue"
                    />
                    Tarea SIF (con potencial de lesión seria o fatal)
                  </label>
                </div>
              );
            })}
          </div>

          <button
            type="button"
            onClick={agregarActividad}
            className="mt-4 rounded-lg border border-dashed border-corp-blue px-4 py-2 text-sm font-semibold text-corp-blue hover:bg-corp-blue-light"
          >
            + Agregar actividad
          </button>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {mensaje && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            {mensaje}
          </div>
        )}

        <div className="flex justify-end gap-3">
          <button
            type="submit"
            disabled={enviando}
            className="rounded-lg bg-corp-blue px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:opacity-60"
          >
            {enviando ? "Guardando…" : declaracion ? "Guardar cambios" : "Crear declaración"}
          </button>
        </div>
      </form>

      {declaracion && (
        <PanelFirmas key={declaracion.id} token={token} declaracion={declaracion} rolesFirma={catalogos.roles_firma} />
      )}
    </div>
  );
}

function SelectorKinney({
  label,
  opciones,
  valor,
  onChange,
}: {
  label: string;
  opciones: { valor: number; etiqueta: string }[];
  valor: number;
  onChange: (valor: number) => void;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium text-corp-muted">{label}</span>
      <select
        value={valor}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded-lg border border-corp-border px-2 py-1.5 text-xs outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
      >
        {opciones.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.etiqueta}
          </option>
        ))}
      </select>
    </label>
  );
}

function PanelFirmas({
  token,
  declaracion,
  rolesFirma,
}: {
  token: string;
  declaracion: DeclaracionMetodo;
  rolesFirma: { clave: string; etiqueta: string }[];
}) {
  const [firmas, setFirmas] = useState<FirmaMetodo[]>(declaracion.firmas);
  const [rol, setRol] = useState<RolFirma>((rolesFirma[0]?.clave as RolFirma) ?? "supervisor_contratista");
  const [nombreFirmante, setNombreFirmante] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function firmar(event: FormEvent) {
    event.preventDefault();
    if (!nombreFirmante.trim()) return;
    setError(null);
    setEnviando(true);
    try {
      const firma = await firmarDeclaracion(token, declaracion.id, { rol, nombre_firmante: nombreFirmante });
      setFirmas((actual) => [...actual.filter((f) => f.rol !== firma.rol), firma]);
      setNombreFirmante("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar la firma.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mt-6 rounded-2xl border border-corp-border bg-white p-5">
      <h3 className="text-base font-semibold text-corp-navy">Firmas</h3>

      {firmas.length > 0 && (
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {firmas.map((f) => (
            <div key={f.id} className="rounded-lg border border-corp-border px-3 py-2 text-sm">
              <p className="font-medium text-corp-navy">{f.rol_display}</p>
              <p className="text-corp-muted">
                {f.nombre_firmante} · {new Date(f.firmado_en).toLocaleString("es-CO")}
              </p>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={firmar} className="mt-4 flex flex-wrap items-end gap-3">
        <label className="space-y-1.5">
          <span className="text-sm font-medium text-corp-navy">Rol</span>
          <select value={rol} onChange={(e) => setRol(e.target.value as RolFirma)} className={INPUT}>
            {rolesFirma.map((r) => (
              <option key={r.clave} value={r.clave}>
                {r.etiqueta}
              </option>
            ))}
          </select>
        </label>
        <label className="flex-1 space-y-1.5">
          <span className="text-sm font-medium text-corp-navy">Nombre de quien firma</span>
          <input
            value={nombreFirmante}
            onChange={(e) => setNombreFirmante(e.target.value)}
            className={INPUT}
            placeholder="Nombre completo"
          />
        </label>
        <button
          type="submit"
          disabled={enviando}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:opacity-60"
        >
          {enviando ? "Firmando…" : "Firmar"}
        </button>
      </form>

      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
    </div>
  );
}

function Campo({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-corp-navy">{label}</span>
      {children}
    </label>
  );
}
