"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { IconChevronLeft } from "@/components/icons";
import { API_URL, obtenerPerfil } from "@/lib/api";
import { leerSesion } from "@/lib/auth";

/** Admin de Django embebido en un <iframe> propio del dashboard (mismo
 * origen que la PWA) — así el link "Admin de Django" del sidebar no saca a
 * quien lo abre desde la app instalada al navegador del celular, que es lo
 * que pasa siempre que se navega directo a un origen distinto (api.*) desde
 * una PWA en modo standalone. El backend habilita esto solo para nuestros
 * propios orígenes (ver core.middleware.PermitirIframeAdminMiddleware),
 * nunca para cualquier sitio. */
export default function AdminDjangoPage() {
  const router = useRouter();
  const [autorizado, setAutorizado] = useState(false);

  useEffect(() => {
    const sesion = leerSesion();
    if (!sesion) {
      router.replace("/login");
      return;
    }
    obtenerPerfil(sesion.token)
      .then((data) => {
        if (data.rol !== "administrador") {
          router.replace("/dashboard");
          return;
        }
        setAutorizado(true);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  if (!autorizado) {
    return null;
  }

  return (
    <div className="flex h-dvh flex-col bg-white">
      <div className="flex shrink-0 items-center gap-2 border-b border-corp-border bg-corp-navy px-3 py-2.5 text-white">
        <button
          type="button"
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm font-medium hover:bg-white/10"
        >
          <IconChevronLeft className="h-5 w-5" />
          Volver
        </button>
        <span className="text-sm font-semibold">Admin de Django</span>
      </div>
      <iframe
        src={`${API_URL}/admin/`}
        title="Admin de Django"
        className="w-full flex-1 border-0"
      />
    </div>
  );
}
