"use client";

import { Fragment, useEffect, useState } from "react";

import {
  ApiError,
  exportarAuditoriaExcel,
  exportarInicioSesionExcel,
  listarAuditoria,
  listarInicioSesion,
  type RegistroAuditoria,
  type RegistroInicioSesion,
} from "@/lib/api";

const MODELOS: { valor: string; etiqueta: string }[] = [
  { valor: "", etiqueta: "Todos los modelos" },
  { valor: "EmpresaContratista", etiqueta: "Empresas contratistas" },
  { valor: "Trabajador", etiqueta: "Trabajadores" },
  { valor: "RadicacionSeguridadSocial", etiqueta: "Radicaciones de seguridad social" },
  { valor: "DeclaracionMetodo", etiqueta: "Declaraciones de método" },
  { valor: "AutorizacionIngreso", etiqueta: "Autorizaciones de ingreso" },
  { valor: "Funcionario", etiqueta: "Funcionarios firmantes" },
];

const ACCION_ESTILO: Record<string, string> = {
  creado: "bg-emerald-100 text-emerald-800",
  actualizado: "bg-amber-100 text-amber-800",
  eliminado: "bg-red-100 text-red-800",
};

export default function AuditoriaView({ token }: { token: string }) {
  return (
    <div className="space-y-10">
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        Esta sección solo la ve el superusuario — ni siquiera otras cuentas con rol Administrador tienen
        acceso, por tratarse de información sensible (IPs, quién aprobó/rechazó qué).
      </div>
      <SeccionInicioSesion token={token} />
      <SeccionAuditoria token={token} />
    </div>
  );
}

