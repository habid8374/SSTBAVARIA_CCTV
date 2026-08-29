"use client";

import { useEffect, useState } from "react";

import { obtenerResumen, type Resumen } from "@/lib/api";

export default function ResumenView({ token }: { token: string }) {
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    obtenerResumen(token)
      .then(setResumen)
      .catch(() => setError("No se pudo cargar el resumen del backend."));
  }, [token]);

  return (
    <div>
      <p className="text-sm text-corp-muted">
        Estado general del sistema de videovigilancia.
      </p>

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {resumen && (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Tarjeta titulo="Cámaras activas" valor={resumen.camaras_activas} />
          <Tarjeta titulo="Eventos nuevos" valor={resumen.eventos_nuevos} />
          <Tarjeta titulo="Alertas hoy" valor={resumen.alertas_hoy} />
        </div>
      )}
    </div>
  );
}

function Tarjeta({ titulo, valor }: { titulo: string; valor: number }) {
  return (
    <div className="rounded-xl border border-corp-border bg-white p-5 shadow-sm">
      <p className="text-sm text-corp-muted">{titulo}</p>
      <p className="mt-2 text-3xl font-semibold text-corp-navy">{valor}</p>
    </div>
  );
}
