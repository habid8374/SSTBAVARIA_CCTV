"use client";

import { useState, type FormEvent } from "react";

import { ApiError, crearRegla } from "@/lib/api";

export const DIAS = ["L", "M", "X", "J", "V", "S", "D"];

export default function FormularioRegla({
  token,
  zonaId,
  onCerrar,
  onCreada,
}: {
  token: string;
  zonaId: number;
  onCerrar: () => void;
  onCreada: () => void;
}) {
  const [horaInicio, setHoraInicio] = useState("22:00");
  const [horaFin, setHoraFin] = useState("06:00");
  const [dias, setDias] = useState<number[]>([0, 1, 2, 3, 4]);
  const [canal, setCanal] = useState<"whatsapp" | "correo">("whatsapp");
  const [destinatario, setDestinatario] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  function alternarDia(dia: number) {
    setDias((prev) => (prev.includes(dia) ? prev.filter((d) => d !== dia) : [...prev, dia].sort()));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await crearRegla(token, {
        zona: zonaId,
        nombre: "",
        hora_inicio: horaInicio,
        hora_fin: horaFin,
        dias_semana: dias,
        canal_notificacion: canal,
        destinatario,
      });
      onCreada();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la regla.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border border-corp-border bg-zinc-50 p-3">
      <div className="flex flex-wrap gap-3">
        <div>
          <label className="text-xs font-medium text-corp-navy">Desde</label>
          <input
            type="time"
            required
            value={horaInicio}
            onChange={(e) => setHoraInicio(e.target.value)}
            className="mt-1 block rounded-md border border-corp-border px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-corp-navy">Hasta</label>
          <input
            type="time"
            required
            value={horaFin}
            onChange={(e) => setHoraFin(e.target.value)}
            className="mt-1 block rounded-md border border-corp-border px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-corp-navy">Canal</label>
          <select
            value={canal}
            onChange={(e) => setCanal(e.target.value as "whatsapp" | "correo")}
            className="mt-1 block rounded-md border border-corp-border px-2 py-1 text-sm"
          >
            <option value="whatsapp">WhatsApp</option>
            <option value="correo">Correo</option>
          </select>
        </div>
        <div className="min-w-[10rem] flex-1">
          <label className="text-xs font-medium text-corp-navy">Destinatario</label>
          <input
            required
            value={destinatario}
            onChange={(e) => setDestinatario(e.target.value)}
            placeholder="+57... o correo@empresa.com"
            className="mt-1 block w-full rounded-md border border-corp-border px-2 py-1 text-sm"
          />
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-corp-navy">Días</label>
        <div className="mt-1 flex gap-1.5">
          {DIAS.map((letra, i) => (
            <button
              key={i}
              type="button"
              onClick={() => alternarDia(i)}
              className={`h-7 w-7 rounded-full text-xs font-semibold transition ${
                dias.includes(i) ? "bg-corp-blue text-white" : "bg-white text-corp-muted ring-1 ring-corp-border"
              }`}
            >
              {letra}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCerrar} className="rounded-md px-3 py-1.5 text-xs text-corp-muted">
          Cancelar
        </button>
        <button
          type="submit"
          disabled={enviando}
          className="rounded-md bg-corp-blue px-3 py-1.5 text-xs font-semibold text-white hover:bg-corp-navy disabled:opacity-60"
        >
          {enviando ? "Guardando…" : "Guardar regla"}
        </button>
      </div>
    </form>
  );
}
