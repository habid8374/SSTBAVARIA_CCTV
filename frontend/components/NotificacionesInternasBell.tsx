"use client";

import { useCallback, useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";

import {
  desuscribirPush,
  eliminarNotificacionInterna,
  eliminarNotificacionesInternasLeidas,
  listarNotificacionesInternas,
  marcarNotificacionLeida,
  marcarTodasNotificacionesLeidas,
  obtenerClavePublicaPush,
  suscribirPush,
  type NotificacionInterna,
} from "@/lib/api";
import { useDialog } from "./DialogProvider";
import type { SeccionId } from "./Sidebar";
import { IconCampana } from "./icons";

const POLL_MS = 45_000;

function seccionParaNotificacion(notificacion: NotificacionInterna): SeccionId {
  return notificacion.tipo === "radicacion_pendiente" ? "contratistas" : "declaracion-metodo";
}

/** El navegador manda la clave pública VAPID en base64url; PushManager.subscribe
 * la necesita como Uint8Array — es la única conversión que hace falta. */
function base64UrlAUint8Array(base64Url: string): Uint8Array {
  const relleno = "=".repeat((4 - (base64Url.length % 4)) % 4);
  const base64 = (base64Url + relleno).replace(/-/g, "+").replace(/_/g, "/");
  const binario = window.atob(base64);
  return Uint8Array.from([...binario].map((caracter) => caracter.charCodeAt(0)));
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
  const [soportaPush, setSoportaPush] = useState(false);
  const [suscritoPush, setSuscritoPush] = useState(false);
  const [cargandoPush, setCargandoPush] = useState(false);
  const contenedorRef = useRef<HTMLDivElement>(null);
  const { confirmar } = useDialog();

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
    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) return;
    // Se detecta una sola vez al montar si el navegador soporta Web Push.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSoportaPush(true);
    navigator.serviceWorker.ready
      .then((registro) => registro.pushManager.getSubscription())
      .then((suscripcion) => setSuscritoPush(!!suscripcion))
      .catch(() => {});
  }, []);

  async function activarPush() {
    setCargandoPush(true);
    try {
      const permiso = await Notification.requestPermission();
      if (permiso !== "granted") return;
      const { clave_publica } = await obtenerClavePublicaPush(token);
      if (!clave_publica) return;
      const registro = await navigator.serviceWorker.ready;
      const suscripcion = await registro.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: base64UrlAUint8Array(clave_publica) as BufferSource,
      });
      await suscribirPush(token, suscripcion.toJSON());
      setSuscritoPush(true);
    } catch {
      // sin permiso, sin llave configurada, o el navegador no lo soportó
      // de verdad pese a los checks de arriba — se deja como estaba
    } finally {
      setCargandoPush(false);
    }
  }

  async function desactivarPush() {
    setCargandoPush(true);
    try {
      const registro = await navigator.serviceWorker.ready;
      const suscripcion = await registro.pushManager.getSubscription();
      if (suscripcion) {
        await desuscribirPush(token, suscripcion.endpoint);
        await suscripcion.unsubscribe();
      }
      setSuscritoPush(false);
    } catch {
      // se deja como estaba
    } finally {
      setCargandoPush(false);
    }
  }

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

  async function eliminar(id: number, event: ReactMouseEvent) {
    event.stopPropagation();
    setNotificaciones((actual) => actual.filter((n) => n.id !== id));
    try {
      await eliminarNotificacionInterna(token, id);
    } catch {
      cargar();
    }
  }

  async function eliminarLeidas() {
    const ok = await confirmar({
      titulo: "Eliminar notificaciones leídas",
      mensaje: "¿Eliminar todas las notificaciones ya leídas? Las que sigan sin leer no se tocan.",
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
    setNotificaciones((actual) => actual.filter((n) => !n.leida));
    try {
      await eliminarNotificacionesInternasLeidas(token);
    } catch {
      cargar();
    }
  }

  const hayLeidas = notificaciones.some((n) => n.leida);

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
          <div className="flex items-center justify-between gap-3 border-b border-corp-border px-4 py-2.5">
            <h3 className="text-sm font-semibold text-corp-navy">Notificaciones</h3>
            <div className="flex items-center gap-3">
              {noLeidas > 0 && (
                <button
                  type="button"
                  onClick={marcarTodas}
                  className="text-xs font-semibold text-corp-blue hover:underline"
                >
                  Marcar todas leídas
                </button>
              )}
              {hayLeidas && (
                <button
                  type="button"
                  onClick={eliminarLeidas}
                  className="text-xs font-semibold text-red-600 hover:underline"
                >
                  Eliminar leídas
                </button>
              )}
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {notificaciones.length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-corp-muted">
                No hay nada pendiente por revisar.
              </p>
            )}
            {notificaciones.map((notificacion) => (
              <div
                key={notificacion.id}
                className={`group flex items-start gap-1 border-b border-corp-border text-sm last:border-0 hover:bg-corp-blue-light/40 ${
                  notificacion.leida ? "text-corp-muted" : "text-corp-navy"
                }`}
              >
                <button
                  type="button"
                  onClick={() => abrir(notificacion)}
                  className="flex flex-1 items-start gap-2 px-4 py-2.5 text-left"
                >
                  {!notificacion.leida && (
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-corp-blue" />
                  )}
                  <div className={notificacion.leida ? "ml-3.5" : ""}>
                    <p className={notificacion.leida ? "" : "font-medium"}>{notificacion.mensaje}</p>
                    <p className="mt-0.5 text-xs text-corp-muted">{tiempoRelativo(notificacion.creada_en)}</p>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={(event) => eliminar(notificacion.id, event)}
                  title="Eliminar notificación"
                  aria-label="Eliminar notificación"
                  className="mr-2 mt-2 shrink-0 rounded p-1 text-corp-muted opacity-0 transition hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          {soportaPush && (
            <div className="border-t border-corp-border px-4 py-2.5">
              <button
                type="button"
                onClick={suscritoPush ? desactivarPush : activarPush}
                disabled={cargandoPush}
                className="text-xs font-medium text-corp-blue hover:underline disabled:opacity-60"
              >
                {cargandoPush
                  ? "Un momento…"
                  : suscritoPush
                    ? "🔕 Desactivar notificaciones en este dispositivo"
                    : "🔔 Activar notificaciones en este dispositivo"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
