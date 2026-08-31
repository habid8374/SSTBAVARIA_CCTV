"use client";

import { Fragment, useEffect, useState } from "react";

import { ApiError, listarAuditoria, type RegistroAuditoria } from "@/lib/api";

const MODELOS: { valor: string; etiqueta: string }[] = [
  { valor: "", etiqueta: "Todos los modelos" },
  { valor: "EmpresaContratista", etiqueta: "Empresas contratistas" },
  { valor: "Trabajador", etiqueta: "Trabajadores" },
  { valor: "RadicacionSeguridadSocial", etiqueta: "Radicaciones de seguridad social" },
  { valor: "DeclaracionMetodo", etiqueta: "Declaraciones de método" },
  { valor: "Funcionario", etiqueta: "Funcionarios firmantes" },
];

const ACCION_ESTILO: Record<string, string> = {
  creado: "bg-emerald-100 text-emerald-800",
  actualizado: "bg-amber-100 text-amber-800",
  eliminado: "bg-red-100 text-red-800",
};

export default function AuditoriaView({ token }: { token: string }) {
  const [registros, setRegistros] = useState<RegistroAuditoria[] | null>(null);
  const [modelo, setModelo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [expandido, setExpandido] = useState<number | null>(null);

  useEffect(() => {
    listarAuditoria(token, modelo ? { modelo } : undefined)
      .then((datos) => {
        setRegistros(datos);
        setError(null);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar la auditoría."));
  }, [token, modelo]);

  return (
    <div className="space-y-4">
      <p className="text-sm text-corp-muted">
        Quién creó, editó o eliminó cada registro crítico (empresas contratistas, trabajadores, radicaciones de
        seguridad social, declaraciones de método y funcionarios firmantes) y qué cambió exactamente. Es de solo
        lectura — nada se puede modificar ni borrar desde acá.
      </p>
      <label className="block max-w-xs space-y-1.5">
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

      {error && <p className="text-sm text-red-700">{error}</p>}

      <div className="overflow-hidden rounded-xl border border-corp-border bg-white shadow-sm">
        <table className="w-full text-sm">
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
