import Link from "next/link";

import PoliticaPrivacidadContenido from "@/components/PoliticaPrivacidadContenido";

export const metadata = {
  title: "Política de privacidad — SST Bavaria Cámaras IA",
};

export default function PoliticaPrivacidadPage() {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-corp-border px-6 py-5 sm:px-10">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-lockup-light.png" alt="SST Bavaria" className="h-10 w-auto" />
          <Link href="/login" className="text-sm font-medium text-corp-blue hover:underline">
            ← Volver al inicio de sesión
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-10 sm:px-10">
        <h1 className="mb-1 text-2xl font-semibold text-corp-navy">
          Política de tratamiento de datos personales
        </h1>
        <p className="mb-2 text-sm text-corp-muted">
          Sistema SST Bavaria Cámaras IA — Ley 1581 de 2012 (Habeas Data) y Decreto 1377 de 2013.
        </p>
        <p className="mb-6 text-sm">
          <Link href="/politica-privacidad/cartel" target="_blank" className="font-medium text-corp-blue hover:underline">
            Descargar/imprimir cartel de aviso de videovigilancia →
          </Link>
        </p>
        <PoliticaPrivacidadContenido />
      </main>
    </div>
  );
}
