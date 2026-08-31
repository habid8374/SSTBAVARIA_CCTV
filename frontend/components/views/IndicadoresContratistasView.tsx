"use client";

import { useEffect, useState, type ReactNode } from "react";

import { obtenerIndicadoresDashboard, type IndicadoresDashboard } from "@/lib/api";

const COLOR_ESTADO_RADICACION: Record<string, string> = {
  pendiente: "bg-amber-500",
  aprobada: "bg-emerald-500",
  rechazada: "bg-red-500",
};

const ETIQUETA_ESTADO_RADICACION: Record<string, string> = {
  pendiente: "Pendiente",
  aprobada: "Aprobada",
  rechazada: "Rechazada",
};

const COLOR_ESTADO_DECLARACION: Record<string, string> = {
  borrador: "bg-zinc-400",
  enviada: "bg-amber-500",
  aprobada: "bg-emerald-500",
  rechazada: "bg-red-500",
};

const ETIQUETA_ESTADO_DECLARACION: Record<string, string> = {
  borrador: "Borrador",
  enviada: "Enviada",
  aprobada: "Aprobada",
  rechazada: "Rechazada",
};

const COLOR_NIVEL_RIESGO: Record<string, string> = {
  "Riesgo muy alto — detener esta actividad específica": "bg-red-100 text-red-800",
  "Riesgo alto — requiere acción inmediata": "bg-orange-100 text-orange-800",
  "Riesgo considerable — requiere corrección": "bg-amber-100 text-amber-800",
  "Riesgo posible — requiere supervisión/atención": "bg-yellow-100 text-yellow-800",
  "Riesgo bajo — aceptable": "bg-emerald-100 text-emerald-800",
};

