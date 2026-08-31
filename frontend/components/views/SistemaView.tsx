"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import {
  ApiError,
  actualizarConfiguracionNotificaciones,
  actualizarEquipoLocal,
  crearEquipoLocal,
  eliminarEquipoLocal,
  listarEquiposLocales,
  obtenerConfiguracionNotificaciones,
  type ConfiguracionNotificaciones,
  type EquipoLocal,
} from "@/lib/api";

type Pestana = "brevo" | "equipo-local";

export default function SistemaView({ token }: { token: string }) {
  const [pestana, setPestana] = useState<Pestana>("brevo");

  return (
    <div>
      <div className="mb-6 flex gap-1 border-b border-corp-border">
        <BotonPestana activa={pestana === "brevo"} onClick={() => setPestana("brevo")}>
          Brevo (correo)
        </BotonPestana>
        <BotonPestana activa={pestana === "equipo-local"} onClick={() => setPestana("equipo-local")}>
          Equipo local
        </BotonPestana>
      </div>

      {pestana === "brevo" ? <ConfiguracionBrevo token={token} /> : <EquiposLocales token={token} />}
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

function ConfiguracionBrevo({ token }: { token: string }) {
  const [config, setConfig] = useState<ConfiguracionNotificaciones | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [remitenteEmail, setRemitenteEmail] = useState("");
  const [remitenteNombre, setRemitenteNombre] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    obtenerConfiguracionNotificaciones(token)
      .then((data) => {
        setConfig(data);
        setRemitenteEmail(data.brevo_remitente_email);
        setRemitenteNombre(data.brevo_remitente_nombre);
      })
      .catch(() => setError("No se pudo cargar la configuración de Brevo."));
  }

  useEffect(cargar, [token]);

  async function guardar(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setExito(null);
    setGuardando(true);
    try {
      const cambios: Parameters<typeof actualizarConfiguracionNotificaciones>[1] = {
        brevo_remitente_email: remitenteEmail,
        brevo_remitente_nombre: remitenteNombre,
      };
      if (apiKey.trim()) {
        cambios.brevo_api_key = apiKey.trim();
      }
      const actualizado = await actualizarConfiguracionNotificaciones(token, cambios);
      setConfig(actualizado);
      setApiKey("");
      setExito("Configuración guardada.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la configuración.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          API key con la que se envían las alertas por correo (Brevo) — se guarda acá en vez de en Railway,
          para que se pueda cambiar sin tocar el servidor.
        </p>
        {config && (
          <span
            className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
              config.brevo_api_key_configurada ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
            }`}
          >
            {config.brevo_api_key_configurada ? "API key configurada" : "Sin API key configurada"}
          </span>
        )}
      </div>

      <form onSubmit={guardar} className="mt-6 max-w-md space-y-4 rounded-xl border border-corp-border bg-white p-5">
        <Campo label="API key de Brevo">
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder={config?.brevo_api_key_configurada ? "•••••••• (sin cambios)" : "xkeysib-…"}
            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
          <p className="text-xs text-corp-muted">
            Se obtiene en Brevo → Configuración → SMTP e API → API Keys. Déjalo en blanco para no cambiarla.
          </p>
        </Campo>
        <Campo label="Correo remitente">
          <input
            type="email"
            value={remitenteEmail}
            onChange={(event) => setRemitenteEmail(event.target.value)}
            placeholder="alertas@sstbavaria.com"
            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
        </Campo>
        <Campo label="Nombre del remitente">
          <input
            value={remitenteNombre}
            onChange={(event) => setRemitenteNombre(event.target.value)}
            placeholder="SST Bavaria — Cámaras IA"
            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
        </Campo>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
        )}
        {exito && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
            {exito}
          </div>
        )}

        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={guardando}
            className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:opacity-60"
          >
            {guardando ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </form>
    </div>
  );
}

function EquiposLocales({ token }: { token: string }) {
  const [equipos, setEquipos] = useState<EquipoLocal[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [copiadoId, setCopiadoId] = useState<number | null>(null);

  function cargar() {
    listarEquiposLocales(token)
      .then(setEquipos)
      .catch(() => setError("No se pudo cargar la lista de equipos locales."));
  }

  useEffect(cargar, [token]);

  async function alternarActivo(equipo: EquipoLocal) {
    try {
      await actualizarEquipoLocal(token, equipo.id, { activo: !equipo.activo });
      cargar();
    } catch {
      setError("No se pudo actualizar el equipo.");
    }
  }

  async function eliminar(equipo: EquipoLocal) {
    if (!window.confirm(`¿Eliminar "${equipo.nombre}"? El equipo local dejará de poder autenticarse.`)) return;
    try {
      await eliminarEquipoLocal(token, equipo.id);
      cargar();
    } catch {
      setError("No se pudo eliminar el equipo.");
    }
  }

  async function copiarApiKey(equipo: EquipoLocal) {
    try {
      await navigator.clipboard.writeText(equipo.api_key);
      setCopiadoId(equipo.id);
      setTimeout(() => setCopiadoId((actual) => (actual === equipo.id ? null : actual)), 2000);
    } catch {
      // clipboard no disponible (ej. sin HTTPS) — el valor sigue visible para copiar a mano
    }
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Cada PC/DVR en sitio que corre <code>equipo_local</code> necesita un registro acá — copia el{" "}
          <code>api_key</code> generado a su <code>.env</code> (variable <code>API_KEY</code>).
        </p>
        <button
          type="button"
          onClick={() => setMostrarFormulario(true)}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy"
        >
          + Nuevo equipo
        </button>
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
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">API key</th>
              <th className="px-4 py-3">Conexión</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {equipos?.map((equipo) => (
              <tr key={equipo.id} className="border-b border-corp-border last:border-0">
                <td className="px-4 py-3 font-medium text-corp-navy">{equipo.nombre}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-corp-muted">
                      {equipo.api_key.slice(0, 10)}…
                    </code>
                    <button
                      type="button"
                      onClick={() => copiarApiKey(equipo)}
                      className="text-xs font-medium text-corp-blue hover:underline"
                    >
                      {copiadoId === equipo.id ? "¡Copiado!" : "Copiar"}
                    </button>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      equipo.conectado ? "bg-green-100 text-green-700" : "bg-zinc-100 text-zinc-500"
                    }`}
                    title={
                      equipo.ultima_conexion
                        ? `Última conexión: ${new Date(equipo.ultima_conexion).toLocaleString("es-CO")}`
                        : "Todavía no se ha conectado"
                    }
                  >
                    {equipo.conectado ? "Conectado" : equipo.ultima_conexion ? "Sin conexión reciente" : "Nunca"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      equipo.activo ? "bg-green-100 text-green-700" : "bg-zinc-100 text-zinc-500"
                    }`}
                  >
                    {equipo.activo ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => alternarActivo(equipo)}
                      className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy hover:border-corp-blue"
                    >
                      {equipo.activo ? "Desactivar" : "Activar"}
                    </button>
                    <button
                      type="button"
                      onClick={() => eliminar(equipo)}
                      className="rounded-md border border-red-200 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                    >
                      Eliminar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {equipos?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-corp-muted">
            Todavía no hay equipos locales registrados.
          </p>
        )}
      </div>

      {mostrarFormulario && (
        <FormularioNuevoEquipo
          token={token}
          onCerrar={() => setMostrarFormulario(false)}
          onCreado={() => {
            setMostrarFormulario(false);
            cargar();
          }}
        />
      )}
    </div>
  );
}

function FormularioNuevoEquipo({
  token,
  onCerrar,
  onCreado,
}: {
  token: string;
  onCerrar: () => void;
  onCreado: () => void;
}) {
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await crearEquipoLocal(token, nombre);
      onCreado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el equipo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">Nuevo equipo local</h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <Campo label="Nombre">
            <input
              required
              autoFocus
              value={nombre}
              onChange={(event) => setNombre(event.target.value)}
              placeholder="Equipo Bodega Principal"
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
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
              {enviando ? "Creando…" : "Crear equipo"}
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
