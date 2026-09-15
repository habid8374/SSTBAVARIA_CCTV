"use client";

import { useEffect, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";

import { useDialog } from "@/components/DialogProvider";
import {
  ApiError,
  actualizarAutorizacionIngreso,
  crearAutorizacionIngreso,
  descargarAutorizacionIngresoPdf,
  eliminarAutorizacionIngreso,
  listarAutorizacionesIngreso,
  listarContratistas,
  listarTrabajadores,
  type AutorizacionIngreso,
  type EmpresaContratista,
  type EstadoDeclaracion,
  type NuevaAutorizacionIngreso,
  type NuevoTrabajadorAutorizacionIngreso,
  type Rol,
  type Trabajador,
} from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20";
const TEXTAREA = `${INPUT} min-h-[70px] resize-y`;

const ESTADOS: { valor: EstadoDeclaracion; etiqueta: string }[] = [
  { valor: "borrador", etiqueta: "Borrador" },
  { valor: "enviada", etiqueta: "Enviada" },
  { valor: "aprobada", etiqueta: "Aprobada" },
  { valor: "rechazada", etiqueta: "Rechazada" },
];

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

function VigenciaBadge({ autorizacion }: { autorizacion: AutorizacionIngreso }) {
  return autorizacion.vigente ? (
    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">Vigente</span>
  ) : (
    <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-semibold text-zinc-600">Fuera de vigencia</span>
  );
}

export default function AutorizacionIngresoView({ token, rol }: { token: string; rol: Rol | null }) {
  const esInterno = rol !== "contratista";
  const [autorizaciones, setAutorizaciones] = useState<AutorizacionIngreso[] | null>(null);
  const [contratistas, setContratistas] = useState<EmpresaContratista[] | null>(null);
  const [seleccionada, setSeleccionada] = useState<AutorizacionIngreso | "nueva" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { confirmar } = useDialog();

  function cargarAutorizaciones() {
    listarAutorizacionesIngreso(token)
      .then(setAutorizaciones)
      .catch(() => setError("No se pudo cargar la lista de autorizaciones de ingreso."));
  }

  useEffect(cargarAutorizaciones, [token]);
  useEffect(() => {
    listarContratistas(token)
      .then(setContratistas)
      .catch(() => {});
  }, [token]);

  async function eliminar(autorizacion: AutorizacionIngreso, event: MouseEvent) {
    event.stopPropagation();
    const ok = await confirmar({
      titulo: "Eliminar autorización de ingreso",
      mensaje: `¿Eliminar la autorización de "${autorizacion.contratista_nombre}" (${autorizacion.fecha_inicio} a ${autorizacion.fecha_fin})?`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
    try {
      await eliminarAutorizacionIngreso(token, autorizacion.id);
      cargarAutorizaciones();
    } catch {
      setError("No se pudo eliminar la autorización.");
    }
  }

  if (seleccionada) {
    return (
      <FormularioAutorizacion
        token={token}
        autorizacionInicial={seleccionada === "nueva" ? null : seleccionada}
        contratistas={contratistas ?? []}
        esInterno={esInterno}
        onVolver={() => {
          setSeleccionada(null);
          cargarAutorizaciones();
        }}
      />
    );
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Autorización de ingreso de personal contratista a la planta — vigencia, horario, área de trabajo,
          responsable SISO del grupo y la lista de trabajadores incluidos o excluidos del ingreso.
        </p>
        {esInterno && (
          <button
            type="button"
            onClick={() => setSeleccionada("nueva")}
            disabled={!contratistas?.length}
            title={!contratistas?.length ? "Registra primero una empresa contratista en “Contratistas”" : undefined}
            className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:cursor-not-allowed disabled:opacity-50"
          >
            + Nueva autorización de ingreso
          </button>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {autorizaciones?.length === 0 && (
        <p className="mt-6 text-sm text-corp-muted">
          Todavía no hay autorizaciones de ingreso registradas — usa el botón de arriba.
        </p>
      )}

      {autorizaciones && autorizaciones.length > 0 && (
        <div className="mt-6 overflow-x-auto rounded-xl border border-corp-border bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-corp-muted">
              <tr>
                <th className="px-4 py-2.5">Contratista</th>
                <th className="px-4 py-2.5">Área de trabajo</th>
                <th className="px-4 py-2.5">Vigencia</th>
                <th className="px-4 py-2.5">Responsable SISO</th>
                <th className="px-4 py-2.5">Trabajadores</th>
                <th className="px-4 py-2.5">Estado</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-corp-border">
              {autorizaciones.map((a) => {
                const incluidos = a.trabajadores.filter((t) => t.incluido).length;
                const excluidos = a.trabajadores.length - incluidos;
                return (
                  <tr key={a.id} onClick={() => setSeleccionada(a)} className="cursor-pointer hover:bg-corp-blue-light/40">
                    <td className="px-4 py-2.5 font-medium text-corp-navy">{a.contratista_nombre}</td>
                    <td className="px-4 py-2.5">{a.area_trabajo}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <span>
                          {a.fecha_inicio} a {a.fecha_fin}
                        </span>
                        <VigenciaBadge autorizacion={a} />
                      </div>
                    </td>
                    <td className="px-4 py-2.5">{a.responsable_siso_nombre || "—"}</td>
                    <td className="px-4 py-2.5">
                      {incluidos} incluido{incluidos === 1 ? "" : "s"}
                      {excluidos > 0 && <span className="text-red-600"> · {excluidos} excluido{excluidos === 1 ? "" : "s"}</span>}
                    </td>
                    <td className="px-4 py-2.5">
                      <EstadoBadge estado={a.estado} />
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {rol === "administrador" && (
                        <button
                          type="button"
                          onClick={(e) => eliminar(a, e)}
                          className="text-xs font-medium text-red-600 hover:underline"
                        >
                          Eliminar
                        </button>
                      )}
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

type TrabajadorLinea = NuevoTrabajadorAutorizacionIngreso & { clave: string };

function clave() {
  return Math.random().toString(36).slice(2);
}

function FormularioAutorizacion({
  token,
  autorizacionInicial,
  contratistas,
  esInterno,
  onVolver,
}: {
  token: string;
  autorizacionInicial: AutorizacionIngreso | null;
  contratistas: EmpresaContratista[];
  esInterno: boolean;
  onVolver: () => void;
}) {
  const [autorizacion, setAutorizacion] = useState<AutorizacionIngreso | null>(autorizacionInicial);
  const [contratistaId, setContratistaId] = useState(
    String(autorizacionInicial?.contratista ?? contratistas[0]?.id ?? "")
  );
  const [fechaInicio, setFechaInicio] = useState(
    autorizacionInicial?.fecha_inicio ?? new Date().toISOString().slice(0, 10)
  );
  const [fechaFin, setFechaFin] = useState(autorizacionInicial?.fecha_fin ?? new Date().toISOString().slice(0, 10));
  const [horaInicio, setHoraInicio] = useState(autorizacionInicial?.hora_inicio ?? "");
  const [horaFin, setHoraFin] = useState(autorizacionInicial?.hora_fin ?? "");
  const [areaTrabajo, setAreaTrabajo] = useState(autorizacionInicial?.area_trabajo ?? "");
  const [sitioEmergencia, setSitioEmergencia] = useState(autorizacionInicial?.sitio_encuentro_emergencia ?? "");
  const [responsableNombre, setResponsableNombre] = useState(autorizacionInicial?.responsable_siso_nombre ?? "");
  const [responsableCargo, setResponsableCargo] = useState(autorizacionInicial?.responsable_siso_cargo ?? "");
  const [responsableTelefono, setResponsableTelefono] = useState(
    autorizacionInicial?.responsable_siso_telefono ?? ""
  );
  const [estado, setEstado] = useState<EstadoDeclaracion>(autorizacionInicial?.estado ?? "borrador");
  const [observaciones, setObservaciones] = useState(autorizacionInicial?.observaciones ?? "");
  const [trabajadoresContratista, setTrabajadoresContratista] = useState<Trabajador[]>([]);
  const [lineas, setLineas] = useState<TrabajadorLinea[]>(
    autorizacionInicial?.trabajadores.map((t) => ({ ...t, clave: clave() })) ?? []
  );
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [descargandoPdf, setDescargandoPdf] = useState(false);

  async function descargarPdf() {
    if (!autorizacion) return;
    setDescargandoPdf(true);
    try {
      await descargarAutorizacionIngresoPdf(token, autorizacion.id);
    } catch {
      setError("No se pudo descargar el PDF.");
    } finally {
      setDescargandoPdf(false);
    }
  }

  useEffect(() => {
    if (!contratistaId) return;
    listarTrabajadores(token, Number(contratistaId))
      .then(setTrabajadoresContratista)
      .catch(() => setTrabajadoresContratista([]));
  }, [token, contratistaId]);

  function alternarTrabajador(trabajador: Trabajador, marcado: boolean) {
    if (marcado) {
      setLineas((actual) => [...actual, { clave: clave(), trabajador: trabajador.id, incluido: true, motivo_exclusion: "" }]);
    } else {
      setLineas((actual) => actual.filter((l) => l.trabajador !== trabajador.id));
    }
  }

  function actualizarLinea(indice: number, cambios: Partial<TrabajadorLinea>) {
    setLineas((actual) => actual.map((l, i) => (i === indice ? { ...l, ...cambios } : l)));
  }

  function nombreTrabajador(trabajadorId: number) {
    const t = trabajadoresContratista.find((tr) => tr.id === trabajadorId);
    return t ? `${t.nombres} ${t.apellidos}` : `Trabajador #${trabajadorId}`;
  }

  async function guardar(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMensaje(null);
    setEnviando(true);
    const payload: NuevaAutorizacionIngreso = {
      contratista: Number(contratistaId),
      fecha_inicio: fechaInicio,
      fecha_fin: fechaFin,
      hora_inicio: horaInicio || null,
      hora_fin: horaFin || null,
      area_trabajo: areaTrabajo,
      sitio_encuentro_emergencia: sitioEmergencia,
      responsable_siso_nombre: responsableNombre,
      responsable_siso_cargo: responsableCargo,
      responsable_siso_telefono: responsableTelefono,
      estado,
      observaciones,
      trabajadores: lineas.map((l) => ({
        trabajador: l.trabajador,
        incluido: l.incluido,
        motivo_exclusion: l.motivo_exclusion,
      })),
    };
    try {
      const guardada = autorizacion
        ? await actualizarAutorizacionIngreso(token, autorizacion.id, payload)
        : await crearAutorizacionIngreso(token, payload);
      setAutorizacion(guardada);
      setLineas(guardada.trabajadores.map((t) => ({ ...t, clave: clave() })));
      setMensaje("Autorización de ingreso guardada.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la autorización de ingreso.");
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
        {autorizacion && (
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

      <form onSubmit={guardar} className="mt-4">
        <fieldset disabled={!esInterno} className="space-y-6">
        <div className="rounded-2xl border border-corp-border bg-white p-5">
          <h3 className="text-base font-semibold text-corp-navy">Datos generales</h3>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Campo label="Empresa contratista">
              <select required value={contratistaId} onChange={(e) => setContratistaId(e.target.value)} className={INPUT}>
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
            <Campo label="Área de trabajo">
              <input required value={areaTrabajo} onChange={(e) => setAreaTrabajo(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Vigencia — desde">
              <input type="date" required value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Vigencia — hasta">
              <input type="date" required value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Horario — desde">
              <input type="time" value={horaInicio} onChange={(e) => setHoraInicio(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Horario — hasta">
              <input type="time" value={horaFin} onChange={(e) => setHoraFin(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Sitio de encuentro en caso de emergencia">
              <input value={sitioEmergencia} onChange={(e) => setSitioEmergencia(e.target.value)} className={INPUT} />
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
            <Campo label="Responsable SISO del grupo — nombre">
              <input required value={responsableNombre} onChange={(e) => setResponsableNombre(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Responsable SISO del grupo — cargo">
              <input value={responsableCargo} onChange={(e) => setResponsableCargo(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Responsable SISO del grupo — teléfono">
              <input value={responsableTelefono} onChange={(e) => setResponsableTelefono(e.target.value)} className={INPUT} />
            </Campo>
          </div>
          <div className="mt-4">
            <Campo label="Observaciones">
              <textarea value={observaciones} onChange={(e) => setObservaciones(e.target.value)} className={TEXTAREA} />
            </Campo>
          </div>
        </div>

        <div className="rounded-2xl border border-corp-border bg-white p-5">
          <h3 className="text-base font-semibold text-corp-navy">Inclusiones / exclusiones</h3>
          <p className="mt-1 text-sm text-corp-muted">
            Marca cada trabajador del contratista que queda autorizado a ingresar. Si desmarcas uno que ya estaba en
            la lista, o lo dejas sin marcar, hay que indicar el motivo por el que queda excluido.
          </p>
          {trabajadoresContratista.length === 0 && (
            <p className="mt-3 text-sm text-corp-muted">
              Esta empresa contratista todavía no tiene trabajadores registrados.
            </p>
          )}
          <div className="mt-3 space-y-2">
            {trabajadoresContratista.map((t) => {
              const indice = lineas.findIndex((l) => l.trabajador === t.id);
              const linea = indice >= 0 ? lineas[indice] : null;
              return (
                <div key={t.id} className="rounded-lg border border-corp-border px-3 py-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={!!linea?.incluido}
                      onChange={(e) =>
                        linea
                          ? actualizarLinea(indice, { incluido: e.target.checked, motivo_exclusion: e.target.checked ? "" : linea.motivo_exclusion })
                          : alternarTrabajador(t, true)
                      }
                      className="h-4 w-4 rounded border-corp-border accent-corp-blue"
                    />
                    <span className="font-medium text-corp-navy">
                      {t.nombres} {t.apellidos}
                    </span>
                    <span className="text-xs text-corp-muted">({t.documento})</span>
                  </label>
                  {linea && !linea.incluido && (
                    <div className="mt-2 pl-6">
                      <input
                        required
                        placeholder="Motivo de la exclusión"
                        value={linea.motivo_exclusion}
                        onChange={(e) => actualizarLinea(indice, { motivo_exclusion: e.target.value })}
                        className={INPUT}
                      />
                    </div>
                  )}
                  {linea && (
                    <button
                      type="button"
                      onClick={() => alternarTrabajador(t, false)}
                      className="mt-2 pl-6 text-xs text-red-600 hover:underline"
                    >
                      Quitar de la lista
                    </button>
                  )}
                </div>
              );
            })}
            {lineas
              .filter((l) => !trabajadoresContratista.some((t) => t.id === l.trabajador))
              .map((linea) => {
                const indice = lineas.indexOf(linea);
                return (
                  <div key={linea.clave} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm">
                    <p className="font-medium text-corp-navy">{nombreTrabajador(linea.trabajador)}</p>
                    <label className="mt-1 flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={linea.incluido}
                        onChange={(e) => actualizarLinea(indice, { incluido: e.target.checked })}
                        className="h-4 w-4 rounded border-corp-border accent-corp-blue"
                      />
                      Incluido
                    </label>
                    {!linea.incluido && (
                      <input
                        required
                        placeholder="Motivo de la exclusión"
                        value={linea.motivo_exclusion}
                        onChange={(e) => actualizarLinea(indice, { motivo_exclusion: e.target.value })}
                        className={`${INPUT} mt-2`}
                      />
                    )}
                  </div>
                );
              })}
          </div>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {mensaje && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
            {mensaje}
          </div>
        )}

        {esInterno && (
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={enviando}
              className="rounded-lg bg-corp-blue px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:opacity-60"
            >
              {enviando ? "Guardando…" : "Guardar autorización"}
            </button>
          </div>
        )}
        </fieldset>
      </form>
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
