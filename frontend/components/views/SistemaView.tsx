"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { useDialog } from "@/components/DialogProvider";
import {
  ApiError,
  actualizarConfiguracionIA,
  actualizarConfiguracionNotificaciones,
  actualizarEquipoLocal,
  actualizarTipoEventoIA,
  crearEquipoLocal,
  crearTipoEventoIA,
  descargarEquipoLocalZip,
  eliminarEquipoLocal,
  eliminarTipoEventoIA,
  enviarAccesoVisitantes,
  listarEquiposLocales,
  listarTiposEventoIA,
  obtenerConfiguracionIA,
  obtenerConfiguracionNotificaciones,
  type ConfiguracionIA,
  type ConfiguracionNotificaciones,
  type EquipoLocal,
  type NuevoTipoEventoIA,
  type ProveedorIA,
  type Severidad,
  type TipoEventoIA,
} from "@/lib/api";
import AuditoriaView from "./AuditoriaView";
import ReglasContratistasView from "./ReglasContratistasView";

type Pestana = "brevo" | "ia" | "equipo-local" | "visitantes" | "reglas" | "auditoria";

export default function SistemaView({ token, esSuperusuario }: { token: string; esSuperusuario: boolean }) {
  const [pestana, setPestana] = useState<Pestana>("brevo");

  return (
    <div>
      <div className="mb-6 flex gap-1 overflow-x-auto border-b border-corp-border">
        <BotonPestana activa={pestana === "brevo"} onClick={() => setPestana("brevo")}>
          Brevo (correo)
        </BotonPestana>
        <BotonPestana activa={pestana === "ia"} onClick={() => setPestana("ia")}>
          Inteligencia Artificial
        </BotonPestana>
        <BotonPestana activa={pestana === "equipo-local"} onClick={() => setPestana("equipo-local")}>
          Equipo local
        </BotonPestana>
        <BotonPestana activa={pestana === "visitantes"} onClick={() => setPestana("visitantes")}>
          Visitantes
        </BotonPestana>
        <BotonPestana activa={pestana === "reglas"} onClick={() => setPestana("reglas")}>
          Reglas de contratistas
        </BotonPestana>
        {esSuperusuario && (
          <BotonPestana activa={pestana === "auditoria"} onClick={() => setPestana("auditoria")}>
            Auditoría
          </BotonPestana>
        )}
      </div>

      {pestana === "brevo" && <ConfiguracionBrevo token={token} />}
      {pestana === "ia" && <ConfiguracionInteligenciaArtificial token={token} />}
      {pestana === "equipo-local" && <EquiposLocales token={token} />}
      {pestana === "visitantes" && <EnviarAccesoVisitantes token={token} />}
      {pestana === "reglas" && <ReglasContratistasView token={token} />}
      {pestana === "auditoria" && esSuperusuario && <AuditoriaView token={token} />}
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
      className={`-mb-px shrink-0 whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition ${
        activa ? "border-corp-blue text-corp-gold" : "border-transparent text-corp-muted hover:text-corp-navy"
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
            placeholder="alertas@sst-cctv.com"
            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
        </Campo>
        <Campo label="Nombre del remitente">
          <input
            value={remitenteNombre}
            onChange={(event) => setRemitenteNombre(event.target.value)}
            placeholder="GuardIA"
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
            className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:opacity-60"
          >
            {guardando ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </form>
    </div>
  );
}

function ConfiguracionInteligenciaArtificial({ token }: { token: string }) {
  const [config, setConfig] = useState<ConfiguracionIA | null>(null);
  const [proveedor, setProveedor] = useState<ProveedorIA>("claude");
  const [apiKey, setApiKey] = useState("");
  const [modelo, setModelo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    obtenerConfiguracionIA(token)
      .then((data) => {
        setConfig(data);
        setProveedor(data.proveedor);
        setModelo(data.modelo);
      })
      .catch(() => setError("No se pudo cargar la configuración de IA."));
  }

  useEffect(cargar, [token]);

  async function guardar(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setExito(null);
    setGuardando(true);
    try {
      const cambios: Parameters<typeof actualizarConfiguracionIA>[1] = { proveedor, modelo };
      if (apiKey.trim()) {
        cambios.api_key = apiKey.trim();
      }
      const actualizado = await actualizarConfiguracionIA(token, cambios);
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
          Cuando el equipo local reporta una persona en una zona restringida, el snapshot se le manda a un
          modelo de visión (Claude o Gemini) para que revise si aparece alguno de los eventos del catálogo de
          abajo (EPP faltante, caídas, comportamiento riesgoso, etc.) — es opcional: sin API key configurada,
          el sistema sigue funcionando igual, solo sin esa clasificación extra.
        </p>
        {config && (
          <span
            className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
              config.api_key_configurada ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
            }`}
          >
            {config.api_key_configurada ? "API key configurada" : "Sin API key configurada"}
          </span>
        )}
      </div>

      <form onSubmit={guardar} className="mt-6 max-w-md space-y-4 rounded-xl border border-corp-border bg-white p-5">
        <Campo label="Proveedor">
          <select
            value={proveedor}
            onChange={(event) => setProveedor(event.target.value as ProveedorIA)}
            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          >
            <option value="claude">Claude (Anthropic)</option>
            <option value="gemini">Gemini (Google)</option>
          </select>
        </Campo>
        <Campo label="API key">
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder={config?.api_key_configurada ? "•••••••• (sin cambios)" : "sk-ant-… o AIza…"}
            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
          <p className="text-xs text-corp-muted">Déjalo en blanco para no cambiarla.</p>
        </Campo>
        <Campo label="Modelo (opcional)">
          <input
            value={modelo}
            onChange={(event) => setModelo(event.target.value)}
            placeholder={proveedor === "claude" ? "claude-opus-5" : "gemini-flash-latest"}
            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
          <p className="text-xs text-corp-muted">Déjalo vacío para usar el valor por defecto.</p>
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
            className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:opacity-60"
          >
            {guardando ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </form>

      <div className="mt-8">
        <h3 className="text-sm font-semibold text-corp-navy">Catálogo de eventos a detectar</h3>
        <p className="mt-1 text-sm text-corp-muted">
          Cada fila es una instrucción en lenguaje natural — entre más detallada, mejor detecta la IA. Ej.
          &quot;Persona sin casco de seguridad puesto en la cabeza&quot;.
        </p>
        <CatalogoEventosIA token={token} />
      </div>
    </div>
  );
}