function SeccionInicioSesion({ token }: { token: string }) {
  const [registros, setRegistros] = useState<RegistroInicioSesion[] | null>(null);
  const [resultado, setResultado] = useState<"" | "true" | "false">("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [exportando, setExportando] = useState(false);

  const filtros = {
    exitoso: resultado === "" ? undefined : resultado === "true",
    desde: desde || undefined,
    hasta: hasta || undefined,
  };

  useEffect(() => {
    listarInicioSesion(token, filtros)
      .then((datos) => {
        setRegistros(datos);
        setError(null);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar los inicios de sesión."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, resultado, desde, hasta]);

  async function exportar() {
    setExportando(true);
    try {
      await exportarInicioSesionExcel(token, filtros);
    } catch {
      setError("No se pudo generar el Excel de inicios de sesión.");
    } finally {
      setExportando(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-semibold text-corp-navy">Inicios de sesión</h3>
        <p className="mt-1 text-sm text-corp-muted">
          Quién se conectó al dashboard (o lo intentó sin éxito), cuándo y desde qué IP — incluye los
          intentos fallidos, útil para detectar accesos sospechosos.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="space-y-1.5">
          <span className="block text-sm font-medium text-corp-navy">Resultado</span>
          <select
            value={resultado}
            onChange={(e) => setResultado(e.target.value as "" | "true" | "false")}
            className="rounded-lg border border-corp-border px-3 py-2 text-sm text-corp-navy outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          >
            <option value="">Todos</option>
            <option value="true">Solo exitosos</option>
            <option value="false">Solo fallidos</option>
          </select>
        </label>
        <label className="space-y-1.5">
          <span className="block text-sm font-medium text-corp-navy">Desde</span>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="rounded-lg border border-corp-border px-3 py-2 text-sm text-corp-navy outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
        </label>
        <label className="space-y-1.5">
          <span className="block text-sm font-medium text-corp-navy">Hasta</span>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="rounded-lg border border-corp-border px-3 py-2 text-sm text-corp-navy outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
        </label>
        <button
          type="button"
          onClick={exportar}
          disabled={exportando}
          className="ml-auto rounded-lg border border-corp-border bg-white px-4 py-2 text-sm font-semibold text-corp-navy transition hover:bg-corp-blue-light disabled:opacity-60"
        >
          {exportando ? "Descargando…" : "Exportar a Excel"}
        </button>
      </div>

      {error && <p className="text-sm text-red-700">{error}</p>}

      <div className="overflow-x-auto rounded-xl border border-corp-border bg-white shadow-sm">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-corp-blue-light text-left text-xs font-semibold uppercase tracking-wide text-corp-navy">
            <tr>
              <th className="px-4 py-2">Fecha</th>
              <th className="px-4 py-2">Usuario</th>
              <th className="px-4 py-2">Resultado</th>
              <th className="px-4 py-2">IP</th>
              <th className="px-4 py-2">Navegador/Dispositivo</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-corp-border">
            {registros?.map((r) => (
              <tr key={r.id}>
                <td className="whitespace-nowrap px-4 py-2 text-corp-muted">
                  {new Date(r.fecha).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })}
                </td>
                <td className="px-4 py-2 text-corp-navy">{r.usuario_nombre}</td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                      r.exitoso ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                    }`}
                  >
                    {r.exitoso ? "Exitoso" : "Fallido"}
                  </span>
                </td>
                <td className="whitespace-nowrap px-4 py-2 font-mono text-xs text-corp-muted">{r.ip || "—"}</td>
                <td className="max-w-[280px] truncate px-4 py-2 text-xs text-corp-muted" title={r.user_agent}>
                  {r.user_agent || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {registros?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-corp-muted">No hay inicios de sesión con estos filtros.</p>
        )}
      </div>
    </div>
  );
}

function SeccionAuditoria({ token }: { token: string }) {
  const [registros, setRegistros] = useState<RegistroAuditoria[] | null>(null);
  const [modelo, setModelo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [expandido, setExpandido] = useState<number | null>(null);
  const [exportando, setExportando] = useState(false);

  useEffect(() => {
    listarAuditoria(token, modelo ? { modelo } : undefined)
      .then((datos) => {
        setRegistros(datos);
        setError(null);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar la auditoría."));
  }, [token, modelo]);

  async function exportar() {
    setExportando(true);
    try {
      await exportarAuditoriaExcel(token, modelo ? { modelo } : undefined);
    } catch {
      setError("No se pudo generar el Excel de auditoría.");
    } finally {
      setExportando(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-semibold text-corp-navy">Cambios, aprobaciones y rechazos</h3>
        <p className="mt-1 text-sm text-corp-muted">
          Quién creó, editó o eliminó cada registro crítico (empresas contratistas, trabajadores,
          radicaciones de seguridad social, declaraciones de método y funcionarios firmantes) y qué cambió
          exactamente — incluye aprobar/rechazar, que queda como un cambio de estado. Es de solo lectura —
          nada se puede modificar ni borrar desde acá.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="max-w-xs space-y-1.5">
          <span className="text-sm font-medium text-corp-navy">Filtrar por tipo de registro</span>
          <select
            value={modelo}
            onChange={(e) => setModelo(e.target.value)}
            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm text-corp-navy outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          >
            {MODELOS.map((m) => (
              <option key={m.valor} value={m.valor}>
                {m.etiqueta}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={exportar}
          disabled={exportando}
          className="ml-auto rounded-lg border border-corp-border bg-white px-4 py-2 text-sm font-semibold text-corp-navy transition hover:bg-corp-blue-light disabled:opacity-60"
        >
          {exportando ? "Descargando…" : "Exportar a Excel"}
        </button>
      </div>

      {error && <p className="text-sm text-red-700">{error}</p>}

      <div className="overflow-x-auto rounded-xl border border-corp-border bg-white shadow-sm">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-corp-blue-light text-left text-xs font-semibold uppercase tracking-wide text-corp-navy">
            <tr>
              <th className="px-4 py-2">Fecha</th>
              <th className="px-4 py-2">Acción</th>
              <th className="px-4 py-2">Registro</th>
              <th className="px-4 py-2">Usuario</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-corp-border">
            {registros?.map((r) => (
              <Fragment key={r.id}>
                <tr className="align-top">
                  <td className="whitespace-nowrap px-4 py-2 text-corp-muted">
                    {new Date(r.fecha).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${ACCION_ESTILO[r.accion] ?? ""}`}>
                      {r.accion_display}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-corp-navy">
                    <span className="font-medium">{r.objeto_str || `#${r.objeto_id}`}</span>
                    <span className="ml-2 text-xs text-corp-muted">
                      ({MODELOS.find((m) => m.valor === r.modelo)?.etiqueta ?? r.modelo})
                    </span>
                  </td>
                  <td className="px-4 py-2 text-corp-muted">{r.usuario_nombre || "—"}</td>
                  <td className="px-4 py-2 text-right">
                    {Object.keys(r.cambios ?? {}).length > 0 && (
                      <button
                        type="button"
                        onClick={() => setExpandido(expandido === r.id ? null : r.id)}
                        className="text-corp-blue hover:underline"
                      >
                        {expandido === r.id ? "Ocultar" : "Ver cambios"}
                      </button>
                    )}
                  </td>
                </tr>
                {expandido === r.id && (
                  <tr>
                    <td colSpan={5} className="bg-corp-blue-light/40 px-4 py-3">
                      <ul className="space-y-1 text-xs text-corp-navy">
                        {Object.entries(r.cambios).map(([campo, valores]) => (
                          <li key={campo}>
                            <span className="font-semibold">{campo}:</span>{" "}
                            <span className="text-corp-muted line-through">{String(valores.antes ?? "—")}</span>
                            {" → "}
                            <span>{String(valores.despues ?? "—")}</span>
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
        {registros?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-corp-muted">Todavía no hay registros de auditoría.</p>
        )}
      </div>
    </div>
  );
}
