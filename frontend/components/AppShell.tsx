"use client";

import { useEffect, useState, type ReactNode } from "react";

import type { Rol } from "@/lib/api";
import { IconMenu } from "./icons";
import Sidebar, { type SeccionId } from "./Sidebar";

const COLAPSADO_KEY = "sstbavaria_sidebar_colapsado";

type Props = {
  nombre: string;
  rol: Rol | null;
  seccionActiva: SeccionId;
  onSeleccionar: (id: SeccionId) => void;
  onCerrarSesion: () => void;
  tituloSeccion: string;
  children: ReactNode;
};

export default function AppShell({
  nombre,
  rol,
  seccionActiva,
  onSeleccionar,
  onCerrarSesion,
  tituloSeccion,
  children,
}: Props) {
  const [colapsado, setColapsado] = useState(false);
  const [drawerAbierto, setDrawerAbierto] = useState(false);

  useEffect(() => {
    // localStorage no existe en el render de servidor; se lee una sola vez al montar.
    if (window.localStorage.getItem(COLAPSADO_KEY) === "1") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setColapsado(true);
    }
  }, []);

  function toggleColapsado() {
    setColapsado((previo) => {
      const siguiente = !previo;
      window.localStorage.setItem(COLAPSADO_KEY, siguiente ? "1" : "0");
      return siguiente;
    });
  }

  function seleccionar(id: SeccionId) {
    onSeleccionar(id);
    setDrawerAbierto(false);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar
        className="hidden md:flex"
        seccionActiva={seccionActiva}
        onSeleccionar={seleccionar}
        rol={rol}
        colapsado={colapsado}
        onToggleColapsado={toggleColapsado}
        onCerrarSesion={onCerrarSesion}
        nombre={nombre}
      />

      {drawerAbierto && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            aria-label="Cerrar menú"
            className="absolute inset-0 bg-black/50"
            onClick={() => setDrawerAbierto(false)}
          />
          <Sidebar
            className="absolute inset-y-0 left-0 z-50 shadow-2xl"
            seccionActiva={seccionActiva}
            onSeleccionar={seleccionar}
            rol={rol}
            colapsado={false}
            onToggleColapsado={toggleColapsado}
            onCerrarSesion={onCerrarSesion}
            nombre={nombre}
          />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-corp-border bg-white px-4 py-3 md:px-8">
          <button
            type="button"
            onClick={() => setDrawerAbierto(true)}
            className="rounded-lg p-2 text-corp-navy hover:bg-corp-blue-light md:hidden"
            aria-label="Abrir menú"
          >
            <IconMenu className="h-5 w-5" />
          </button>
          <h1 className="text-lg font-semibold text-corp-navy">{tituloSeccion}</h1>
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