function CatalogoEventosIA({ token }: { token: string }) {
  const [tipos, setTipos] = useState<TipoEventoIA[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const { confirmar } = useDialog();

  function cargar() {
    listarTiposEventoIA(token)
      .then(setTipos)
      .catch(() => setError("No se pudo cargar el catálogo de eventos."));
  }

  useEffect(cargar, [token]);

  async function alternarActivo(tipo: TipoEventoIA) {
    try {
      await actualizarTipoEventoIA(token, tipo.id, { activo: !tipo.activo });
      cargar();
    } catch {
      setError("No se pudo actualizar el evento.");
    }
  }

  async function eliminar(tipo: TipoEventoIA) {
    const ok = await confirmar({
      titulo: "Eliminar tipo de evento",
      mensaje: `¿Eliminar "${tipo.nombre}"? La IA dejará de buscarlo en los snapshots.`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
    try {
      await eliminarTipoEventoIA(token, tipo.id);
      cargar();
    } catch {
      setError("No se pudo eliminar el evento.");
    }
  }

  const colorSeveridad: Record<Severidad, string> = {
    alta: "bg-red-100 text-red-700",
    media: "bg-amber-100 text-amber-700",
    baja: "bg-zinc-100 text-zinc-600",
  };

  return (
    <div>
      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={() => setMostrarFormulario(true)}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white"
        >
          + Nuevo evento
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-4 overflow-x-auto rounded-xl border border-corp-border bg-white">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-corp-border bg-corp-blue-light text-xs uppercase text-corp-muted">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Descripción</th>
              <th className="px-4 py-3">Severidad</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {tipos?.map((tipo) => (
              <tr key={tipo.id} className="border-b border-corp-border last:border-0">
                <td className="px-4 py-3 font-medium text-corp-navy">{tipo.nombre}</td>
                <td className="max-w-xs px-4 py-3 text-corp-muted">{tipo.descripcion}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colorSeveridad[tipo.severidad]}`}>
                    {tipo.severidad}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      tipo.activo ? "bg-green-100 text-green-700" : "bg-zinc-100 text-zinc-500"
                    }`}
                  >
                    {tipo.activo ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => alternarActivo(tipo)}
                      className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy hover:border-corp-blue"
                    >
                      {tipo.activo ? "Desactivar" : "Activar"}
                    </button>
                    <button
                      type="button"
                      onClick={() => eliminar(tipo)}
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
        {tipos?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-corp-muted">
            Todavía no hay eventos configurados en el catálogo.
          </p>
        )}
      </div>

      {mostrarFormulario && (
        <FormularioNuevoTipoEvento
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

function FormularioNuevoTipoEvento({
  token,
  onCerrar,
  onCreado,
}: {
  token: string;
  onCerrar: () => void;
  onCreado: () => void;
}) {
  const [datos, setDatos] = useState<NuevoTipoEventoIA>({ nombre: "", descripcion: "", severidad: "media" });
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await crearTipoEventoIA(token, datos);
      onCreado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el evento.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">Nuevo evento a detectar</h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <Campo label="Nombre">
            <input
              required
              autoFocus
              value={datos.nombre}
              onChange={(event) => setDatos({ ...datos, nombre: event.target.value })}
              placeholder="Sin casco"
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <Campo label="Descripción (qué debe buscar la IA)">
            <textarea
              required
              rows={3}
              value={datos.descripcion}
              onChange={(event) => setDatos({ ...datos, descripcion: event.target.value })}
              placeholder="Persona sin casco de seguridad puesto en la cabeza"
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <Campo label="Severidad">
            <select
              value={datos.severidad}
              onChange={(event) => setDatos({ ...datos, severidad: event.target.value as Severidad })}
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            >
              <option value="baja">Baja</option>
              <option value="media">Media</option>
              <option value="alta">Alta</option>
            </select>
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
              className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:opacity-60"
            >
              {enviando ? "Creando…" : "Crear evento"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EquiposLocales({ token }: { token: string }) {
  const [equipos, setEquipos] = useState<EquipoLocal[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [copiadoId, setCopiadoId] = useState<number | null>(null);
  const [descargandoZipId, setDescargandoZipId] = useState<number | null>(null);
  const [equipoVisorEditando, setEquipoVisorEditando] = useState<EquipoLocal | null>(null);
  const { confirmar } = useDialog();

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
    const ok = await confirmar({
      titulo: "Eliminar equipo local",
      mensaje: `¿Eliminar "${equipo.nombre}"? El equipo local dejará de poder autenticarse.`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
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

  async function descargarZip(equipo: EquipoLocal) {
    setDescargandoZipId(equipo.id);
    try {
      await descargarEquipoLocalZip(token, equipo.id);
    } catch {
      setError("No se pudo descargar el archivo del programa equipo_local.");
    } finally {
      setDescargandoZipId(null);
    }
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Cada PC dedicado en sitio que corre <code>equipo_local</code> necesita un registro acá. Lo más
          simple: botón <strong>&quot;+ Nuevo equipo&quot;</strong> → en su fila, botón{" "}
          <strong>&quot;Descargar equipo_local (.zip)&quot;</strong> (ya trae el <code>.env</code> completo,
          con la conexión al backend y el <code>api_key</code> de ese equipo — no hay que editar nada) →
          descomprimirlo en el PC de la planta → doble clic en <code>instalar.bat</code> (Windows) o correr{" "}
          <code>./instalar.sh</code> (Linux/Mac) — ese instalador deja todo corriendo solo, sin necesidad de
          saber de líneas de comando.
        </p>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => setMostrarFormulario(true)}
            className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white"
          >
            + Nuevo equipo
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-4 rounded-lg border border-corp-blue/30 bg-corp-blue-light px-4 py-3 text-sm text-corp-navy">
        <p className="font-semibold">📹 Cámaras en vivo y grabaciones</p>
        <p className="mt-1 text-corp-muted">
          Cada equipo local levanta su propia página para ver las cámaras en tiempo real y revisar/eliminar
          grabaciones por fecha — se abre desde un navegador <strong>en la misma red de la planta</strong>{" "}
          (no desde acá, para no subir video a internet), en:
        </p>
        <p className="mt-2 rounded-md bg-white px-3 py-2 font-mono text-xs text-corp-navy">
          http://guardia-camaras.local:8090
        </p>
        <p className="mt-1 text-xs text-corp-muted">
          Nombre fijo en la red (funciona directo en Mac/Linux; en Windows hace falta instalar &quot;Bonjour
          Print Services&quot; una vez, o usar el nombre del PC en la red en su lugar — ej.{" "}
          <code>http://NOMBRE-DEL-PC:8090</code>). Si nada de eso funciona, la IP directa siempre sirve — se
          consulta en el PC del equipo local con <code>ipconfig</code> (Windows) o <code>ip addr</code> (Linux).
        </p>
      </div>

      <div className="mt-6 overflow-x-auto rounded-xl border border-corp-border bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-corp-border bg-corp-blue-light text-xs uppercase text-corp-muted">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">API key</th>
              <th className="px-4 py-3">Conexión</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Visor web</th>
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
                      className="text-xs font-medium text-corp-gold hover:underline"
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
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => setEquipoVisorEditando(equipo)}
                    title="Usuario/contraseña del visor web local (http://guardia-camaras.local:8090)"
                    className={`rounded-full px-2 py-0.5 text-xs font-medium transition hover:underline ${
                      equipo.visor_usuario ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {equipo.visor_usuario ? "Con contraseña" : "Sin autenticar"}
                  </button>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => descargarZip(equipo)}
                      disabled={descargandoZipId === equipo.id}
                      className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy hover:border-corp-blue disabled:opacity-60"
                    >
                      {descargandoZipId === equipo.id ? "Descargando…" : "Descargar equipo_local (.zip)"}
                    </button>
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

      {equipoVisorEditando && (
        <FormularioAccesoVisor
          token={token}
          equipo={equipoVisorEditando}
          onCerrar={() => setEquipoVisorEditando(null)}
          onGuardado={() => {
            setEquipoVisorEditando(null);
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
              className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:opacity-60"
            >
              {enviando ? "Creando…" : "Crear equipo"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function FormularioAccesoVisor({
  token,
  equipo,
  onCerrar,
  onGuardado,
}: {
  token: string;
  equipo: EquipoLocal;
  onCerrar: () => void;
  onGuardado: () => void;
}) {
  const [usuario, setUsuario] = useState(equipo.visor_usuario);
  const [password, setPassword] = useState(equipo.visor_password);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (usuario.trim() && !password.trim()) {
      setError("Si pones un usuario, también hace falta una contraseña.");
      return;
    }
    setEnviando(true);
    try {
      await actualizarEquipoLocal(token, equipo.id, {
        visor_usuario: usuario.trim(),
        visor_password: usuario.trim() ? password : "",
      });
      onGuardado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el acceso del visor.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">Acceso al visor web — {equipo.nombre}</h2>
        <p className="mt-1 text-sm text-corp-muted">
          Usuario y contraseña para entrar a <code>http://guardia-camaras.local:8090</code> desde la red de
          planta. Déjalos vacíos para que el visor quede sin autenticación — cualquiera en esa red podrá
          verlo y configurarlo.
        </p>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <Campo label="Usuario">
            <input
              autoFocus
              value={usuario}
              onChange={(event) => setUsuario(event.target.value)}
              placeholder="Vacío = sin autenticación"
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>

          <Campo label="Contraseña">
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Vacío = sin autenticación"
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

          <p className="text-xs text-corp-muted">
            Al guardar, vuelve a descargar el <code>equipo_local (.zip)</code> de este equipo e instálalo de
            nuevo para que tome el usuario/contraseña nuevos.
          </p>

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
              className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:opacity-60"
            >
              {enviando ? "Guardando…" : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EnviarAccesoVisitantes({ token }: { token: string }) {
  const [correos, setCorreos] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<{ enviados: number; errores: number; venceEn: string | null } | null>(
    null
  );

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setResultado(null);
    const lista = correos
      .split(/[,\n]/)
      .map((c) => c.trim())
      .filter(Boolean);
    if (lista.length === 0) {
      setError("Escribe al menos un correo.");
      return;
    }
    setEnviando(true);
    try {
      const respuesta = await enviarAccesoVisitantes(token, lista);
      setResultado({ enviados: respuesta.enviados, errores: respuesta.errores.length, venceEn: respuesta.vence_en });
      if (respuesta.errores.length === 0) setCorreos("");
      if (respuesta.errores.length > 0) {
        setError(respuesta.errores.map((e) => `${e.correo}: ${e.detail}`).join(" — "));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar el acceso.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="max-w-xl">
      <p className="text-sm text-corp-muted">
        Manda por correo (usando la configuración de Brevo de la pestaña &quot;Brevo (correo)&quot;) el link
        del dashboard y el usuario/contraseña de la cuenta compartida de <strong>Visitante/Auditor</strong> —
        la misma para todas las visitas y auditorías a planta, pensada solo para tomar el curso de
        Capacitación.
      </p>
      <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        La contraseña es válida por <strong>máximo 24 horas</strong> desde que se genera. Si vuelves a usar
        este formulario dentro de esas 24 horas, se reenvía la misma contraseña (para mandar el acceso en
        varias tandas durante el día sin invalidar a los destinatarios anteriores); pasadas las 24 horas, el
        siguiente envío genera una nueva y arranca de nuevo el plazo. Cada correo indica la hora exacta hasta
        la que es válida.
      </div>

      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <Campo label="Correos de los destinatarios">
          <textarea
            required
            rows={4}
            value={correos}
            onChange={(event) => setCorreos(event.target.value)}
            placeholder={"visita1@empresa.com\nauditor@empresa.com"}
            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
        </Campo>
        <p className="text-xs text-corp-muted">Uno por línea, o separados por coma.</p>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {resultado && resultado.errores === 0 && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
            Acceso enviado a {resultado.enviados} destinatario{resultado.enviados === 1 ? "" : "s"}.
            {resultado.venceEn && (
              <>
                {" "}
                Válido hasta el{" "}
                {new Date(resultado.venceEn).toLocaleString("es-CO", {
                  dateStyle: "short",
                  timeStyle: "short",
                })}
                .
              </>
            )}
          </div>
        )}

        <button
          type="submit"
          disabled={enviando}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {enviando ? "Enviando…" : "Enviar acceso"}
        </button>
      </form>
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
