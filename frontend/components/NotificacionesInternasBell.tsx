"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  listarNotificacionesInternas,
  marcarNotificacionLeida,
  marcarTodasNotificacionesLeidas,
  type NotificacionInterna,
} from "@/lib/api";
import type { SeccionId } from "./Sidebar";
import { IconCampana } from "./icons";

const POLL_MS = 45_000;

function seccionParaNotificacion(notificacion: NotificacionInterna): SeccionId {
  return notificacion.tipo === "radicacion_pendiente" ? "contratistas" : "declaracion-metodo";
}

function tiempoRelativo(fecha: string): string {
  const minutos = Math.round((Date.now() - new Date(fecha).getTime()) / 60000);
  if (minutos < 1) return "ahora mismo";
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  const dias = Math.round(horas / 24);
  return `hace ${dias} d`;
}

export default function NotificacionesInternasBell({
  token,
  onIrA,
}: {
  token: string;
  onIrA: (seccion: SeccionId) => void;
}) {
  const [notificaciones, setNotificaciones] = useState<NotificacionInterna[]>([]);
  const [abierto, setAbierto] = useState(false);
  const contenedorRef = useRef<HTMLDivElement>(null);

  const cargar = useCallback(() => {
    listarNotificacionesInternas(token)
      .then(setNotificaciones)
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    cargar();
    const id = window.setInterval(cargar, POLL_MS);
    return () => window.clearInterval(id);
  }, [cargar]);

  useEffect(() => {
    if (!abierto) return;
    function alHacerClicFuera(event: MouseEvent) {
      if (contenedorRef.current && !contenedorRef.current.contains(event.target as Node)) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", alHacerClicFuera);
    return () => document.removeEventListener("mousedown", alHacerClicFuera);
  }, [abierto]);

  const noLeidas = notificaciones.filter((n) => !n.leida).length;

  async function abrir(notificacion: NotificacionInterna) {
    setAbierto(false);
    onIrA(seccionParaNotificacion(notificacion));
    if (!notificacion.leida) {
      setNotificaciones((actual) =>
        actual.map((n) => (n.id === notificacion.id ? { ...n, leida: true } : n))
      );
      try {
        await marcarNotificacionLeida(token, notificacion.id);
      } catch {
        cargar();
      }
    }
  }

  async function marcarTodas() {
    setNotificaciones((actual) => actual.map((n) => ({ ...n, leida: true })));
    try {
      await marcarTodasNotificacionesLeidas(token);
    } catch {
      cargar();
    }
  }

  return (
    <div ref={contenedorRef} className="relative">
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        className="relative rounded-lg p-2 text-corp-navy hover:bg-corp-blue-light"
        aria-label="Notificaciones"
      >
        <IconCampana className="h-5 w-5" />
        {noLeidas > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">
            {noLeidas > 9 ? "9+" : noLeidas}
          </span>
        )}
      </button>

      {abierto && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-corp-border bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-corp-border px-4 py-2.5">
            <h3 className="text-sm font-semibold text-corp-navy">Notificaciones</h3>
            {noLeidas > 0 && (
              <button
                type="button"
                onClick={marcarTodas}
                className="text-xs font-semibold text-corp-blue hover:underline"
              >
                Marcar todas leídas
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {notificaciones.length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-corp-muted">
                No hay nada pendiente por revisar.
              </p>
            )}
            {notificaciones.map((notificacion) => (
              <button
                key={notificacion.id}
                type="button"
                onClick={() => abrir(notificacion)}
                className={`block w-full border-b border-corp-border px-4 py-2.5 text-left text-sm last:border-0 hover:bg-corp-blue-light/40 ${
                  notificacion.leida ? "text-corp-muted" : "text-corp-navy"
                }`}
              >
                <div className="flex items-start gap-2">
                  {!notificacion.leida && (
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-corp-blue" />
                  )}
                  <div className={notificacion.leida ? "ml-3.5" : ""}>
                    <p className={notificacion.leida ? "" : "font-medium"}>{notificacion.mensaje}</p>
                    <p className="mt-0.5 text-xs text-corp-muted">{tiempoRelativo(notificacion.creada_en)}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
