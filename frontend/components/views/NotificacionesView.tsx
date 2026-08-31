"use client";

import { useEffect, useState } from "react";

import { listarEventos, type EventoDashboard, type Rol } from "@/lib/api";

import ConfiguracionAlertasView from "./ConfiguracionAlertasView";

type Pestana = "envios" | "configuracion";
type FiltroCanal = "todos" | "whatsapp" | "correo";

export default function NotificacionesView({ token, rol }: { token: string; rol: Rol | null }) {
  const [pestana, setPestana] = useState<Pestana>("envios");

  return (
    <div>
      <div className="mb-6 flex gap-1 border-b border-corp-border">
        <BotonPestana activa={pestana === "envios"} onClick={() => setPestana("envios")}>
          Envíos
        </BotonPestana>
        <BotonPestana activa={pestana === "configuracion"} onClick={() => setPestana("configuracion")}>
          Configuración
        </BotonPestana>
      </div>

      {pestana === "envios" ? (
        <EnviosNotificaciones token={token} />
      ) : (
        <ConfiguracionAlertasView token={token} rol={rol} />
      )}
    </div>
  );
}

function BotonPestana({
  activa,
  onClick,
  children,
}: {
  activa: boolean;
  onClick: () => void;
  children: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition ${
        activa ? "border-corp-blue text-corp-blue" : "border-transparent text-corp-muted hover:text-corp-navy"
      }`}
    >
      {children}
    </button>
  );
}

function BadgeEstadoEnvio({ evento }: { evento: EventoDashboard }) {
  if (evento.notificacion_enviada) {
    return (
      <span
        title={evento.notificacion_detalle}
        className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
      >
        Enviada
      </span>
    );
  }
  if (evento.notificacion_detalle) {
    return (
      <span
        title={evento.notificacion_detalle}
        className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700"
      >
        Error
      </span>
    );
  }
  // Canal WhatsApp: sigue siendo un stub, no hay envío real que reportar.
  return <span className="text-xs text-corp-muted">N/D</span>;
}

function EnviosNotificaciones({ token }: { token: string }) {
  const [eventos, setEventos] = useState<EventoDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filtroCanal, setFiltroCanal] = useState<FiltroCanal>("todos");

  function cargar() {
    listarEventos(token, {
      disparo_alerta: true,
      canal_notificacion: filtroCanal === "todos" ? undefined : filtroCanal,
    })
      .then(setEventos)
      .catch(() => setError("No se pudo cargar el registro de notificaciones."));
  }

  useEffect(cargar, [token, filtroCanal]);

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Historial de notificaciones enviadas por cada alerta disparada, con su canal y estado.
        </p>
        <select
          value={filtroCanal}
          onChange={(e) => setFiltroCanal(e.target.value as FiltroCanal)}
          className="rounded-md border border-corp-border px-2 py-1.5 text-sm"
        >
          <option value="todos">Todos los canales</option>
          <option value="correo">Solo correo</option>
          <option value="whatsapp">Solo WhatsApp</option>
        </select>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-6 overflow-x-auto rounded-xl border border-corp-border bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-corp-border bg-corp-blue-light text-xs uppercase text-corp-muted">
            <tr>
              <th className="px-4 py-3">Cámara</th>
              <th className="px-4 py-3">Zona</th>
              <th className="px-4 py-3">Fecha</th>
              <th className="px-4 py-3">Canal</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Detalle</th>
            </tr>
          </thead>
          <tbody>
            {eventos?.map((evento) => (
              <tr key={evento.id} className="border-b border-corp-border last:border-0">
                <td className="px-4 py-3 font-medium text-corp-navy">{evento.camara_nombre}</td>
                <td className="px-4 py-3 text-corp-muted">{evento.zona_nombre ?? "—"}</td>
                <td className="px-4 py-3 text-corp-muted">
                  {new Date(evento.timestamp).toLocaleString("es-CO")}
                </td>
                <td className="px-4 py-3 text-corp-muted capitalize">{evento.canal_notificacion || "—"}</td>
                <td className="px-4 py-3">
                  <BadgeEstadoEnvio evento={evento} />
                </td>
                <td className="px-4 py-3 max-w-[280px] truncate text-corp-muted" title={evento.notificacion_detalle}>
                  {evento.notificacion_detalle || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {eventos?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-corp-muted">
            Todavía no se ha enviado ninguna notificación.
          </p>
        )}
      </div>
    </div>
  );
}
