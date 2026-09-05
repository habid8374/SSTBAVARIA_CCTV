"use client";

import { useEffect, useMemo, useState, type FormEvent, type MouseEvent as ReactMouseEvent } from "react";

import FormularioRegla, { DIAS } from "@/components/FormularioRegla";
import PoligonoOverlay from "@/components/PoligonoOverlay";
import CirculoOverlay from "@/components/CirculoOverlay";
import { useDialog } from "@/components/DialogProvider";
import {
  ApiError,
  actualizarRegla,
  actualizarZona,
  calibrarCamara,
  crearZona,
  eliminarRegla,
  eliminarZona,
  listarCamarasDashboard,
  subirSnapshotReferencia,
  type CamaraDashboard,
  type Rol,
  type TipoZona,
  type ZonaDashboard,
} from "@/lib/api";

export default function ZonasView({ token, rol }: { token: string; rol: Rol | null }) {
  const esAdmin = rol === "administrador";
  const [camaras, setCamaras] = useState<CamaraDashboard[] | null>(null);
  const [camaraId, setCamaraId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dimensiones, setDimensiones] = useState<{ w: number; h: number } | null>(null);
  const [dibujando, setDibujando] = useState(false);
  const [tipoDraft, setTipoDraft] = useState<TipoZona>("poligono");
  const [puntosDraft, setPuntosDraft] = useState<number[][]>([]);
  const [radioMetrosDraft, setRadioMetrosDraft] = useState("");
  const [nombreZona, setNombreZona] = useState("");
  const [guardandoZona, setGuardandoZona] = useState(false);
  const [subiendo, setSubiendo] = useState(false);
  const [calibrando, setCalibrando] = useState(false);
  const [puntosCalibracion, setPuntosCalibracion] = useState<number[][]>([]);
  const [distanciaCalibracion, setDistanciaCalibracion] = useState("");
  const [guardandoCalibracion, setGuardandoCalibracion] = useState(false);

  function cargar() {
    listarCamarasDashboard(token)
      .then((datos) => {
        setCamaras(datos);
        setCamaraId((actual) => actual ?? datos[0]?.id ?? null);
      })
      .catch(() => setError("No se pudo cargar la lista de cámaras."));
  }

  useEffect(cargar, [token]);

  const camara = useMemo(() => camaras?.find((c) => c.id === camaraId) ?? null, [camaras, camaraId]);

  function cancelarDibujo() {
    setDibujando(false);
    setTipoDraft("poligono");
    setPuntosDraft([]);
    setRadioMetrosDraft("");
    setNombreZona("");
  }

  function cancelarCalibracion() {
    setCalibrando(false);
    setPuntosCalibracion([]);
    setDistanciaCalibracion("");
  }

  function coordenadasDesdeClick(event: ReactMouseEvent<HTMLDivElement>): [number, number] | null {
    if (!dimensiones) return null;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Math.round(((event.clientX - rect.left) / rect.width) * dimensiones.w);
    const y = Math.round(((event.clientY - rect.top) / rect.height) * dimensiones.h);
    return [x, y];
  }

  function handleClickImagen(event: ReactMouseEvent<HTMLDivElement>) {
    if (calibrando) {
      const punto = coordenadasDesdeClick(event);
      if (!punto) return;
      setPuntosCalibracion((prev) => (prev.length >= 2 ? [punto] : [...prev, punto]));
      return;
    }
    if (!dibujando) return;
    const punto = coordenadasDesdeClick(event);
    if (!punto) return;
    if (tipoDraft === "punto_radio") {
      setPuntosDraft([punto]); // un solo punto: cada clic reemplaza el centro marcado
    } else {
      setPuntosDraft((prev) => [...prev, punto]);
    }
  }

  async function guardarZona(event: FormEvent) {
    event.preventDefault();
    if (!camara) return;
    if (tipoDraft === "poligono" && puntosDraft.length < 3) return;
    if (tipoDraft === "punto_radio" && (puntosDraft.length === 0 || !radioMetrosDraft)) return;
    setGuardandoZona(true);
    try {
      if (tipoDraft === "punto_radio") {
        const [centro_x, centro_y] = puntosDraft[0];
        await crearZona(token, {
          camara: camara.id,
          nombre: nombreZona,
          tipo: "punto_radio",
          centro_x,
          centro_y,
          radio_metros: Number(radioMetrosDraft),
        });
      } else {
        await crearZona(token, { camara: camara.id, nombre: nombreZona, tipo: "poligono", poligono: puntosDraft });
      }
      cancelarDibujo();
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la zona.");
    } finally {
      setGuardandoZona(false);
    }
  }

  async function guardarCalibracion(event: FormEvent) {
    event.preventDefault();
    if (!camara || puntosCalibracion.length < 2 || !distanciaCalibracion) return;
    setGuardandoCalibracion(true);
    try {
      await calibrarCamara(token, camara.id, {
        punto1: puntosCalibracion[0] as [number, number],
        punto2: puntosCalibracion[1] as [number, number],
        distancia_metros: Number(distanciaCalibracion),
      });
      cancelarCalibracion();
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la calibración.");
    } finally {
      setGuardandoCalibracion(false);
    }
  }

  async function subirReferencia(archivo: File) {
    if (!camara) return;
    setSubiendo(true);
    try {
      await subirSnapshotReferencia(token, camara.id, archivo);
      cargar();
    } catch {
      setError("No se pudo subir el snapshot de referencia.");
    } finally {
      setSubiendo(false);
    }
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">
          Dibuja el polígono de la zona restringida sobre el encuadre fijo de la cámara, o marca un punto y un
          radio en metros reales (ej. &quot;3m alrededor de la estiba&quot;) para zonas que se deban recalcular
          solas si ese punto se mueve.
        </p>
        {camaras && camaras.length > 0 && (
          <select
            value={camaraId ?? ""}
            onChange={(e) => {
              setCamaraId(Number(e.target.value));
              cancelarDibujo();
              cancelarCalibracion();
              setDimensiones(null);
            }}
            className="rounded-md border border-corp-border px-3 py-1.5 text-sm"
          >
            {camaras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {camaras && camaras.length === 0 && (
        <p className="mt-6 text-sm text-corp-muted">
          Todavía no hay cámaras registradas — créalas primero en la sección{" "}
          <span className="font-medium text-corp-navy">Cámaras</span> del menú.
        </p>
      )}

      {camara && (
        <div className="mt-6 rounded-xl border border-corp-border bg-white p-5 shadow-sm">
          {!camara.snapshot_referencia ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-corp-border bg-zinc-50 py-16 text-center">
              <p className="text-sm text-corp-muted">Esta cámara todavía no tiene un snapshot de referencia.</p>
              {esAdmin && (
                <label className="cursor-pointer rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy">
                  {subiendo ? "Subiendo…" : "Subir snapshot"}
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    disabled={subiendo}
                    onChange={(e) => {
                      const archivo = e.target.files?.[0];
                      if (archivo) subirReferencia(archivo);
                    }}
                  />
                </label>
              )}
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-semibold text-corp-navy">
                  {calibrando
                    ? `Haz clic para marcar 2 puntos de una distancia real conocida (${puntosCalibracion.length}/2)`
                    : dibujando && tipoDraft === "punto_radio"
                      ? puntosDraft.length === 0
                        ? "Haz clic para marcar el centro (ej. la estiba)"
                        : "Centro marcado — puedes hacer clic de nuevo para moverlo"
                      : dibujando
                        ? `Haz clic para agregar puntos (${puntosDraft.length} agregados, mínimo 3)`
                        : "Encuadre de referencia"}
                </p>
                {esAdmin && !dibujando && !calibrando && (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setCalibrando(true)}
                      className="rounded-lg border border-corp-border px-3 py-1.5 text-xs font-semibold text-corp-navy hover:border-corp-blue"
                    >
                      {camara.px_por_metro ? "Recalibrar cámara" : "Calibrar cámara"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setDibujando(true)}
                      className="rounded-lg bg-corp-blue px-3 py-1.5 text-xs font-semibold text-white hover:bg-corp-navy"
                    >
                      + Nueva zona
                    </button>
                  </div>
                )}
                {dibujando && (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setPuntosDraft((prev) => prev.slice(0, -1))}
                      disabled={puntosDraft.length === 0}
                      className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy disabled:opacity-40"
                    >
                      Deshacer punto
                    </button>
                    <button
                      type="button"
                      onClick={cancelarDibujo}
                      className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy"
                    >
                      Cancelar
                    </button>
                  </div>
                )}
                {calibrando && (
                  <button
                    type="button"
                    onClick={cancelarCalibracion}
                    className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy"
                  >
                    Cancelar
                  </button>
                )}
              </div>

              <p className="mt-1 text-xs text-corp-muted">
                {camara.px_por_metro
                  ? `Cámara calibrada — 1 metro real ≈ ${camara.px_por_metro.toFixed(1)}px en esta foto.`
                  : "Cámara sin calibrar — necesario solo para zonas tipo Punto y radio."}
              </p>

              {esAdmin && dibujando && puntosDraft.length === 0 && (
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={() => setTipoDraft("poligono")}
                    className={`rounded-md border px-2.5 py-1 text-xs font-medium ${
                      tipoDraft === "poligono"
                        ? "border-corp-blue bg-corp-blue-light text-corp-blue"
                        : "border-corp-border text-corp-navy"
                    }`}
                  >
                    Polígono
                  </button>
                  <button
                    type="button"
                    onClick={() => setTipoDraft("punto_radio")}
                    className={`rounded-md border px-2.5 py-1 text-xs font-medium ${
                      tipoDraft === "punto_radio"
                        ? "border-corp-blue bg-corp-blue-light text-corp-blue"
                        : "border-corp-border text-corp-navy"
                    }`}
                  >
                    Punto y radio
                  </button>
                </div>
              )}

              <div
                data-testid="lienzo-zona"
                className={`relative mt-3 overflow-hidden rounded-lg bg-zinc-100 ${
                  dibujando || calibrando ? "cursor-crosshair" : ""
                }`}
                onClick={handleClickImagen}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={camara.snapshot_referencia}
                  alt={`Encuadre de ${camara.nombre}`}
                  className="block w-full select-none"
                  draggable={false}
                  onLoad={(e) =>
                    setDimensiones({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })
                  }
                />
                {dimensiones &&
                  camara.zonas.map((zona) =>
                    zona.tipo === "punto_radio" ? (
                      zona.centro_x !== null && zona.centro_y !== null && camara.px_por_metro ? (
                        <CirculoOverlay
                          key={zona.id}
                          centro={[zona.centro_x, zona.centro_y]}
                          radioPx={(zona.radio_metros ?? 0) * camara.px_por_metro}
                          naturalWidth={dimensiones.w}
                          naturalHeight={dimensiones.h}
                          color="#3b82f6"
                        />
                      ) : null
                    ) : (
                      <PoligonoOverlay
                        key={zona.id}
                        puntos={zona.poligono}
                        naturalWidth={dimensiones.w}
                        naturalHeight={dimensiones.h}
                        color="#3b82f6"
                      />
                    )
                  )}
                {dimensiones && tipoDraft === "punto_radio" && puntosDraft.length > 0 && (
                  <CirculoOverlay
                    centro={[puntosDraft[0][0], puntosDraft[0][1]]}
                    radioPx={
                      camara.px_por_metro && radioMetrosDraft
                        ? Number(radioMetrosDraft) * camara.px_por_metro
                        : dimensiones.w * 0.008
                    }
                    naturalWidth={dimensiones.w}
                    naturalHeight={dimensiones.h}
                    color="#eab308"
                  />
                )}
                {dimensiones && tipoDraft === "poligono" && puntosDraft.length > 0 && (
                  <PoligonoOverlay
                    puntos={puntosDraft}
                    naturalWidth={dimensiones.w}
                    naturalHeight={dimensiones.h}
                    color="#eab308"
                  />
                )}
                {dimensiones && puntosCalibracion.length === 1 && (
                  <CirculoOverlay
                    centro={[puntosCalibracion[0][0], puntosCalibracion[0][1]]}
                    radioPx={dimensiones.w * 0.008}
                    naturalWidth={dimensiones.w}
                    naturalHeight={dimensiones.h}
                    color="#10b981"
                    dashed={false}
                  />
                )}
                {dimensiones && puntosCalibracion.length === 2 && (
                  <PoligonoOverlay
                    puntos={puntosCalibracion}
                    naturalWidth={dimensiones.w}
                    naturalHeight={dimensiones.h}
                    color="#10b981"
                    dashed={false}
                  />
                )}
              </div>

              {dibujando &&
                ((tipoDraft === "poligono" && puntosDraft.length >= 3) ||
                  (tipoDraft === "punto_radio" && puntosDraft.length === 1)) && (
                  <form onSubmit={guardarZona} className="mt-4 space-y-3">
                    {tipoDraft === "punto_radio" && !camara.px_por_metro && (
                      <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                        Esta cámara no está calibrada — esta zona se guardará, pero nunca disparará una alerta
                        hasta que calibres la cámara (botón &quot;Calibrar cámara&quot; arriba).
                      </p>
                    )}
                    <div className="flex flex-wrap items-end gap-3">
                      <div className="flex-1 space-y-1.5">
                        <label className="text-sm font-medium text-corp-navy">Nombre de la zona</label>
                        <input
                          required
                          value={nombreZona}
                          onChange={(e) => setNombreZona(e.target.value)}
                          placeholder="Ej. Muelle de recepción"
                          className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
                        />
                      </div>
                      {tipoDraft === "punto_radio" && (
                        <div className="w-32 space-y-1.5">
                          <label className="text-sm font-medium text-corp-navy">Radio (metros)</label>
                          <input
                            required
                            type="number"
                            min="0.1"
                            step="0.1"
                            value={radioMetrosDraft}
                            onChange={(e) => setRadioMetrosDraft(e.target.value)}
                            placeholder="3"
                            className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
                          />
                        </div>
                      )}
                      <button
                        type="submit"
                        disabled={guardandoZona}
                        className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white hover:bg-corp-navy disabled:opacity-60"
                      >
                        {guardandoZona ? "Guardando…" : "Guardar zona"}
                      </button>
                    </div>
                  </form>
                )}

              {calibrando && puntosCalibracion.length === 2 && (
                <form onSubmit={guardarCalibracion} className="mt-4 flex flex-wrap items-end gap-3">
                  <div className="w-48 space-y-1.5">
                    <label className="text-sm font-medium text-corp-navy">
                      Distancia real entre esos 2 puntos (metros)
                    </label>
                    <input
                      required
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={distanciaCalibracion}
                      onChange={(e) => setDistanciaCalibracion(e.target.value)}
                      placeholder="Ej. 1.2"
                      className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={guardandoCalibracion}
                    className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white hover:bg-corp-navy disabled:opacity-60"
                  >
                    {guardandoCalibracion ? "Guardando…" : "Guardar calibración"}
                  </button>
                </form>
              )}

              {esAdmin && (
                <label className="mt-3 inline-block cursor-pointer text-xs font-medium text-corp-blue hover:underline">
                  {subiendo ? "Subiendo…" : "Reemplazar snapshot de referencia"}
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    disabled={subiendo}
                    onChange={(e) => {
                      const archivo = e.target.files?.[0];
                      if (archivo) subirReferencia(archivo);
                    }}
                  />
                </label>
              )}
            </>
          )}
        </div>
      )}

      {camara && camara.zonas.length > 0 && (
        <div className="mt-6 space-y-4">
          {camara.zonas.map((zona) => (
            <ZonaCard key={zona.id} zona={zona} token={token} esAdmin={esAdmin} onCambio={cargar} />
          ))}
        </div>
      )}
    </div>
  );
}

