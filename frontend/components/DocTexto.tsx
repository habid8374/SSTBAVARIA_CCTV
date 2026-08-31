import type { ReactNode } from "react";

/** Helpers de tipografía compartidos entre documentos largos dentro de la app
 * (Ayuda, Política de Privacidad) — mismo estilo, sin duplicar las clases. */

export function P({ children }: { children: ReactNode }) {
  return <p className="text-sm leading-relaxed text-corp-navy">{children}</p>;
}

export function Sub({ children }: { children: ReactNode }) {
  return <h3 className="mt-5 text-sm font-semibold uppercase tracking-wide text-corp-muted">{children}</h3>;
}

export function Ul({ children }: { children: ReactNode }) {
  return <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-corp-navy">{children}</ul>;
}

export function Ol({ children }: { children: ReactNode }) {
  return <ol className="list-decimal space-y-1.5 pl-5 text-sm leading-relaxed text-corp-navy">{children}</ol>;
}

export function Mono({ children }: { children: ReactNode }) {
  return <code className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs text-corp-navy">{children}</code>;
}

export function Nota({ children, tipo = "info" }: { children: ReactNode; tipo?: "info" | "aviso" }) {
  return (
    <div
      className={`rounded-lg border px-4 py-3 text-sm leading-relaxed ${
        tipo === "aviso"
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-corp-blue/30 bg-corp-blue-light text-corp-navy"
      }`}
    >
      {children}
    </div>
  );
}
