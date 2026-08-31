"use client";

import { useEffect, useState } from "react";

import { actualizarEvento, listarEventos, type EstadoEvento, type EventoDashboard } from "@/lib/api";

type FiltroDisparo = "todas" | "con_alerta" | "sin_alerta";

export default function AlertasView({ token }: { token: string }) {
  const [eventos, setEventos] = useState<EventoDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filtroEstado, setFiltroEstado] = useState<EstadoEvento | "todos">("todos");
  const [filtroDisparo, setFiltroDisparo] = useState<FiltroDisparo>("todas");
  const [eventoAmpliado, setEventoAmpliado] = useState<EventoDashboard | null>(null);

  function cargar() {
    listarEventos(token, {
      estado: filtroEstado === "todos" ? undefined : filtroEstado,
      disparo_alerta: filtroDisparo === "todas" ? undefined : filtroDisparo === "con_alerta",
    })
      .then(setEventos)
      .catch(() => setError("No se pudo cargar la bandeja de alertas."));
  }

  useEffect(cargar, [token, filtroEstado, filtroDisparo]);

  async function alternarEstado(evento: EventoDashboard) {
    const nuevoEstado: EstadoEvento = evento.estado === "nuevo" ? "revisado" : "nuevo";
    try {
      await actualizarEvento(token, evento.id, nuevoEstado);
      cargar();
    } catch {
      setError("No se pudo actualizar el estado del evento.");
    }
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">Eventos detectados por las cámaras, con evidencia.</p>
        <div className="flex flex-wrap gap-2">
          <select
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value as EstadoEvento | "todos")}
            className="rounded-md border border-corp-border px-2 py-1.5 text-sm"
          >
            <option value="todos">Todos los estados</option>
            <option value="nuevo">Nuevos</option>
            <option value="revisado">Revisados</option>
          </select>
          <select
            value={filtroDisparo}
            onChange={(e) => setFiltroDisparo(e.target.value as FiltroDisparo)}
            className="rounded-md border border-corp-border px-2 py-1.5 text-sm"
          >
            <option value="todas">Con y sin alerta</option>
            <option value="con_alerta">Solo con alerta</option>
            <option value="sin_alerta">Solo sin alerta</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-6 overflow-x-auto rounded-xl border border-corp-border bg-white">
        <table className="w-full min-w-[680px] text-left text-sm">
          <thead className="border-b border-corp-border bg-corp-blue-light text-xs uppercase text-corp-muted">
            <tr>
              <th className="px-4 py-3">Foto</th>
              <th className="px-4 py-3">Cámara</th>
              <th className="px-4 py-3">Zona</th>
              <th className="px-4 py-3">Fecha</th>
              <th className="px-4 py-3">Alerta</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {eventos?.map((evento) => (
              <tr key={evento.id} className="border-b border-corp-border last:border-0">
                <td className="px-4 py-3">
                  {evento.snapshot ? (
                    <button type="button" onClick={() => setEventoAmpliado(evento)}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={evento.snapshot}
                        alt={`Snapshot de ${evento.camara_nombre}`}
                        className="h-12 w-16 rounded-md object-cover ring-1 ring-corp-border"
                      />
                    </button>
                  ) : (
                    <div className="flex h-12 w-16 items-center justify-center rounded-md bg-zinc-100 text-[10px] text-corp-muted">
                      Sin foto
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 font-medium text-corp-navy">{evento.camara_nombre}</td>
                <td className="px-4 py-3 text-corp-muted">{evento.zona_nombre ?? "—"}</td>
                <td className="px-4 py-3 text-corp-muted">
                  {new Date(evento.timestamp).toLocaleString("es-CO")}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      evento.disparo_alerta ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
                    }`}
                  >
                    {evento.disparo_alerta ? "Alerta" : "Normal"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      evento.estado === "nuevo" ? "bg-amber-100 text-amber-700" : "bg-zinc-100 text-zinc-500"
                    }`}
                  >
                    {evento.estado === "nuevo" ? "Nuevo" : "Revisado"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => alternarEstado(evento)}
                    className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy transition hover:border-corp-blue"
                  >
                    {evento.estado === "nuevo" ? "Marcar revisado" : "Marcar nuevo"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {eventos?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-corp-muted">
            {filtroEstado === "todos" && filtroDisparo === "todas"
              ? "Todavía no ha llegado ningún evento — aparecen aquí automáticamente en cuanto una cámara reporte movimiento."
              : "No hay eventos con estos filtros."}
          </p>
        )}
      </div>

      {eventoAmpliado?.snapshot && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
          onClick={() => setEventoAmpliado(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={eventoAmpliado.snapshot}
            alt={`Snapshot de ${eventoAmpliado.camara_nombre}`}
            className="max-h-[85vh] max-w-full rounded-lg shadow-2xl"
          />
        </div>
      )}
    </div>
  );
}
