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
  listarCamarasDashboard,
  listarEquiposLocales,
  listarTiposEventoIA,
  obtenerConfiguracionIA,
  obtenerConfiguracionNotificaciones,
  obtenerConsumoIA,
  reiniciarConsumoIA,
  type CamaraDashboard,
  type ConfiguracionIA,
  type ConsumoIA,
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

      {config?.proveedor === "claude" && (
        <ConsumoClaude key={config.tope_usd} token={token} tope={config.tope_usd} onTopeGuardado={setConfig} />
      )}

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
        <h3 className="text-sm font-semibold text-corp-navy">Alertas de IA por cámara</h3>
        <p className="mt-1 text-sm text-corp-muted">
          Cada alerta es una instrucción en lenguaje natural que la IA revisa solo en las cámaras elegidas — ej.
          cámara 1: &quot;Persona sin casco de seguridad puesto en la cabeza&quot;; cámara 2: &quot;Persona a más
          de 3 metros del compresor&quot;. Entre más detallada, mejor detecta. Cuando la IA encuentra una, el
          evento queda como alerta y llega una notificación.
        </p>
        <CatalogoEventosIA token={token} />
      </div>
    </div>
  );
}

// Colores de estado reservados (ver skill de visualización): siempre van con
// ícono + texto, nunca solos.
const ESTADO_CONSUMO = {
  normal: { color: "#0ca30c", icono: "●", texto: "Consumo normal" },
  aviso: { color: "#fab219", icono: "▲", texto: "Cerca del tope (80% o más)" },
  tope: { color: "#d03b3b", icono: "■", texto: "Tope alcanzado — la clasificación con IA está pausada" },
} as const;

function usd(valor: number, decimales = 2) {
  return `USD ${valor.toLocaleString("es-CO", { minimumFractionDigits: decimales, maximumFractionDigits: decimales })}`;
}

