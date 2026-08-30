"use client";

import { useEffect, useMemo, useState } from "react";

import FormularioRegla, { DIAS } from "@/components/FormularioRegla";
import {
  actualizarRegla,
  eliminarRegla,
  listarCamarasDashboard,
  type CamaraDashboard,
  type ReglaAlerta,
  type Rol,
} from "@/lib/api";

type ReglaConContexto = ReglaAlerta & { camaraNombre: string; camaraId: number };

export default function ConfiguracionAlertasView({ token, rol }: { token: string; rol: Rol | null }) {
  const esAdmin = rol === "administrador";
  const [camaras, setCamaras] = useState<CamaraDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creando, setCreando] = useState(false);
  const [camaraNuevaId, setCamaraNuevaId] = useState<number | null>(null);
  const [zonaNuevaId, setZonaNuevaId] = useState<number | null>(null);

  function cargar() {
    listarCamarasDashboard(token)
      .then(setCamaras)
      .catch(() => setError("No se pudo cargar la configuración de alertas."));
  }

  useEffect(cargar, [token]);

  const reglas: ReglaConContexto[] = useMemo(() => {
    if (!camaras) return [];
    return camaras.flatMap((camara) =>
      camara.zonas.flatMap((zona) =>
        zona.reglas.map((regla) => ({ ...regla, camaraNombre: camara.nombre, camaraId: camara.id }))
      )
    );
  }, [camaras]);

  const camaraNueva = camaras?.find((c) => c.id === camaraNuevaId) ?? null;

  async function alternarActiva(regla: ReglaConContexto) {
    try {
      await actualizarRegla(token, regla.id, { activa: !regla.activa });
      cargar();
    } catch {
      setError("No se pudo actualizar la regla.");
    }
  }

  async function eliminar(regla: ReglaConContexto) {
    if (!window.confirm(`¿Eliminar esta regla de "${regla.zona_nombre}"?`)) return;
    try {
      await eliminarRegla(token, regla.id);
      cargar();
    } catch {
      setError("No se pudo eliminar la regla.");
    }
  }

  function cerrarCreacion() {
    setCreando(false);
    setCamaraNuevaId(null);
    setZonaNuevaId(null);
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Horario, canal y destinatario de cada zona restringida — a quién avisar y cuándo.
        </p>
        {esAdmin && !creando && (
          <button
            type="button"
            onClick={() => setCreando(true)}
            className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy"
          >
            + Nueva regla
          </button>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {creando && (
        <div className="mt-4 space-y-3 rounded-lg border border-corp-border bg-zinc-50 p-3">
          <div className="flex flex-wrap gap-3">
            <div>
              <label className="text-xs font-medium text-corp-navy">Cámara</label>
              <select
                value={camaraNuevaId ?? ""}
                onChange={(e) => {
                  setCamaraNuevaId(Number(e.target.value) || null);
                  setZonaNuevaId(null);
                }}
                className="mt-1 block rounded-md border border-corp-border px-2 py-1 text-sm"
              >
                <option value="">Selecciona una cámara…</option>
                {camaras?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-corp-navy">Zona</label>
              <select
                value={zonaNuevaId ?? ""}
                onChange={(e) => setZonaNuevaId(Number(e.target.value) || null)}
                disabled={!camaraNueva}
                className="mt-1 block rounded-md border border-corp-border px-2 py-1 text-sm disabled:opacity-50"
              >
                <option value="">Selecciona una zona…</option>
                {camaraNueva?.zonas.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.nombre}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {camaraNueva && camaraNueva.zonas.length === 0 && (
            <p className="text-xs text-corp-muted">
              Esa cámara todavía no tiene zonas dibujadas — créalas primero en &ldquo;Zonas y
              horarios&rdquo;.
            </p>
          )}

          {zonaNuevaId ? (
            <FormularioRegla
              token={token}
              zonaId={zonaNuevaId}
              onCerrar={cerrarCreacion}
              onCreada={() => {
                cerrarCreacion();
                cargar();
              }}
            />
          ) : (
            <div className="flex justify-end">
              <button type="button" onClick={cerrarCreacion} className="text-xs text-corp-muted hover:underline">
                Cancelar
              </button>
            </div>
          )}
        </div>
      )}

      <div className="mt-6 overflow-x-auto rounded-xl border border-corp-border bg-white">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-corp-border bg-corp-blue-light text-xs uppercase text-corp-muted">
            <tr>
              <th className="px-4 py-3">Cámara</th>
              <th className="px-4 py-3">Zona</th>
              <th className="px-4 py-3">Horario</th>
              <th className="px-4 py-3">Días</th>
              <th className="px-4 py-3">Canal</th>
              <th className="px-4 py-3">Destinatario</th>
              <th className="px-4 py-3">Estado</th>
              {esAdmin && <th className="px-4 py-3 text-right">Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {reglas.map((regla) => (
              <tr key={regla.id} className="border-b border-corp-border last:border-0">
                <td className="px-4 py-3 font-medium text-corp-navy">{regla.camaraNombre}</td>
                <td className="px-4 py-3 text-corp-muted">{regla.zona_nombre}</td>
                <td className="px-4 py-3 text-corp-muted">
                  {regla.hora_inicio.slice(0, 5)}–{regla.hora_fin.slice(0, 5)}
                </td>
                <td className="px-4 py-3 text-corp-muted">{regla.dias_semana.map((d) => DIAS[d]).join(" ")}</td>
                <td className="px-4 py-3 text-corp-muted capitalize">{regla.canal_notificacion}</td>
                <td className="px-4 py-3 text-corp-muted">{regla.destinatario}</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      regla.activa ? "bg-green-100 text-green-700" : "bg-zinc-100 text-zinc-500"
                    }`}
                  >
                    {regla.activa ? "Activa" : "Inactiva"}
                  </span>
                </td>
                {esAdmin && (
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => alternarActiva(regla)}
                        className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy hover:border-corp-blue"
                      >
                        {regla.activa ? "Desactivar" : "Activar"}
                      </button>
                      <button
                        type="button"
                        onClick={() => eliminar(regla)}
                        className="rounded-md border border-red-200 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                      >
                        Eliminar
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {camaras && reglas.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-corp-muted">
            Todavía no hay reglas de alerta configuradas.
          </p>
        )}
      </div>
    </div>
  );
}
