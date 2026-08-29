"use client";

import { useEffect, useState } from "react";

import PoligonoOverlay from "@/components/PoligonoOverlay";
import { listarCamarasDashboard, type CamaraDashboard } from "@/lib/api";

export default function CamarasView({ token }: { token: string }) {
  const [camaras, setCamaras] = useState<CamaraDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listarCamarasDashboard(token)
      .then(setCamaras)
      .catch(() => setError("No se pudo cargar la lista de cámaras."));
  }, [token]);

  return (
    <div>
      <p className="text-sm text-corp-muted">
        Último evento reportado por cámara, con la zona restringida dibujada encima.
      </p>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {camaras?.length === 0 && (
        <p className="mt-6 text-sm text-corp-muted">
          Todavía no hay cámaras registradas — cárgalas desde el admin de Django.
        </p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2 xl:grid-cols-3">
        {camaras?.map((camara) => (
          <TarjetaCamara key={camara.id} camara={camara} />
        ))}
      </div>
    </div>
  );
}

function TarjetaCamara({ camara }: { camara: CamaraDashboard }) {
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
    </div>
  );
}