function ConsumoClaude({
  token,
  tope,
  onTopeGuardado,
}: {
  token: string;
  tope: string | null;
  onTopeGuardado: (config: ConfiguracionIA) => void;
}) {
  const [consumo, setConsumo] = useState<ConsumoIA | null>(null);
  const [nuevoTope, setNuevoTope] = useState(tope ?? "");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar } = useDialog();

  function cargar() {
    obtenerConsumoIA(token)
      .then(setConsumo)
      .catch(() => setError("No se pudo cargar el consumo de IA."));
  }

  useEffect(cargar, [token]);

  async function guardarTope(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setGuardando(true);
    try {
      onTopeGuardado(await actualizarConfiguracionIA(token, { tope_usd: nuevoTope.trim() }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el tope.");
    } finally {
      setGuardando(false);
    }
  }

  async function reiniciar() {
    const ok = await confirmar({
      titulo: "Reiniciar el contador de consumo",
      mensaje:
        "El gasto vuelve a contar desde cero a partir de ahora (por ejemplo, después de recargar créditos en Anthropic). " +
        "El historial de llamadas no se borra.",
      textoConfirmar: "Reiniciar",
    });
    if (!ok) return;
    try {
      await reiniciarConsumoIA(token);
      cargar();
    } catch {
      setError("No se pudo reiniciar el contador.");
    }
  }

  if (!consumo) {
    return error ? (
      <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
    ) : null;
  }

  const estado = consumo.tope_alcanzado ? ESTADO_CONSUMO.tope : consumo.porcentaje >= 80 ? ESTADO_CONSUMO.aviso : ESTADO_CONSUMO.normal;
  const relleno = Math.min(consumo.porcentaje, 100);

  return (
    <section className="mt-6 rounded-xl border border-corp-border bg-white p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-corp-navy">Consumo de Claude</h3>
          <p className="mt-0.5 text-xs text-corp-muted">
            {consumo.consumo_desde
              ? `Contando desde el ${new Date(consumo.consumo_desde).toLocaleString("es-CO")}`
              : "Contando desde la primera llamada"}
          </p>
        </div>
        <button
          type="button"
          onClick={reiniciar}
          className="self-start rounded-lg border border-corp-border px-3 py-1.5 text-xs font-medium text-corp-navy transition hover:bg-slate-50"
        >
          Reiniciar contador
        </button>
      </div>

      <p className="mt-4 text-2xl font-semibold text-corp-navy">
        {usd(consumo.gastado_usd)} <span className="text-base font-normal text-corp-muted">de {usd(consumo.tope_usd)}</span>
      </p>
      <div
        role="meter"
        aria-label="Gasto de IA frente al tope"
        aria-valuemin={0}
        aria-valuemax={consumo.tope_usd}
        aria-valuenow={consumo.gastado_usd}
        title={`${usd(consumo.gastado_usd, 4)} de ${usd(consumo.tope_usd)} (${consumo.porcentaje.toFixed(1)}%)`}
        className="relative mt-2 h-3 w-full rounded bg-slate-100"
      >
        <div className="h-full rounded" style={{ width: `${relleno}%`, backgroundColor: estado.color }} />
        <div className="absolute inset-y-0 w-0.5 bg-slate-400" style={{ left: "80%" }} aria-hidden />
      </div>
      <div className="mt-1.5 flex items-center justify-between text-xs">
        <span className="font-medium text-corp-navy">
          <span style={{ color: estado.color }} aria-hidden>
            {estado.icono}
          </span>{" "}
          {estado.texto}
        </span>
        <span className="text-corp-muted">{consumo.porcentaje.toFixed(1)}% · marca en 80%</span>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Cifra etiqueta="Restante" valor={usd(consumo.restante_usd)} />
        <Cifra etiqueta="Llamadas" valor={consumo.llamadas.toLocaleString("es-CO")} />
        <Cifra
          etiqueta="Costo promedio"
          valor={consumo.costo_promedio_usd === null ? "—" : usd(consumo.costo_promedio_usd, 4)}
        />
        <Cifra
          etiqueta="Clasificaciones restantes (aprox.)"
          valor={consumo.llamadas_restantes_estimadas === null ? "—" : consumo.llamadas_restantes_estimadas.toLocaleString("es-CO")}
        />
      </dl>
      <p className="mt-2 text-xs text-corp-muted">
        Tokens del periodo: {consumo.tokens_entrada.toLocaleString("es-CO")} de entrada ·{" "}
        {consumo.tokens_salida.toLocaleString("es-CO")} de salida.
      </p>

      <div className="mt-5">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-corp-muted">Reparto por cámara</h4>
        <p className="mt-1 text-xs text-corp-muted">
          {consumo.camaras_con_ia === 0
            ? "Ninguna cámara tiene alertas de IA todavía — el tope se reparte entre las que las tengan."
            : `El tope se reparte por igual entre las ${consumo.camaras_con_ia} cámaras con alertas de IA: ${usd(consumo.cuota_por_camara_usd)} cada una. Una cámara que agota su cuota deja de usar la IA; las demás siguen. Se recalcula sola al agregar cámaras.`}
        </p>
        {consumo.por_camara.length > 0 && (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="text-xs text-corp-muted">
                <tr className="border-b border-corp-border">
                  <th className="py-2 pr-4 font-medium">Cámara</th>
                  <th className="w-1/3 py-2 pr-4 font-medium">Gasto frente a su cuota</th>
                  <th className="py-2 pr-4 text-right font-medium">Gastado</th>
                  <th className="py-2 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {consumo.por_camara.map((fila) => {
                  const estadoCamara = fila.agotada
                    ? { ...ESTADO_CONSUMO.tope, texto: "Cuota agotada" }
                    : fila.porcentaje >= 80
                      ? { ...ESTADO_CONSUMO.aviso, texto: "Cerca de la cuota" }
                      : ESTADO_CONSUMO.normal;
                  return (
                    <tr key={fila.camara} className="border-b border-corp-border/60 last:border-0">
                      <td className="py-2 pr-4 text-corp-navy">{fila.nombre}</td>
                      <td className="py-2 pr-4">
                        <div
                          role="meter"
                          aria-label={`Gasto de IA de ${fila.nombre} frente a su cuota`}
                          aria-valuemin={0}
                          aria-valuemax={fila.cuota_usd}
                          aria-valuenow={fila.gastado_usd}
                          title={`${usd(fila.gastado_usd, 4)} de ${usd(fila.cuota_usd)} (${fila.porcentaje.toFixed(1)}%) · ${fila.llamadas} llamadas`}
                          className="h-2 w-full rounded bg-slate-100"
                        >
                          <div
                            className="h-full rounded"
                            style={{ width: `${Math.min(fila.porcentaje, 100)}%`, backgroundColor: estadoCamara.color }}
                          />
                        </div>
                      </td>
                      <td className="whitespace-nowrap py-2 pr-4 text-right tabular-nums text-corp-navy">
                        {usd(fila.gastado_usd)} <span className="text-corp-muted">de {usd(fila.cuota_usd)}</span>
                      </td>
                      <td className="whitespace-nowrap py-2 text-xs text-corp-navy">
                        <span style={{ color: estadoCamara.color }} aria-hidden>
                          {estadoCamara.icono}
                        </span>{" "}
                        {estadoCamara.texto}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <form onSubmit={guardarTope} className="mt-5 flex flex-wrap items-end gap-2">
        <Campo label="Tope de gasto (USD)">
          <input
            type="number"
            min="0"
            step="0.01"
            value={nuevoTope}
            onChange={(event) => setNuevoTope(event.target.value)}
            className="block w-36 rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          />
        </Campo>
        <button
          type="submit"
          disabled={guardando || nuevoTope.trim() === "" || nuevoTope === tope}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:opacity-60"
        >
          {guardando ? "Guardando…" : "Guardar tope"}
        </button>
      </form>
      {error && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}
      <p className="mt-3 text-xs text-corp-muted">
        Al llegar al tope el sistema deja de llamar a Claude y avisa con una notificación (también al 80%). Es una
        estimación con la tarifa pública de cada modelo: configure además un límite de gasto en la consola de
        Anthropic como respaldo.
      </p>

      {consumo.ultimas.length > 0 && (
        <div className="mt-5 overflow-x-auto">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-corp-muted">Últimas llamadas</h4>
          <table className="mt-2 w-full text-left text-sm">
            <thead className="text-xs text-corp-muted">
              <tr className="border-b border-corp-border">
                <th className="py-2 pr-4 font-medium">Fecha</th>
                <th className="py-2 pr-4 font-medium">Modelo</th>
                <th className="py-2 pr-4 text-right font-medium">Tokens entrada</th>
                <th className="py-2 pr-4 text-right font-medium">Tokens salida</th>
                <th className="py-2 text-right font-medium">Costo</th>
              </tr>
            </thead>
            <tbody>
              {consumo.ultimas.map((llamada) => (
                <tr key={llamada.id} className="border-b border-corp-border/60 last:border-0">
                  <td className="whitespace-nowrap py-2 pr-4 text-corp-navy">
                    {new Date(llamada.creado_en).toLocaleString("es-CO")}
                  </td>
                  <td className="py-2 pr-4 text-corp-muted">{llamada.modelo}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{llamada.tokens_entrada.toLocaleString("es-CO")}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{llamada.tokens_salida.toLocaleString("es-CO")}</td>
                  <td className="py-2 text-right tabular-nums">{usd(Number(llamada.costo_usd), 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Cifra({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <dt className="text-xs text-corp-muted">{etiqueta}</dt>
      <dd className="mt-0.5 text-sm font-semibold text-corp-navy tabular-nums">{valor}</dd>
    </div>
  );
}

function CatalogoEventosIA({ token }: { token: string }) {
  const [tipos, setTipos] = useState<TipoEventoIA[] | null>(null);
  const [camaras, setCamaras] = useState<CamaraDashboard[]>([]);
  const [filtroCamara, setFiltroCamara] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formulario, setFormulario] = useState<{ tipo: TipoEventoIA | null } | null>(null);
  const { confirmar } = useDialog();

  function cargar() {
    listarTiposEventoIA(token)
      .then(setTipos)
      .catch(() => setError("No se pudo cargar el catálogo de alertas."));
  }

  useEffect(cargar, [token]);
  useEffect(() => {
    listarCamarasDashboard(token)
      .then(setCamaras)
      .catch(() => setError("No se pudo cargar la lista de cámaras."));
  }, [token]);

  async function alternarActivo(tipo: TipoEventoIA) {
    try {
      await actualizarTipoEventoIA(token, tipo.id, { activo: !tipo.activo });
      cargar();
    } catch {
      setError("No se pudo actualizar la alerta.");
    }
  }

  async function eliminar(tipo: TipoEventoIA) {
    const ok = await confirmar({
      titulo: "Eliminar alerta",
      mensaje: `¿Eliminar "${tipo.nombre}"? La IA dejará de buscarla en todas sus cámaras.`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
    try {
      await eliminarTipoEventoIA(token, tipo.id);
      cargar();
    } catch {
      setError("No se pudo eliminar la alerta.");
    }
  }

  const colorSeveridad: Record<Severidad, string> = {
    alta: "bg-red-100 text-red-700",
    media: "bg-amber-100 text-amber-700",
    baja: "bg-zinc-100 text-zinc-600",
  };
  const nombreCamara = new Map(camaras.map((camara) => [camara.id, camara.nombre]));
  const visibles = tipos?.filter((tipo) => filtroCamara === null || tipo.camaras.includes(filtroCamara));

  return (
    <div>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-corp-navy">Ver alertas de</span>
          <select
            value={filtroCamara ?? ""}
            onChange={(event) => setFiltroCamara(event.target.value ? Number(event.target.value) : null)}
            className="block rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
          >
            <option value="">Todas las cámaras</option>
            {camaras.map((camara) => (
              <option key={camara.id} value={camara.id}>
                {camara.nombre}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => setFormulario({ tipo: null })}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white"
        >
          + Nueva alerta
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-4 overflow-x-auto rounded-xl border border-corp-border bg-white">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-corp-border bg-corp-blue-light text-xs uppercase text-corp-muted">
            <tr>
              <th className="px-4 py-3">Alerta</th>
              <th className="px-4 py-3">Qué revisa la IA</th>
              <th className="px-4 py-3">Cámaras</th>
              <th className="px-4 py-3">Severidad</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {visibles?.map((tipo) => (
              <tr key={tipo.id} className="border-b border-corp-border last:border-0">
                <td className="px-4 py-3 font-medium text-corp-navy">{tipo.nombre}</td>
                <td className="max-w-xs px-4 py-3 text-corp-muted">{tipo.descripcion}</td>
                <td className="px-4 py-3">
                  {tipo.camaras.length === 0 ? (
                    <span className="text-xs font-medium text-amber-700">Ninguna — no se revisa</span>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {tipo.camaras.map((id) => (
                        <span
                          key={id}
                          className="whitespace-nowrap rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-corp-navy"
                        >
                          {nombreCamara.get(id) ?? `Cámara ${id}`}
                        </span>
                      ))}
                    </div>
                  )}
                </td>
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
                    {tipo.activo ? "Activa" : "Inactiva"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setFormulario({ tipo })}
                      className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy hover:border-corp-blue"
                    >
                      Editar
                    </button>
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
        {visibles?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-corp-muted">
            {filtroCamara === null
              ? "Todavía no hay alertas configuradas."
              : "Esta cámara no tiene alertas de IA — no se le envía nada a la IA."}
          </p>
        )}
      </div>

      {formulario && (
        <FormularioTipoEvento
          token={token}
          tipo={formulario.tipo}
          camaras={camaras}
          camaraInicial={filtroCamara}
          onCerrar={() => setFormulario(null)}
          onGuardado={() => {
            setFormulario(null);
            cargar();
          }}
        />
      )}
    </div>
  );
}

function FormularioTipoEvento({
  token,
  tipo,
  camaras,
  camaraInicial,
  onCerrar,
  onGuardado,
}: {
  token: string;
  tipo: TipoEventoIA | null;
  camaras: CamaraDashboard[];
  camaraInicial: number | null;
  onCerrar: () => void;
  onGuardado: () => void;
}) {
  const [datos, setDatos] = useState<NuevoTipoEventoIA>(
    tipo
      ? { nombre: tipo.nombre, descripcion: tipo.descripcion, severidad: tipo.severidad, camaras: tipo.camaras }
      : { nombre: "", descripcion: "", severidad: "media", camaras: camaraInicial === null ? [] : [camaraInicial] }
  );
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  function alternarCamara(id: number) {
    setDatos({
      ...datos,
      camaras: datos.camaras.includes(id) ? datos.camaras.filter((c) => c !== id) : [...datos.camaras, id],
    });
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      if (tipo) {
        await actualizarTipoEventoIA(token, tipo.id, datos);
      } else {
        await crearTipoEventoIA(token, datos);
      }
      onGuardado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la alerta.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="max-h-[90dvh] w-full max-w-md overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">{tipo ? "Editar alerta" : "Nueva alerta de IA"}</h2>
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
          <Campo label="Qué debe revisar la IA">
            <textarea
              required
              rows={3}
              value={datos.descripcion}
              onChange={(event) => setDatos({ ...datos, descripcion: event.target.value })}
              placeholder="Persona sin casco de seguridad puesto en la cabeza"
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <fieldset className="space-y-1.5">
            <legend className="text-sm font-medium text-corp-navy">Cámaras donde aplica</legend>
            {camaras.length === 0 ? (
              <p className="text-sm text-amber-700">Primero registra una cámara en la sección Cámaras.</p>
            ) : (
              <div className="max-h-40 space-y-1 overflow-y-auto rounded-lg border border-corp-border p-2">
                {camaras.map((camara) => (
                  <label key={camara.id} className="flex items-center gap-2 rounded px-1 py-1 text-sm hover:bg-zinc-50">
                    <input
                      type="checkbox"
                      checked={datos.camaras.includes(camara.id)}
                      onChange={() => alternarCamara(camara.id)}
                      className="h-4 w-4 accent-corp-navy"
                    />
                    {camara.nombre}
                  </label>
                ))}
              </div>
            )}
          </fieldset>
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
              disabled={enviando || datos.camaras.length === 0}
              title={datos.camaras.length === 0 ? "Elige al menos una cámara" : undefined}
              className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white disabled:opacity-60"
            >
              {enviando ? "Guardando…" : tipo ? "Guardar cambios" : "Crear alerta"}
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