export default function IndicadoresContratistasView({ token }: { token: string }) {
  const [datos, setDatos] = useState<IndicadoresDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    obtenerIndicadoresDashboard(token)
      .then(setDatos)
      .catch(() => setError("No se pudo cargar el panel de indicadores."));
  }, [token]);

  return (
    <div>
      <p className="text-sm text-corp-muted">
        Cumplimiento de contratistas, estado de declaraciones y radicaciones, riesgo Kinney y tendencia de
        los últimos meses — se calcula en vivo, sin resúmenes guardados que puedan desactualizarse.
      </p>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {datos && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Kpi titulo="Contratistas activos" valor={String(datos.contratistas_activos)} />
            <Kpi titulo="Trabajadores activos" valor={String(datos.trabajadores_activos)} />
            <Kpi
              titulo="Riesgo Kinney promedio"
              valor={`${datos.riesgo_promedio_sin} → ${datos.riesgo_promedio_con}`}
              nota="sin mitigación → con mitigación"
            />
            <Kpi
              titulo="Tiempo promedio de aprobación"
              valor={
                datos.tiempo_promedio_aprobacion_dias !== null
                  ? `${datos.tiempo_promedio_aprobacion_dias} día(s)`
                  : "—"
              }
              nota="declaraciones aprobadas"
            />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel titulo="Radicaciones de seguridad social por estado">
              <BarrasEstado
                conteos={datos.radicaciones_por_estado}
                colores={COLOR_ESTADO_RADICACION}
                etiquetas={ETIQUETA_ESTADO_RADICACION}
              />
            </Panel>
            <Panel titulo="Declaraciones de método por estado">
              <BarrasEstado
                conteos={datos.declaraciones_por_estado}
                colores={COLOR_ESTADO_DECLARACION}
                etiquetas={ETIQUETA_ESTADO_DECLARACION}
              />
            </Panel>
          </div>

          <div className="mt-6">
            <Panel titulo="Tendencia mensual (últimos 6 meses)">
              <TendenciaMensual datos={datos.tendencia_mensual} />
            </Panel>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel titulo="Cumplimiento por contratista">
              {datos.por_contratista.length === 0 ? (
                <p className="mt-3 text-sm text-corp-muted">No hay contratistas activos todavía.</p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-corp-border text-left text-xs uppercase tracking-wide text-corp-muted">
                        <th className="pb-2 pr-3">Contratista</th>
                        <th className="pb-2 pr-3">Trabajadores</th>
                        <th className="pb-2 pr-3">Radicaciones pend.</th>
                        <th className="pb-2">Declaraciones pend.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {datos.por_contratista.map((c) => (
                        <tr key={c.contratista} className="border-b border-corp-border/60 last:border-0">
                          <td className="py-2 pr-3 text-corp-navy">{c.contratista}</td>
                          <td className="py-2 pr-3">{c.trabajadores}</td>
                          <td className="py-2 pr-3">
                            {c.radicaciones_pendientes > 0 ? (
                              <span className="font-semibold text-amber-700">{c.radicaciones_pendientes}</span>
                            ) : (
                              c.radicaciones_pendientes
                            )}
                          </td>
                          <td className="py-2">
                            {c.declaraciones_pendientes > 0 ? (
                              <span className="font-semibold text-amber-700">{c.declaraciones_pendientes}</span>
                            ) : (
                              c.declaraciones_pendientes
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>

            <Panel titulo="Top 5 riesgos (sin mitigación)">
              {datos.top_riesgos.length === 0 ? (
                <p className="mt-3 text-sm text-corp-muted">No hay actividades con riesgo evaluado todavía.</p>
              ) : (
                <div className="mt-3 space-y-2">
                  {datos.top_riesgos.map((r, i) => (
                    <div key={i} className="rounded-lg border border-corp-border px-3 py-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm text-corp-navy">{r.secuencia || "—"}</p>
                        <span
                          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
                            COLOR_NIVEL_RIESGO[r.nivel_sin] ?? "bg-zinc-100 text-corp-muted"
                          }`}
                        >
                          {r.riesgo_sin}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-corp-muted">
                        {r.contratista} · con mitigación: {r.riesgo_con}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}

function Kpi({ titulo, valor, nota }: { titulo: string; valor: string; nota?: string }) {
  return (
    <div className="rounded-xl border border-corp-border bg-white p-5 shadow-sm">
      <p className="text-sm text-corp-muted">{titulo}</p>
      <p className="mt-2 text-2xl font-semibold text-corp-navy">{valor}</p>
      {nota && <p className="mt-1 text-xs text-corp-muted">{nota}</p>}
    </div>
  );
}

function Panel({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-corp-border bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-corp-navy">{titulo}</h3>
      {children}
    </div>
  );
}

function BarrasEstado({
  conteos,
  colores,
  etiquetas,
}: {
  conteos: Record<string, number>;
  colores: Record<string, string>;
  etiquetas: Record<string, string>;
}) {
  const entradas = Object.entries(conteos);
  const total = entradas.reduce((acc, [, n]) => acc + n, 0);
  const max = Math.max(...entradas.map(([, n]) => n), 1);

  if (total === 0) {
    return <p className="mt-3 text-sm text-corp-muted">Sin registros todavía.</p>;
  }

  return (
    <div className="mt-4 space-y-3">
      {entradas.map(([clave, n]) => (
        <div key={clave} className="flex items-center gap-3">
          <div className="w-28 shrink-0 text-sm text-corp-navy">{etiquetas[clave] ?? clave}</div>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-zinc-100">
            <div
              className={`h-full rounded-full ${colores[clave] ?? "bg-corp-blue"}`}
              style={{ width: `${Math.max((n / max) * 100, n > 0 ? 4 : 0)}%` }}
            />
          </div>
          <div className="w-6 shrink-0 text-right text-sm font-semibold text-corp-navy">{n}</div>
        </div>
      ))}
    </div>
  );
}

function TendenciaMensual({ datos }: { datos: { mes: string; declaraciones: number; radicaciones: number }[] }) {
  const max = Math.max(...datos.flatMap((d) => [d.declaraciones, d.radicaciones]), 1);

  return (
    <div className="mt-4">
      <div className="flex items-center gap-4 text-xs text-corp-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-corp-blue" /> Declaraciones
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Radicaciones
        </span>
      </div>
      <div className="mt-3 flex items-end gap-4">
        {datos.map((d) => (
          <div key={d.mes} className="flex flex-1 flex-col items-center gap-1">
            <div className="flex h-28 items-end gap-1">
              <div
                title={`${d.declaraciones} declaración(es)`}
                className="w-3 rounded-t bg-corp-blue"
                style={{ height: `${Math.max((d.declaraciones / max) * 100, d.declaraciones > 0 ? 6 : 2)}%` }}
              />
              <div
                title={`${d.radicaciones} radicación(es)`}
                className="w-3 rounded-t bg-emerald-500"
                style={{ height: `${Math.max((d.radicaciones / max) * 100, d.radicaciones > 0 ? 6 : 2)}%` }}
              />
            </div>
            <span className="text-xs text-corp-muted">{d.mes}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
