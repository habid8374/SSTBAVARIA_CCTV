"use client";

import { useEffect, useState } from "react";

import {
  obtenerEventosPorZona,
  obtenerIndicadores,
  type EventoPorZona,
  type Indicadores,
} from "@/lib/api";

export default function TableroView({ token }: { token: string }) {
  const [indicadores, setIndicadores] = useState<Indicadores | null>(null);
  const [eventosPorZona, setEventosPorZona] = useState<EventoPorZona[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([obtenerIndicadores(token), obtenerEventosPorZona(token)])
      .then(([kpis, zonas]) => {
        setIndicadores(kpis);
        setEventosPorZona(zonas);
      })
      .catch(() => setError("No se pudo cargar el tablero del backend."));
  }, [token]);

  return (
    <div>
      <p className="text-sm text-corp-muted">Estado general del sistema de videovigilancia.</p>

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {indicadores && (
        <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Kpi titulo="Cámaras activas" valor={`${indicadores.camaras_activas}/${indicadores.camaras_total}`} />
          <Kpi titulo="Alertas hoy" valor={String(indicadores.alertas_hoy)} />
          <Kpi titulo="Disponibilidad" valor={`${indicadores.disponibilidad}%`} />
          <Kpi titulo="Zonas con actividad" valor={String(eventosPorZona?.length ?? 0)} />
        </div>
      )}

      <div className="mt-8 rounded-xl border border-corp-border bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-corp-navy">Eventos por zona (últimos 7 días)</h2>
        {eventosPorZona && eventosPorZona.length > 0 ? (
          <BarrasEventosPorZona datos={eventosPorZona} />
        ) : eventosPorZona ? (
          <p className="mt-4 text-sm text-corp-muted">Sin eventos registrados en los últimos 7 días.</p>
        ) : null}
      </div>
    </div>
  );
}

function Kpi({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div className="rounded-xl border border-corp-border bg-white p-5 shadow-sm">
      <p className="text-sm text-corp-muted">{titulo}</p>
      <p className="mt-2 text-3xl font-semibold text-corp-navy">{valor}</p>
    </div>
  );
}

function BarrasEventosPorZona({ datos }: { datos: EventoPorZona[] }) {
  const max = Math.max(...datos.map((d) => d.total));

  return (
    <div className="mt-5 space-y-3">
      {datos.map((d) => (
        <div key={`${d.camara}-${d.zona}`} className="flex items-center gap-3">
          <div className="w-40 shrink-0 truncate text-sm text-corp-navy" title={`${d.zona} — ${d.camara}`}>
            {d.zona}
            <span className="text-corp-muted"> — {d.camara}</span>
          </div>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-corp-blue-light">
            <div
              className="h-full rounded-full bg-corp-blue"
              style={{ width: `${Math.max((d.total / max) * 100, 4)}%` }}
            />
          </div>
          <div className="w-6 shrink-0 text-right text-sm font-semibold text-corp-navy">{d.total}</div>
        </div>
      ))}
    </div>
  );
}
