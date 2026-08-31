"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { useDialog } from "@/components/DialogProvider";
import {
  ApiError,
  actualizarContratista,
  actualizarTrabajador,
  aprobarRadicacion,
  crearContratista,
  crearRadicacion,
  crearTrabajador,
  exportarRadicacionesExcel,
  listarContratistas,
  listarRadicaciones,
  listarTrabajadores,
  obtenerCatalogosContratistas,
  obtenerIndicadoresContratistas,
  rechazarRadicacion,
  type Catalogos,
  type EmpresaContratista,
  type EstadoRadicacion,
  type IndicadoresContratistas,
  type NuevaEmpresaContratista,
  type NuevoTrabajador,
  type RadicacionSeguridadSocial,
  type Rol,
  type TipoVinculacion,
  type Trabajador,
} from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20";

const MESES = [
  "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
  "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
];

export default function ContratistasView({ token, rol }: { token: string; rol: Rol | null }) {
  const esAdmin = rol === "administrador";
  const [contratistas, setContratistas] = useState<EmpresaContratista[] | null>(null);
  const [seleccionada, setSeleccionada] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formulario, setFormulario] = useState<"nueva" | EmpresaContratista | null>(null);
  const [indicadores, setIndicadores] = useState<IndicadoresContratistas | null>(null);
  const [exportando, setExportando] = useState(false);

  function cargar() {
    listarContratistas(token)
      .then((datos) => {
        setContratistas(datos);
        setSeleccionada((actual) => actual ?? datos[0]?.id ?? null);
      })
      .catch(() => setError("No se pudo cargar la lista de empresas contratistas."));
  }

  useEffect(cargar, [token]);
  useEffect(() => {
    obtenerIndicadoresContratistas(token)
      .then(setIndicadores)
      .catch(() => {});
  }, [token]);

  async function exportar() {
    setExportando(true);
    try {
      await exportarRadicacionesExcel(token);
    } catch {
      setError("No se pudo exportar el Excel de radicaciones.");
    } finally {
      setExportando(false);
    }
  }

  const contratista = contratistas?.find((c) => c.id === seleccionada) ?? null;

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Empresas contratistas, su personal y la radicación de seguridad social.
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={exportar}
            disabled={exportando}
            className="rounded-lg border border-corp-border px-4 py-2 text-sm font-semibold text-corp-navy transition hover:border-corp-blue disabled:opacity-60"
          >
            {exportando ? "Exportando…" : "Exportar radicaciones (Excel)"}
          </button>
          <button
            type="button"
            onClick={() => setFormulario("nueva")}
            className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy"
          >
            + Nueva empresa contratista
          </button>
        </div>
      </div>

      {indicadores && (indicadores.radicaciones_vencidas > 0 || indicadores.radicaciones_por_vencer > 0) && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {indicadores.radicaciones_vencidas > 0 && (
            <p>
              ⚠ <strong>{indicadores.radicaciones_vencidas}</strong> radicación
              {indicadores.radicaciones_vencidas === 1 ? "" : "es"} de seguridad social{" "}
              <strong>vencida{indicadores.radicaciones_vencidas === 1 ? "" : "s"}</strong>.
            </p>
          )}
          {indicadores.radicaciones_por_vencer > 0 && (
            <p>
              {indicadores.radicaciones_vencidas > 0 && <br />}
              <strong>{indicadores.radicaciones_por_vencer}</strong> radicación
              {indicadores.radicaciones_por_vencer === 1 ? "" : "es"} por vencer en los próximos 15 días.
            </p>
          )}
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {contratistas?.length === 0 && (
        <p className="mt-6 text-sm text-corp-muted">
          Todavía no hay empresas contratistas registradas — usa el botón de arriba.
        </p>
      )}

      {contratistas && contratistas.length > 0 && (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
          <div className="space-y-2">
            {contratistas.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setSeleccionada(c.id)}
                className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                  c.id === seleccionada
                    ? "border-corp-blue bg-corp-blue-light"
                    : "border-corp-border bg-white hover:border-corp-blue/40"
                }`}
              >
                <p className="text-sm font-semibold text-corp-navy">{c.nombre}</p>
                <p className="mt-0.5 text-xs text-corp-muted">
                  {c.nit || "Sin NIT"} · {c.trabajadores_count} trabajador{c.trabajadores_count === 1 ? "" : "es"}
                </p>
                <p className="mt-1 flex items-center text-xs text-corp-muted">
                  <span
                    className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${c.activa ? "bg-emerald-500" : "bg-zinc-400"}`}
                  />
                  {c.activa ? "Activa" : "Inactiva"}
                </p>
              </button>
            ))}
          </div>

          <div>
            {contratista ? (
              <PanelContratista
                key={contratista.id}
                token={token}
                contratista={contratista}
                esAdmin={esAdmin}
                onEditarContratista={() => setFormulario(contratista)}
                onCambioTrabajadores={cargar}
              />
            ) : (
              <p className="text-sm text-corp-muted">Selecciona una empresa contratista para ver su personal.</p>
            )}
          </div>
        </div>
      )}

      {formulario && (
        <FormularioContratista
          token={token}
          contratista={formulario === "nueva" ? null : formulario}
          onCerrar={() => setFormulario(null)}
          onGuardada={() => {
            setFormulario(null);
            cargar();
          }}
        />
      )}
    </div>
  );
}

