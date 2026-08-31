"use client";

import { createContext, useCallback, useContext, useState, type FormEvent, type ReactNode } from "react";

type OpcionesConfirmar = {
  titulo?: string;
  mensaje: string;
  textoConfirmar?: string;
  textoCancelar?: string;
  /** Estilo rojo para acciones destructivas (eliminar) — igual que el resto de la app. */
  peligroso?: boolean;
};

type OpcionesPedirTexto = {
  titulo: string;
  mensaje?: string;
  placeholder?: string;
  textoConfirmar?: string;
  textoCancelar?: string;
  /** Si es false, no deja confirmar con el campo vacío. Por defecto true (ej. observaciones opcionales). */
  opcional?: boolean;
};

type EstadoDialogo =
  | { tipo: "confirmar"; opciones: OpcionesConfirmar; resolver: (valor: boolean) => void }
  | { tipo: "texto"; opciones: OpcionesPedirTexto; resolver: (valor: string | null) => void };

type DialogContextValor = {
  confirmar: (opciones: OpcionesConfirmar) => Promise<boolean>;
  pedirTexto: (opciones: OpcionesPedirTexto) => Promise<string | null>;
};

const DialogContext = createContext<DialogContextValor | null>(null);

/** Reemplazo de window.confirm()/window.prompt() con un modal propio del
 * sistema — los diálogos nativos del navegador rompen la estética de la app. */
export function useDialog() {
  const contexto = useContext(DialogContext);
  if (!contexto) throw new Error("useDialog debe usarse dentro de <DialogProvider>.");
  return contexto;
}

export default function DialogProvider({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<EstadoDialogo | null>(null);
  const [valorTexto, setValorTexto] = useState("");

  const confirmar = useCallback((opciones: OpcionesConfirmar) => {
    return new Promise<boolean>((resolver) => {
      setEstado({ tipo: "confirmar", opciones, resolver });
    });
  }, []);

  const pedirTexto = useCallback((opciones: OpcionesPedirTexto) => {
    setValorTexto("");
    return new Promise<string | null>((resolver) => {
      setEstado({ tipo: "texto", opciones, resolver });
    });
  }, []);

  function cerrar(valor: boolean | string | null) {
    if (!estado) return;
    if (estado.tipo === "confirmar") {
      estado.resolver(valor as boolean);
    } else {
      estado.resolver(valor as string | null);
    }
    setEstado(null);
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!estado || estado.tipo !== "texto") return;
    if (!estado.opciones.opcional && !valorTexto.trim()) return;
    cerrar(valorTexto);
  }

  return (
    <DialogContext.Provider value={{ confirmar, pedirTexto }}>
      {children}
      {estado && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 px-4"
          onClick={() => cerrar(estado.tipo === "confirmar" ? false : null)}
        >
          <div
            className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-corp-navy">{estado.opciones.titulo}</h2>

            {estado.tipo === "confirmar" ? (
              <p className="mt-2 text-sm text-corp-muted">{estado.opciones.mensaje}</p>
            ) : (
              <form onSubmit={handleSubmit}>
                {estado.opciones.mensaje && (
                  <p className="mt-1 text-sm text-corp-muted">{estado.opciones.mensaje}</p>
                )}
                <textarea
                  autoFocus
                  rows={3}
                  value={valorTexto}
                  onChange={(event) => setValorTexto(event.target.value)}
                  placeholder={estado.opciones.placeholder}
                  className="mt-3 w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
                />
              </form>
            )}

            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => cerrar(estado.tipo === "confirmar" ? false : null)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-corp-muted hover:bg-zinc-100"
              >
                {estado.opciones.textoCancelar ?? "Cancelar"}
              </button>
              <button
                type="button"
                onClick={() => {
                  if (estado.tipo === "texto") {
                    if (!estado.opciones.opcional && !valorTexto.trim()) return;
                    cerrar(valorTexto);
                  } else {
                    cerrar(true);
                  }
                }}
                className={`rounded-lg px-4 py-2 text-sm font-semibold text-white transition ${
                  estado.tipo === "confirmar" && estado.opciones.peligroso
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-corp-blue hover:bg-corp-navy"
                }`}
              >
                {estado.opciones.textoConfirmar ?? "Confirmar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </DialogContext.Provider>
  );
}
