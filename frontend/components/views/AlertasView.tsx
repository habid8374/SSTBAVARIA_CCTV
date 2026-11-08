"use client";

import { useEffect, useMemo, useState } from "react";

import { actualizarEvento, listarEventos, type EstadoEvento, type EventoDashboard } from "@/lib/api";

type FiltroDisparo = "todas" | "con_alerta" | "sin_alerta";

// --- Agrupación por día -----------------------------------------------------

function claveDia(ts: string): string {
  const d = new Date(ts);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function mismaFecha(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function etiquetaDia(ts: string): string {
  const d = new Date(ts);
  const hoy = new Date();
  const ayer = new Date();
  ayer.setDate(hoy.getDate() - 1);
  if (mismaFecha(d, hoy)) return "Hoy";
  if (mismaFecha(d, ayer)) return "Ayer";
  const texto = d.toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function hora(ts: string): string {
  return new Date(ts).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
}

type GrupoDia = { clave: string; etiqueta: string; eventos: EventoDashboard[] };

function agruparPorDia(eventos: EventoDashboard[]): GrupoDia[] {
  const grupos: GrupoDia[] = [];
  const indice = new Map<string, number>();
  for (const ev of eventos) {
    const clave = claveDia(ev.timestamp);
    if (!indice.has(clave)) {
      indice.set(clave, grupos.length);
      grupos.push({ clave, etiqueta: etiquetaDia(ev.timestamp), eventos: [] });
    }
    grupos[indice.get(clave)!].eventos.push(ev);
  }
  return grupos;
}

function esConfirmada(evento: EventoDashboard): boolean {
  return evento.tipos_ia.length > 0 || evento.disparo_alerta;
}

// --- Vista ------------------------------------------------------------------

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

  const grupos = useMemo(() => (eventos ? agruparPorDia(eventos) : []), [eventos]);

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
        <p className="text-sm text-corp-muted">Eventos detectados por las cámaras, agrupados por día.</p>
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
            <option value="con_alerta">Solo alertas</option>
            <option value="sin_alerta">Solo sin novedad</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {eventos && eventos.length === 0 && (
        <div className="mt-6 rounded-xl border border-corp-border bg-white px-4 py-10 text-center text-sm text-corp-muted">
          {filtroEstado === "todos" && filtroDisparo === "todas"
            ? "Todavía no ha llegado ningún evento — aparecen aquí automáticamente en cuanto una cámara reporte movimiento."
            : "No hay eventos con estos filtros."}
        </div>
      )}

      <div className="mt-6 space-y-8">
        {grupos.map((grupo) => {
          const confirmadas = grupo.eventos.filter(esConfirmada).length;
          return (
            <section key={grupo.clave}>
              {/* Encabezado del día */}
              <div className="sticky top-0 z-10 -mx-1 flex items-center justify-between border-b border-corp-border bg-background/90 px-1 py-2 backdrop-blur">
                <h3 className="text-base font-semibold text-corp-navy">{grupo.etiqueta}</h3>
                <div className="flex items-center gap-2 text-xs">
                  {confirmadas > 0 && (
                    <span className="rounded-full bg-red-100 px-2.5 py-1 font-semibold text-red-700">
                      {confirmadas} {confirmadas === 1 ? "alerta" : "alertas"}
                    </span>
                  )}
                  <span className="rounded-full bg-zinc-100 px-2.5 py-1 font-medium text-corp-muted">
                    {grupo.eventos.length} {grupo.eventos.length === 1 ? "evento" : "eventos"}
                  </span>
                </div>
              </div>

              {/* Tarjetas del día */}
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {grupo.eventos.map((evento) => {
                  const confirmada = esConfirmada(evento);
                  return (
                    <article
                      key={evento.id}
                      className={`overflow-hidden rounded-xl border bg-white shadow-sm transition hover:shadow-md ${
                        confirmada ? "border-red-200 ring-1 ring-red-100" : "border-corp-border"
                      }`}
                    >
                      <div className="relative">
                        {evento.snapshot ? (
                          <button
                            type="button"
                            onClick={() => setEventoAmpliado(evento)}
                            className="block w-full"
                            title="Ampliar foto"
                          >
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={evento.snapshot}
                              alt={`Evento en ${evento.camara_nombre}`}
                              className="h-40 w-full object-cover"
                            />
                          </button>
                        ) : (
                          <div className="flex h-40 w-full items-center justify-center bg-zinc-100 text-xs text-corp-muted">
                            Sin foto
                          </div>
                        )}
                        <span className="absolute left-2 top-2 rounded-md bg-black/60 px-2 py-0.5 text-xs font-medium text-white">
                          {hora(evento.timestamp)}
                        </span>
                        {evento.estado === "nuevo" && (
                          <span className="absolute right-2 top-2 rounded-md bg-amber-400 px-2 py-0.5 text-xs font-semibold text-black">
                            Nuevo
                          </span>
                        )}
                      </div>

                      <div className="space-y-2 p-3">
                        <div>
                          <p className="font-semibold text-corp-navy">{evento.camara_nombre}</p>
                          <p className="text-xs text-corp-muted">{evento.zona_nombre ?? "Sin zona"}</p>
                        </div>

                        {/* Resultado de la IA */}
                        {evento.tipos_ia.length > 0 ? (
                          <div className="flex flex-wrap gap-1" title={evento.descripcion_ia}>
                            {evento.tipos_ia.map((tipo) => (
                              <span
                                key={tipo.id}
                                className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                                  tipo.severidad === "alta"
                                    ? "bg-red-100 text-red-700"
                                    : tipo.severidad === "media"
                                      ? "bg-amber-100 text-amber-700"
                                      : "bg-zinc-100 text-zinc-600"
                                }`}
                              >
                                {tipo.nombre}
                              </span>
                            ))}
                          </div>
                        ) : evento.ia_analizado_en ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700">
                            <span className="h-1.5 w-1.5 rounded-full bg-green-500" /> Sin novedad
                          </span>
                        ) : (
                          <span className="text-xs text-corp-muted">Pendiente de análisis</span>
                        )}

                        <div className="flex items-center justify-between pt-1">
                          {evento.notificacion_enviada ? (
                            <span className="text-xs text-corp-muted">✉️ Notificado</span>
                          ) : (
                            <span className="text-xs text-transparent">·</span>
                          )}
                          <button
                            type="button"
                            onClick={() => alternarEstado(evento)}
                            className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy transition hover:border-corp-blue"
                          >
                            {evento.estado === "nuevo" ? "Marcar revisado" : "Marcar nuevo"}
                          </button>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          );
        })}
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