function EstadoBadge({ estado }: { estado?: EstadoRadicacion }) {
  if (!estado) {
    return <span className="text-xs text-corp-muted">Sin radicar</span>;
  }
  const estilos: Record<EstadoRadicacion, string> = {
    pendiente: "bg-amber-100 text-amber-800",
    aprobada: "bg-emerald-100 text-emerald-800",
    rechazada: "bg-red-100 text-red-800",
  };
  const etiquetas: Record<EstadoRadicacion, string> = {
    pendiente: "Pendiente",
    aprobada: "Aprobada",
    rechazada: "Rechazada",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${estilos[estado]}`}>{etiquetas[estado]}</span>
  );
}

function VencimientoBadge({ radicacion }: { radicacion: RadicacionSeguridadSocial }) {
  if (!radicacion.fecha_vencimiento) return null;
  if (radicacion.vencida) {
    return <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">Vencida</span>;
  }
  if (radicacion.dias_para_vencer !== null && radicacion.dias_para_vencer <= 15) {
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
        Vence en {radicacion.dias_para_vencer} día{radicacion.dias_para_vencer === 1 ? "" : "s"}
      </span>
    );
  }
  return <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">Vigente</span>;
}

function PanelContratista({
  token,
  contratista,
  esAdmin,
  onEditarContratista,
  onCambioTrabajadores,
}: {
  token: string;
  contratista: EmpresaContratista;
  esAdmin: boolean;
  onEditarContratista: () => void;
  onCambioTrabajadores: () => void;
}) {
  const [trabajadores, setTrabajadores] = useState<Trabajador[] | null>(null);
  const [seleccionado, setSeleccionado] = useState<number | null>(null);
  const [formulario, setFormulario] = useState<"nuevo" | Trabajador | null>(null);
  const [catalogos, setCatalogos] = useState<Catalogos | null>(null);
  const [error, setError] = useState<string | null>(null);

  function cargar() {
    listarTrabajadores(token, contratista.id)
      .then(setTrabajadores)
      .catch(() => setError("No se pudo cargar el personal."));
  }

  useEffect(cargar, [token, contratista.id]);

  useEffect(() => {
    obtenerCatalogosContratistas(token)
      .then(setCatalogos)
      .catch(() => {});
  }, [token]);

  const trabajador = trabajadores?.find((t) => t.id === seleccionado) ?? null;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-corp-border bg-white p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-corp-navy">{contratista.nombre}</h3>
            <p className="mt-1 text-sm text-corp-muted">NIT {contratista.nit || "—"}</p>
            {contratista.responsable_sst_nombre && (
              <p className="mt-1 text-sm text-corp-muted">
                Responsable SST: {contratista.responsable_sst_nombre}
                {contratista.responsable_sst_telefono && ` · ${contratista.responsable_sst_telefono}`}
              </p>
            )}
          </div>
          {esAdmin && (
            <button
              type="button"
              onClick={onEditarContratista}
              className="shrink-0 rounded-lg border border-corp-border px-3 py-1.5 text-xs font-semibold text-corp-navy hover:bg-corp-blue-light"
            >
              Editar
            </button>
          )}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-corp-navy">Trabajadores</h4>
          <button
            type="button"
            onClick={() => setFormulario("nuevo")}
            className="rounded-lg bg-corp-blue px-3 py-1.5 text-xs font-semibold text-white hover:bg-corp-navy"
          >
            + Nuevo trabajador
          </button>
        </div>

        {error && <p className="mt-2 text-sm text-red-700">{error}</p>}

        {trabajadores?.length === 0 && (
          <p className="mt-3 text-sm text-corp-muted">Sin trabajadores registrados.</p>
        )}

        {trabajadores && trabajadores.length > 0 && (
          <div className="mt-3 overflow-x-auto rounded-xl border border-corp-border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-corp-muted">
                <tr>
                  <th className="px-4 py-2.5">Nombre</th>
                  <th className="px-4 py-2.5">Documento</th>
                  <th className="px-4 py-2.5">EPS / ARL / AFP</th>
                  <th className="px-4 py-2.5">Seguridad social</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-corp-border">
                {trabajadores.map((t) => (
                  <tr key={t.id} className={seleccionado === t.id ? "bg-corp-blue-light/60" : undefined}>
                    <td className="px-4 py-2.5 font-medium text-corp-navy">
                      {t.apellidos} {t.nombres}
                    </td>
                    <td className="px-4 py-2.5">{t.documento}</td>
                    <td className="px-4 py-2.5 text-xs text-corp-muted">
                      {t.eps || "—"} / {t.arl || "—"} / {t.afp || "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <EstadoBadge estado={t.ultima_radicacion?.estado} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-right">
                      <button
                        type="button"
                        onClick={() => setSeleccionado(seleccionado === t.id ? null : t.id)}
                        className="mr-3 text-xs font-semibold text-corp-blue hover:underline"
                      >
                        {seleccionado === t.id ? "Ocultar" : "Ver radicaciones"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setFormulario(t)}
                        className="text-xs font-semibold text-corp-blue hover:underline"
                      >
                        Editar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {trabajador && <PanelRadicaciones token={token} trabajador={trabajador} />}

      {formulario && catalogos && (
        <FormularioTrabajador
          token={token}
          contratistaId={contratista.id}
          trabajador={formulario === "nuevo" ? null : formulario}
          catalogos={catalogos}
          onCerrar={() => setFormulario(null)}
          onGuardado={() => {
            setFormulario(null);
            cargar();
            onCambioTrabajadores();
          }}
        />
      )}
    </div>
  );
}

function PanelRadicaciones({ token, trabajador }: { token: string; trabajador: Trabajador }) {
  const [radicaciones, setRadicaciones] = useState<RadicacionSeguridadSocial[] | null>(null);
  const [formulario, setFormulario] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { pedirTexto } = useDialog();

  function cargar() {
    listarRadicaciones(token, { trabajador: trabajador.id })
      .then(setRadicaciones)
      .catch(() => setError("No se pudieron cargar las radicaciones."));
  }

  useEffect(cargar, [token, trabajador.id]);

  async function decidir(id: number, accion: "aprobar" | "rechazar") {
    const observaciones = await pedirTexto({
      titulo: accion === "aprobar" ? "Aprobar radicación" : "Rechazar radicación",
      mensaje: accion === "aprobar" ? "Observaciones (opcional):" : "Motivo del rechazo:",
      placeholder: accion === "aprobar" ? "Sin observaciones" : "Explica por qué se rechaza…",
      textoConfirmar: accion === "aprobar" ? "Aprobar" : "Rechazar",
      opcional: accion === "aprobar",
    });
    if (observaciones === null) return;
    try {
      if (accion === "aprobar") {
        await aprobarRadicacion(token, id, observaciones);
      } else {
        await rechazarRadicacion(token, id, observaciones);
      }
      cargar();
    } catch {
      setError("No se pudo actualizar la radicación.");
    }
  }

  return (
    <div className="rounded-2xl border border-corp-border bg-white p-5">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-corp-navy">
          Seguridad social — {trabajador.apellidos} {trabajador.nombres}
        </h4>
        <button
          type="button"
          onClick={() => setFormulario(true)}
          className="rounded-lg bg-corp-blue px-3 py-1.5 text-xs font-semibold text-white hover:bg-corp-navy"
        >
          + Radicar
        </button>
      </div>

      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}

      {radicaciones?.length === 0 && <p className="mt-3 text-sm text-corp-muted">Sin radicaciones registradas.</p>}

      <div className="mt-3 space-y-2">
        {radicaciones?.map((r) => (
          <div
            key={r.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-corp-border px-3 py-2 text-sm"
          >
            <div>
              <span className="font-medium text-corp-navy">
                {r.mes} {r.anio}
              </span>
              {r.numero_planilla && <span className="ml-2 text-corp-muted">Planilla {r.numero_planilla}</span>}
              {r.fecha_vencimiento && <span className="ml-2 text-corp-muted">Vence {r.fecha_vencimiento}</span>}
              {r.soporte_pago && (
                <a
                  href={r.soporte_pago}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-2 font-medium text-corp-blue hover:underline"
                >
                  Ver soporte
                </a>
              )}
              {r.observaciones && <p className="mt-1 text-xs text-corp-muted">{r.observaciones}</p>}
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <VencimientoBadge radicacion={r} />
              <EstadoBadge estado={r.estado} />
              {r.estado === "pendiente" && (
                <>
                  <button
                    type="button"
                    onClick={() => decidir(r.id, "aprobar")}
                    className="text-xs font-semibold text-emerald-700 hover:underline"
                  >
                    Aprobar
                  </button>
                  <button
                    type="button"
                    onClick={() => decidir(r.id, "rechazar")}
                    className="text-xs font-semibold text-red-700 hover:underline"
                  >
                    Rechazar
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {formulario && (
        <FormularioRadicacion
          token={token}
          trabajadorId={trabajador.id}
          onCerrar={() => setFormulario(false)}
          onGuardada={() => {
            setFormulario(false);
            cargar();
          }}
        />
      )}
    </div>
  );
}

function FormularioContratista({
  token,
  contratista,
  onCerrar,
  onGuardada,
}: {
  token: string;
  contratista: EmpresaContratista | null;
  onCerrar: () => void;
  onGuardada: () => void;
}) {
  const [nombre, setNombre] = useState(contratista?.nombre ?? "");
  const [nit, setNit] = useState(contratista?.nit ?? "");
  const [contactoNombre, setContactoNombre] = useState(contratista?.contacto_nombre ?? "");
  const [contactoTelefono, setContactoTelefono] = useState(contratista?.contacto_telefono ?? "");
  const [contactoCorreo, setContactoCorreo] = useState(contratista?.contacto_correo ?? "");
  const [responsableNombre, setResponsableNombre] = useState(contratista?.responsable_sst_nombre ?? "");
  const [responsableTelefono, setResponsableTelefono] = useState(contratista?.responsable_sst_telefono ?? "");
  const [activa, setActiva] = useState(contratista?.activa ?? true);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    const datos: Partial<NuevaEmpresaContratista> = {
      nombre,
      nit,
      contacto_nombre: contactoNombre,
      contacto_telefono: contactoTelefono,
      contacto_correo: contactoCorreo,
      responsable_sst_nombre: responsableNombre,
      responsable_sst_telefono: responsableTelefono,
      activa,
    };
    try {
      if (contratista) {
        await actualizarContratista(token, contratista.id, datos);
      } else {
        await crearContratista(token, datos);
      }
      onGuardada();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la empresa contratista.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 px-4 py-8">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">
          {contratista ? "Editar empresa contratista" : "Nueva empresa contratista"}
        </h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <Campo label="Nombre">
            <input required value={nombre} onChange={(e) => setNombre(e.target.value)} className={INPUT} />
          </Campo>
          <Campo label="NIT">
            <input value={nit} onChange={(e) => setNit(e.target.value)} className={INPUT} />
          </Campo>
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Contacto — nombre">
              <input value={contactoNombre} onChange={(e) => setContactoNombre(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Contacto — teléfono">
              <input value={contactoTelefono} onChange={(e) => setContactoTelefono(e.target.value)} className={INPUT} />
            </Campo>
          </div>
          <Campo label="Contacto — correo">
            <input
              type="email"
              value={contactoCorreo}
              onChange={(e) => setContactoCorreo(e.target.value)}
              className={INPUT}
            />
          </Campo>
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Responsable SST — nombre">
              <input
                value={responsableNombre}
                onChange={(e) => setResponsableNombre(e.target.value)}
                className={INPUT}
              />
            </Campo>
            <Campo label="Responsable SST — teléfono">
              <input
                value={responsableTelefono}
                onChange={(e) => setResponsableTelefono(e.target.value)}
                className={INPUT}
              />
            </Campo>
          </div>
          {contratista && (
            <label className="flex items-center gap-2 text-sm text-corp-navy">
              <input
                type="checkbox"
                checked={activa}
                onChange={(e) => setActiva(e.target.checked)}
                className="h-4 w-4 rounded border-corp-border accent-corp-blue"
              />
              Activa
            </label>
          )}

          {error && (
            <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onCerrar}
              className="rounded-lg px-4 py-2 text-sm font-medium text-corp-muted hover:bg-zinc-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:opacity-60"
            >
              {enviando ? "Guardando…" : contratista ? "Guardar cambios" : "Crear empresa"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function FormularioTrabajador({
  token,
  contratistaId,
  trabajador,
  catalogos,
  onCerrar,
  onGuardado,
}: {
  token: string;
  contratistaId: number;
  trabajador: Trabajador | null;
  catalogos: Catalogos;
  onCerrar: () => void;
  onGuardado: () => void;
}) {
  const [nombres, setNombres] = useState(trabajador?.nombres ?? "");
  const [apellidos, setApellidos] = useState(trabajador?.apellidos ?? "");
  const [documento, setDocumento] = useState(trabajador?.documento ?? "");
  const [eps, setEps] = useState(trabajador?.eps ?? "");
  const [arl, setArl] = useState(trabajador?.arl ?? "");
  const [afp, setAfp] = useState(trabajador?.afp ?? "");
  const [tipoVinculacion, setTipoVinculacion] = useState<TipoVinculacion>(trabajador?.tipo_vinculacion ?? "fijo");
  const [fechaInicio, setFechaInicio] = useState(trabajador?.fecha_inicio_contrato ?? "");
  const [cursos, setCursos] = useState<Record<string, string | null>>(trabajador?.cursos_safety_academy ?? {});
  const [autorizacionDatos, setAutorizacionDatos] = useState(trabajador?.autorizacion_datos ?? false);
  const [evidenciaAutorizacion, setEvidenciaAutorizacion] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  function alternarCurso(clave: string, marcado: boolean) {
    setCursos((actual) => ({ ...actual, [clave]: marcado ? actual[clave] || new Date().toISOString().slice(0, 10) : null }));
  }

  function fecharCurso(clave: string, fecha: string) {
    setCursos((actual) => ({ ...actual, [clave]: fecha }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    if (!trabajador && !autorizacionDatos) {
      setError("Hace falta la autorización de tratamiento de datos personales para registrar al trabajador.");
      setEnviando(false);
      return;
    }
    const datos: NuevoTrabajador = {
      contratista: contratistaId,
      nombres,
      apellidos,
      documento,
      eps,
      arl,
      afp,
      tipo_vinculacion: tipoVinculacion,
      fecha_inicio_contrato: fechaInicio || null,
      cursos_safety_academy: cursos,
      autorizacion_datos: autorizacionDatos,
    };
    try {
      if (trabajador) {
        await actualizarTrabajador(token, trabajador.id, datos, evidenciaAutorizacion ?? undefined);
      } else {
        await crearTrabajador(token, datos, evidenciaAutorizacion ?? undefined);
      }
      onGuardado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el trabajador.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 px-4 py-8">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">
          {trabajador ? "Editar trabajador" : "Nuevo trabajador"}
        </h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Nombres">
              <input required value={nombres} onChange={(e) => setNombres(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Apellidos">
              <input required value={apellidos} onChange={(e) => setApellidos(e.target.value)} className={INPUT} />
            </Campo>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Documento de identidad">
              <input required value={documento} onChange={(e) => setDocumento(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="Tipo de vinculación">
              <select
                value={tipoVinculacion}
                onChange={(e) => setTipoVinculacion(e.target.value as TipoVinculacion)}
                className={INPUT}
              >
                <option value="fijo">Fijo</option>
                <option value="temporal">Temporal</option>
              </select>
            </Campo>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Campo label="EPS">
              <input value={eps} onChange={(e) => setEps(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="ARL">
              <input value={arl} onChange={(e) => setArl(e.target.value)} className={INPUT} />
            </Campo>
            <Campo label="AFP">
              <input value={afp} onChange={(e) => setAfp(e.target.value)} className={INPUT} />
            </Campo>
          </div>
          <Campo label="Fecha de inicio de contrato">
            <input
              type="date"
              value={fechaInicio ?? ""}
              onChange={(e) => setFechaInicio(e.target.value)}
              className={INPUT}
            />
          </Campo>

          <div>
            <span className="text-sm font-medium text-corp-navy">Cursos Safety Academy</span>
            <div className="mt-2 space-y-2 rounded-lg border border-corp-border p-3">
              {catalogos.cursos_safety_academy.map((curso) => {
                const completado = cursos[curso.clave] != null;
                return (
                  <div key={curso.clave} className="flex flex-wrap items-center gap-2">
                    <label className="flex flex-1 items-center gap-2 text-sm text-corp-navy">
                      <input
                        type="checkbox"
                        checked={completado}
                        onChange={(e) => alternarCurso(curso.clave, e.target.checked)}
                        className="h-4 w-4 rounded border-corp-border accent-corp-blue"
                      />
                      {curso.etiqueta}
                    </label>
                    {completado && (
                      <input
                        type="date"
                        value={cursos[curso.clave] ?? ""}
                        onChange={(e) => fecharCurso(curso.clave, e.target.value)}
                        className="rounded-lg border border-corp-border px-2 py-1 text-xs outline-none focus:border-corp-blue"
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {!trabajador && (
            <label className="flex items-start gap-2 rounded-lg border border-corp-border bg-zinc-50 px-3 py-2.5 text-sm text-corp-navy">
              <input
                type="checkbox"
                required
                checked={autorizacionDatos}
                onChange={(e) => setAutorizacionDatos(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-corp-border accent-corp-blue"
              />
              <span>
                Declaro que cuento con la autorización del trabajador para el tratamiento de sus datos
                personales, incluidos los de afiliación a seguridad social, conforme a la{" "}
                <Link href="/politica-privacidad" target="_blank" className="font-medium text-corp-blue hover:underline">
                  política de tratamiento de datos personales
                </Link>{" "}
                (Ley 1581 de 2012).
              </span>
            </label>
          )}

          <Campo label="Evidencia de la autorización (opcional)">
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={(e) => setEvidenciaAutorizacion(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm text-corp-navy outline-none file:mr-3 file:rounded-md file:border-0 file:bg-corp-blue-light file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-corp-blue"
            />
            {trabajador?.soporte_autorizacion_datos && !evidenciaAutorizacion && (
              <p className="mt-1 text-xs text-corp-muted">
                Ya hay una evidencia guardada —{" "}
                <a
                  href={trabajador.soporte_autorizacion_datos}
                  target="_blank"
                  rel="noreferrer"
                  className="text-corp-blue hover:underline"
                >
                  verla
                </a>
                . Sube un archivo nuevo para reemplazarla.
              </p>
            )}
          </Campo>

          {error && (
            <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onCerrar}
              className="rounded-lg px-4 py-2 text-sm font-medium text-corp-muted hover:bg-zinc-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:opacity-60"
            >
              {enviando ? "Guardando…" : trabajador ? "Guardar cambios" : "Crear trabajador"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function FormularioRadicacion({
  token,
  trabajadorId,
  onCerrar,
  onGuardada,
}: {
  token: string;
  trabajadorId: number;
  onCerrar: () => void;
  onGuardada: () => void;
}) {
  const ahora = new Date();
  const [anio, setAnio] = useState(String(ahora.getFullYear()));
  const [mes, setMes] = useState(MESES[ahora.getMonth()]);
  const [numeroPlanilla, setNumeroPlanilla] = useState("");
  const [fechaVencimiento, setFechaVencimiento] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await crearRadicacion(
        token,
        {
          trabajador: trabajadorId,
          anio: Number(anio),
          mes,
          numero_planilla: numeroPlanilla,
          fecha_vencimiento: fechaVencimiento || undefined,
        },
        archivo ?? undefined
      );
      onGuardada();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo radicar la seguridad social.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 px-4 py-8">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">Radicar seguridad social</h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Mes">
              <select value={mes} onChange={(e) => setMes(e.target.value)} className={INPUT}>
                {MESES.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo label="Año">
              <input
                type="number"
                required
                value={anio}
                onChange={(e) => setAnio(e.target.value)}
                className={INPUT}
              />
            </Campo>
          </div>
          <Campo label="Número de planilla">
            <input
              value={numeroPlanilla}
              onChange={(e) => setNumeroPlanilla(e.target.value)}
              className={INPUT}
            />
          </Campo>
          <Campo label="Fecha de vencimiento">
            <input
              type="date"
              value={fechaVencimiento}
              onChange={(e) => setFechaVencimiento(e.target.value)}
              className={INPUT}
            />
          </Campo>
          <Campo label="Soporte de pago (PDF)">
            <input
              type="file"
              accept="application/pdf,image/*"
              onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
              className="w-full text-sm text-corp-muted file:mr-3 file:rounded-lg file:border-0 file:bg-corp-blue-light file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-corp-navy"
            />
          </Campo>

          {error && (
            <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onCerrar}
              className="rounded-lg px-4 py-2 text-sm font-medium text-corp-muted hover:bg-zinc-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:opacity-60"
            >
              {enviando ? "Radicando…" : "Radicar"}
            </button>
          </div>
        </form>
      </div>
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
