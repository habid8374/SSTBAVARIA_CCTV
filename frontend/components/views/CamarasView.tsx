"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { Nota } from "@/components/DocTexto";
import PoligonoOverlay from "@/components/PoligonoOverlay";
import {
  ApiError,
  actualizarCamara,
  crearCamara,
  listarCamarasDashboard,
  type CamaraDashboard,
  type NuevaCamara,
  type Rol,
} from "@/lib/api";

export default function CamarasView({ token, rol }: { token: string; rol: Rol | null }) {
  const esAdmin = rol === "administrador";
  const [camaras, setCamaras] = useState<CamaraDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formulario, setFormulario] = useState<"nueva" | CamaraDashboard | null>(null);

  function cargar() {
    listarCamarasDashboard(token)
      .then(setCamaras)
      .catch(() => setError("No se pudo cargar la lista de cámaras."));
  }

  useEffect(cargar, [token]);

  async function alternarActiva(camara: CamaraDashboard) {
    try {
      await actualizarCamara(token, camara.id, { activa: !camara.activa });
      cargar();
    } catch {
      setError("No se pudo actualizar la cámara.");
    }
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Último evento reportado por cámara, con la zona restringida dibujada encima.
        </p>
        {esAdmin && (
          <button
            type="button"
            onClick={() => setFormulario("nueva")}
            className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy"
          >
            + Nueva cámara
          </button>
        )}
      </div>

      <div className="mt-4">
        <Nota tipo="aviso">
          Tratamiento de datos personales: cada zona cubierta por estas cámaras debe tener un aviso físico
          visible (&quot;Zona vigilada por cámaras con IA&quot;) antes de que la persona ingrese, conforme a
          la{" "}
          <Link href="/politica-privacidad" target="_blank" className="font-medium text-corp-blue hover:underline">
            política de tratamiento de datos personales
          </Link>
          . Descarga el cartel para imprimir desde Ayuda → Política de privacidad.
        </Nota>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {camaras?.length === 0 && (
        <p className="mt-6 text-sm text-corp-muted">
          Todavía no hay cámaras registradas
          {esAdmin ? " — usa el botón “+ Nueva cámara” de arriba." : "."}
        </p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2 xl:grid-cols-3">
        {camaras?.map((camara) => (
          <TarjetaCamara
            key={camara.id}
            camara={camara}
            esAdmin={esAdmin}
            onEditar={() => setFormulario(camara)}
            onAlternarActiva={() => alternarActiva(camara)}
          />
        ))}
      </div>

      {formulario && (
        <FormularioCamara
          token={token}
          camara={formulario === "nueva" ? null : formulario}
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

function TarjetaCamara({
  camara,
  esAdmin,
  onEditar,
  onAlternarActiva,
}: {
  camara: CamaraDashboard;
  esAdmin: boolean;
  onEditar: () => void;
  onAlternarActiva: () => void;
}) {
  const [dimensiones, setDimensiones] = useState<{ w: number; h: number } | null>(null);
  const evento = camara.ultimo_evento;
  const imagen = evento?.snapshot ?? camara.snapshot_referencia;

  const zona = camara.zonas.find((z) => z.id === evento?.zona) ?? camara.zonas[0] ?? null;
  const enAlerta = Boolean(evento?.disparo_alerta);
  const colorZona = !evento ? "#eab308" : enAlerta ? "#ef4444" : "#22c55e";

  const puntoEvento =
    evento && evento.punto_x !== null && evento.punto_y !== null ? [evento.punto_x, evento.punto_y] : null;
  const tamanoMarcador = dimensiones ? Math.max(dimensiones.w * 0.05, 10) : 10;

  return (
    <div className="overflow-hidden rounded-xl border border-corp-border bg-white shadow-sm">
      <div className="flex items-center justify-between bg-corp-navy px-4 py-2.5 text-white">
        <div>
          <p className="text-sm font-semibold">{camara.nombre}</p>
          <p className="text-xs text-white/60">{camara.ubicacion || "Sin ubicación registrada"}</p>
        </div>
        <span className={`h-2.5 w-2.5 rounded-full ${camara.activa ? "bg-red-500" : "bg-white/30"}`} />
      </div>

      <div className="relative bg-zinc-100">
        {imagen ? (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imagen}
              alt={`Encuadre de ${camara.nombre}`}
              className="block w-full"
              onLoad={(e) =>
                setDimensiones({
                  w: e.currentTarget.naturalWidth,
                  h: e.currentTarget.naturalHeight,
                })
              }
            />
            {dimensiones && zona && (
              <PoligonoOverlay
                puntos={zona.poligono}
                naturalWidth={dimensiones.w}
                naturalHeight={dimensiones.h}
                color={colorZona}
              />
            )}
            {dimensiones && puntoEvento && (
              <div
                className="absolute rounded-sm border-2"
                style={{
                  left: `${(puntoEvento[0] / dimensiones.w) * 100}%`,
                  top: `${(puntoEvento[1] / dimensiones.h) * 100}%`,
                  width: `${tamanoMarcador}px`,
                  height: `${tamanoMarcador}px`,
                  transform: "translate(-50%, -50%)",
                  borderColor: colorZona,
                }}
              />
            )}
          </>
        ) : (
          <div className="flex aspect-video items-center justify-center text-sm text-corp-muted">
            Sin snapshot todavía
          </div>
        )}
      </div>

      <div
        className={`px-4 py-2 text-center text-xs font-semibold text-white ${
          !evento ? "bg-zinc-400" : enAlerta ? "bg-red-500" : "bg-green-500"
        }`}
      >
        {!evento
          ? "Sin eventos registrados"
          : enAlerta
            ? "ALERTA — Persona en zona restringida fuera de horario"
            : "Sin alertas — actividad normal"}
      </div>

      {evento && (
        <p className="px-4 py-2 text-xs text-corp-muted">
          {new Date(evento.timestamp).toLocaleString("es-CO")}
          {zona ? ` · ${zona.nombre}` : ""}
        </p>
      )}

      {esAdmin && (
        <div className="flex justify-end gap-2 border-t border-corp-border px-4 py-2">
          <button
            type="button"
            onClick={onEditar}
            className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy transition hover:border-corp-blue"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={onAlternarActiva}
            className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy transition hover:border-corp-blue"
          >
            {camara.activa ? "Desactivar" : "Activar"}
          </button>
        </div>
      )}
    </div>
  );
}

function FormularioCamara({
  token,
  camara,
  onCerrar,
  onGuardada,
}: {
  token: string;
  camara: CamaraDashboard | null;
  onCerrar: () => void;
  onGuardada: () => void;
}) {
  const [nombre, setNombre] = useState(camara?.nombre ?? "");
  const [ip, setIp] = useState(camara?.ip ?? "");
  const [puertoOnvif, setPuertoOnvif] = useState(String(camara?.puerto_onvif ?? 80));
  const [usuarioOnvif, setUsuarioOnvif] = useState(camara?.usuario_onvif ?? "");
  const [passwordOnvif, setPasswordOnvif] = useState(camara?.password_onvif ?? "");
  const [rtspUrl, setRtspUrl] = useState(camara?.rtsp_url ?? "");
  const [ubicacion, setUbicacion] = useState(camara?.ubicacion ?? "");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    const datos: NuevaCamara = {
      nombre,
      ip,
      puerto_onvif: Number(puertoOnvif) || 80,
      usuario_onvif: usuarioOnvif,
      password_onvif: passwordOnvif,
      rtsp_url: rtspUrl,
      ubicacion,
    };
    try {
      if (camara) {
        await actualizarCamara(token, camara.id, datos);
      } else {
        await crearCamara(token, datos);
      }
      onGuardada();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la cámara.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">
          {camara ? "Editar cámara" : "Nueva cámara"}
        </h2>
        {!camara && (
          <div className="mt-3">
            <Nota tipo="aviso">
              Si es una Dahua Picoo (A2 o B1): antes de registrarla acá, entra a la app DMSS →{" "}
              <strong>IA → Detección</strong> y confirma que{" "}
              <strong>&quot;Seguimiento automático&quot;</strong> esté apagado. Si la cámara se mueve sola al
              detectar a alguien, el encuadre deja de coincidir con la foto de referencia y las zonas
              restringidas quedan mal calibradas.
            </Nota>
          </div>
        )}
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <Campo label="Nombre">
            <input
              required
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej. CAM 01 — Muelle de Recepción"
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <Campo label="Dirección IP">
            <input
              required
              value={ip}
              onChange={(e) => setIp(e.target.value)}
              placeholder="192.168.1.10"
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <Campo label="Ubicación">
            <input
              value={ubicacion}
              onChange={(e) => setUbicacion(e.target.value)}
              placeholder="Ej. Muelle de recepción"
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Puerto ONVIF">
              <input
                type="number"
                value={puertoOnvif}
                onChange={(e) => setPuertoOnvif(e.target.value)}
                className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
              />
            </Campo>
            <Campo label="Usuario ONVIF">
              <input
                value={usuarioOnvif}
                onChange={(e) => setUsuarioOnvif(e.target.value)}
                className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
              />
            </Campo>
          </div>
          <Campo label="Contraseña ONVIF">
            <input
              type="password"
              value={passwordOnvif}
              onChange={(e) => setPasswordOnvif(e.target.value)}
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <Campo label="URL RTSP (opcional)">
            <input
              value={rtspUrl}
              onChange={(e) => setRtspUrl(e.target.value)}
              placeholder="Vacío = usa el patrón estándar de Dahua con la IP y credenciales de arriba"
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
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
              {enviando ? "Guardando…" : camara ? "Guardar cambios" : "Crear cámara"}
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
