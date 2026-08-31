import type { ComponentType } from "react";

import { API_URL, type Rol } from "@/lib/api";
import {
  IconAlerta,
  IconCamara,
  IconChevronLeft,
  IconContratista,
  IconDeclaracionMetodo,
  IconLogout,
  IconNotificacion,
  IconPanelAdmin,
  IconResumen,
  IconSistema,
  IconUsuarios,
  IconZona,
} from "./icons";

export type SeccionId =
  | "tablero"
  | "camaras"
  | "zonas"
  | "alertas"
  | "notificaciones"
  | "contratistas"
  | "declaracion-metodo"
  | "sistema"
  | "usuarios";

type Item = {
  id: SeccionId;
  label: string;
  icon: ComponentType<{ className?: string }>;
  adminOnly?: boolean;
};

const ITEMS: Item[] = [
  { id: "tablero", label: "Tablero", icon: IconResumen },
  { id: "camaras", label: "Cámaras", icon: IconCamara },
  { id: "zonas", label: "Zonas y horarios", icon: IconZona },
  { id: "alertas", label: "Alertas", icon: IconAlerta },
  { id: "notificaciones", label: "Notificaciones", icon: IconNotificacion },
  { id: "contratistas", label: "Contratistas", icon: IconContratista },
  { id: "declaracion-metodo", label: "Declaración de Método", icon: IconDeclaracionMetodo },
  { id: "sistema", label: "Sistema", icon: IconSistema, adminOnly: true },
  { id: "usuarios", label: "Usuarios", icon: IconUsuarios, adminOnly: true },
];

// Transición compartida por toda etiqueta de texto que aparece/desaparece
// junto con el colapso del riel — mismo timing que el ancho del <aside>.
const TEXTO_COLAPSABLE = "overflow-hidden whitespace-nowrap transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]";

type Props = {
  seccionActiva: SeccionId;
  onSeleccionar: (id: SeccionId) => void;
  rol: Rol | null;
  colapsado: boolean;
  onToggleColapsado: () => void;
  onCerrarSesion: () => void;
  nombre: string;
  className?: string;
};

export default function Sidebar({
  seccionActiva,
  onSeleccionar,
  rol,
  colapsado,
  onToggleColapsado,
  onCerrarSesion,
  nombre,
  className = "",
}: Props) {
  const items = ITEMS.filter((item) => !item.adminOnly || rol === "administrador");

  return (
    <aside
      className={`flex h-full flex-col bg-corp-navy text-white transition-[width] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        colapsado ? "w-[76px]" : "w-64"
      } ${className}`}
    >
      <div className="flex items-center gap-3 border-b border-white/10 px-4 py-4">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo-sstbavaria.png" alt="SST Bavaria" className="h-9 w-9 shrink-0 rounded-lg" />
        <div className={`min-w-0 ${TEXTO_COLAPSABLE} ${colapsado ? "max-w-0 opacity-0" : "max-w-[160px] opacity-100"}`}>
          <p className="truncate text-sm font-semibold">SST BAVARIA</p>
          <p className="truncate text-xs text-white/60">Cámaras IA</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
        {items.map((item) => {
          const Icon = item.icon;
          const activo = item.id === seccionActiva;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSeleccionar(item.id)}
              title={colapsado ? item.label : undefined}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                activo ? "bg-corp-blue text-white" : "text-white/80 hover:bg-white/10"
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span
                className={`text-left ${TEXTO_COLAPSABLE} ${colapsado ? "max-w-0 opacity-0" : "max-w-[9rem] opacity-100"}`}
              >
                {item.label}
              </span>
            </button>
          );
        })}
      </nav>

      <div className="border-t border-white/10 px-2 py-3">
        <button
          type="button"
          onClick={onToggleColapsado}
          className="hidden w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-white/70 hover:bg-white/10 md:flex"
        >
          <IconChevronLeft className={`h-4 w-4 shrink-0 transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${colapsado ? "rotate-180" : ""}`} />
          <span className={`${TEXTO_COLAPSABLE} ${colapsado ? "max-w-0 opacity-0" : "max-w-[9rem] opacity-100"}`}>
            Colapsar menú
          </span>
        </button>

        <div className="mt-1 flex items-center gap-3 rounded-lg px-3 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold">
            {nombre.slice(0, 2).toUpperCase()}
          </div>
          <span className={`${TEXTO_COLAPSABLE} ${colapsado ? "max-w-0 opacity-0" : "max-w-[9rem] opacity-100"}`}>
            {nombre}
          </span>
        </div>

        {rol === "administrador" && (
          <a
            href={`${API_URL}/admin/`}
            target="_blank"
            rel="noopener noreferrer"
            title={colapsado ? "Admin de Django" : undefined}
            className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-white/70 hover:bg-white/10"
          >
            <IconPanelAdmin className="h-5 w-5 shrink-0" />
            <span className={`${TEXTO_COLAPSABLE} ${colapsado ? "max-w-0 opacity-0" : "max-w-[9rem] opacity-100"}`}>
              Admin de Django
            </span>
          </a>
        )}

        <button
          type="button"
          onClick={onCerrarSesion}
          className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-white/70 hover:bg-white/10"
        >
          <IconLogout className="h-5 w-5 shrink-0" />
          <span className={`${TEXTO_COLAPSABLE} ${colapsado ? "max-w-0 opacity-0" : "max-w-[9rem] opacity-100"}`}>
            Cerrar sesión
          </span>
        </button>
      </div>
    </aside>
  );
}