function ZonaCard({
  zona,
  token,
  esAdmin,
  onCambio,
}: {
  zona: ZonaDashboard;
  token: string;
  esAdmin: boolean;
  onCambio: () => void;
}) {
  const [expandida, setExpandida] = useState(false);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { confirmar } = useDialog();

  async function alternarActiva() {
    try {
      await actualizarZona(token, zona.id, { activa: !zona.activa });
      onCambio();
    } catch {
      setError("No se pudo actualizar la zona.");
    }
  }

  async function eliminar() {
    const ok = await confirmar({
      titulo: "Eliminar zona",
      mensaje: `¿Eliminar la zona "${zona.nombre}"? También se eliminan sus reglas.`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
    try {
      await eliminarZona(token, zona.id);
      onCambio();
    } catch {
      setError("No se pudo eliminar la zona.");
    }
  }

  async function eliminarReglaClick(reglaId: number) {
    try {
      await eliminarRegla(token, reglaId);
      onCambio();
    } catch {
      setError("No se pudo eliminar la regla.");
    }
  }

  async function alternarReglaActiva(reglaId: number, activa: boolean) {
    try {
      await actualizarRegla(token, reglaId, { activa: !activa });
      onCambio();
    } catch {
      setError("No se pudo actualizar la regla.");
    }
  }

  return (
    <div className="rounded-xl border border-corp-border bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <button
            type="button"
            onClick={() => setExpandida((v) => !v)}
            className="text-sm font-semibold text-corp-navy hover:underline"
          >
            {zona.nombre}
          </button>
          <span
            className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${
              zona.activa ? "bg-green-100 text-green-700" : "bg-zinc-100 text-zinc-500"
            }`}
          >
            {zona.activa ? "Activa" : "Inactiva"}
          </span>
          {zona.tipo === "punto_radio" && (
            <span className="ml-2 rounded-full bg-corp-blue-light px-2 py-0.5 text-xs font-medium text-corp-blue">
              Punto y radio · {zona.radio_metros}m
            </span>
          )}
          <span className="ml-2 text-xs text-corp-muted">
            {zona.reglas.length} regla{zona.reglas.length === 1 ? "" : "s"}
          </span>
        </div>
        {esAdmin && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={alternarActiva}
              className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy hover:border-corp-blue"
            >
              {zona.activa ? "Desactivar" : "Activar"}
            </button>
            <button
              type="button"
              onClick={eliminar}
              className="rounded-md border border-red-200 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
            >
              Eliminar zona
            </button>
          </div>
        )}
      </div>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      {expandida && (
        <div className="mt-4 space-y-3 border-t border-corp-border pt-4">
          {zona.reglas.map((regla) => (
            <div
              key={regla.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-zinc-50 px-3 py-2 text-sm"
            >
              <div>
                <span className="font-medium text-corp-navy">
                  {regla.hora_inicio.slice(0, 5)}–{regla.hora_fin.slice(0, 5)}
                </span>
                <span className="ml-2 text-corp-muted">
                  {regla.dias_semana.map((d) => DIAS[d]).join(" ")} · {regla.canal_notificacion} ·{" "}
                  {regla.destinatario}
                </span>
              </div>
              {esAdmin && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => alternarReglaActiva(regla.id, regla.activa)}
                    className="rounded-md border border-corp-border px-2 py-0.5 text-xs text-corp-navy"
                  >
                    {regla.activa ? "Desactivar" : "Activar"}
                  </button>
                  <button
                    type="button"
                    onClick={() => eliminarReglaClick(regla.id)}
                    className="rounded-md border border-red-200 px-2 py-0.5 text-xs text-red-600"
                  >
                    Eliminar
                  </button>
                </div>
              )}
            </div>
          ))}
          {zona.reglas.length === 0 && (
            <p className="text-sm text-corp-muted">Sin reglas de horario — nunca dispara alerta.</p>
          )}

          {esAdmin &&
            (mostrarForm ? (
              <FormularioRegla
                token={token}
                zonaId={zona.id}
                onCerrar={() => setMostrarForm(false)}
                onCreada={() => {
                  setMostrarForm(false);
                  onCambio();
                }}
              />
            ) : (
              <button
                type="button"
                onClick={() => setMostrarForm(true)}
                className="text-xs font-medium text-corp-blue hover:underline"
              >
                + Agregar regla de horario
              </button>
            ))}
        </div>
      )}
    </div>
  );
}

