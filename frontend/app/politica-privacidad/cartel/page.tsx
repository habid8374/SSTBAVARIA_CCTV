"use client";

import Link from "next/link";

export const dynamic = "force-static";

export default function CartelVideovigilanciaPage() {
  return (
    <div className="min-h-screen bg-zinc-100 py-10 print:bg-white print:py-0">
      <div className="mx-auto mb-6 flex max-w-[210mm] items-center justify-between px-4 print:hidden">
        <Link href="/politica-privacidad" className="text-sm font-medium text-corp-blue hover:underline">
          ← Volver a la política de privacidad
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy"
        >
          Imprimir cartel
        </button>
      </div>

      <div className="mx-auto flex min-h-[297mm] w-full max-w-[210mm] flex-col items-center justify-center gap-8 border border-corp-border bg-white px-12 py-16 text-center shadow-lg print:min-h-0 print:border-0 print:shadow-none">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo-lockup-light.png" alt="SST Bavaria" className="h-20 w-auto" />

        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-corp-navy text-white">
          <svg viewBox="0 0 24 24" className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        </div>

        <h1 className="text-4xl font-bold leading-tight text-corp-navy">
          ZONA VIGILADA
          <br />
          CON CÁMARAS DE VIDEOVIGILANCIA
          <br />E INTELIGENCIA ARTIFICIAL
        </h1>

        <p className="max-w-md text-base leading-relaxed text-corp-navy">
          Esta área cuenta con cámaras que analizan imágenes en tiempo real con fines de{" "}
          <strong>seguridad y salud en el trabajo</strong> (por ejemplo, verificar el uso de elementos de
          protección personal o el ingreso a zonas restringidas).
        </p>

        <p className="max-w-md text-sm leading-relaxed text-corp-muted">
          El video se procesa localmente, dentro de la planta. Solo se conservan imágenes puntuales
          (snapshots) cuando el sistema detecta una condición de riesgo — no se transmite ni almacena video
          continuo fuera de las instalaciones.
        </p>

        <div className="w-full max-w-md rounded-lg border border-corp-border bg-zinc-50 px-6 py-4 text-sm text-corp-navy">
          <p className="font-semibold">Responsable del tratamiento:</p>
          <p className="mt-1 text-corp-muted">[Razón social de la empresa] — NIT [NIT]</p>
          <p className="mt-3 font-semibold">Más información y ejercicio de tus derechos:</p>
          <p className="mt-1 text-corp-muted">/politica-privacidad — [correo de contacto]</p>
        </div>

        <p className="text-xs text-corp-muted">Ley 1581 de 2012 — Protección de datos personales (Habeas Data)</p>
      </div>

      <p className="mx-auto mt-4 max-w-[210mm] px-4 text-center text-xs text-amber-700 print:hidden">
        Borrador para imprimir: completa los datos de la empresa (NIT, razón social, correo de contacto)
        antes de colocarlo en planta.
      </p>
    </div>
  );
}
