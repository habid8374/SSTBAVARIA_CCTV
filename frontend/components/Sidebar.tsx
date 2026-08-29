import type { ComponentType } from "react";

import type { Rol } from "@/lib/api";
import {
  IconAlerta,
  IconCamara,
  IconChevronLeft,
  IconLogout,
  IconResumen,
  IconUsuarios,
  IconZona,
} from "./icons";

export type SeccionId = "resumen" | "usuarios";

type Item = {
  id: SeccionId;
  label: string;
  icon: ComponentType<{ className?: string }>;
  adminOnly?: boolean;
  disponible?: boolean;
};

const ITEMS: Item[] = [
  { id: "resumen", label: "Resumen", icon: IconResumen, disponible: true },
  { id: "usuarios", label: "Usuarios", icon: IconUsuarios, adminOnly: true, disponible: true },
  { id: "camaras" as SeccionId, label: "Cámaras", icon: IconCamara, disponible: false },
  { id: "zonas" as SeccionId, label: "Zonas y horarios", icon: IconZona, disponible: false },
  { id: "alertas" as SeccionId, label: "Alertas", icon: IconAlerta, disponible: false },
];

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
      className={`flex h-full flex-col bg-corp-navy text-white transition-[width] duration-200 ${
        colapsado ? "w-[76px]" : "w-64"
      } ${className}`}
    >
      <div className="flex items-center gap-3 border-b border-white/10 px-4 py-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-corp-blue text-sm font-bold">
          SB
        </div>
        {!colapsado && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">SST BAVARIA</p>
            <p className="truncate text-xs text-white/60">Cámaras IA</p>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
        {items.map((item) => {
          const Icon = item.icon;
          const activo = item.id === seccionActiva;
          return (
            <button
              key={item.id}
              type="button"
              disabled={!item.disponible}
              onClick={() => item.disponible && onSeleccionar(item.id)}
              title={colapsado ? item.label : undefined}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                activo ? "bg-corp-blue text-white" : "text-white/80 hover:bg-white/10"
              } ${!item.disponible ? "cursor-not-allowed opacity-40" : ""}`}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!colapsado && <span className="flex-1 truncate text-left">{item.label}</span>}
              {!colapsado && !item.disponible && (
                <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
                  Pronto
                </span>
              )}
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
          <IconChevronLeft className={`h-4 w-4 transition-transform ${colapsado ? "rotate-180" : ""}`} />
          {!colapsado && <span>Colapsar menú</span>}
        </button>

        <div className="mt-1 flex items-center gap-3 rounded-lg px-3 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold">
            {nombre.slice(0, 2).toUpperCase()}
          </div>
          {!colapsado && <span className="truncate text-sm">{nombre}</span>}
        </div>

        <button
          type="button"
          onClick={onCerrarSesion}
          className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-white/70 hover:bg-white/10"
        >
          <IconLogout className="h-5 w-5 shrink-0" />
          {!colapsado && <span>Cerrar sesión</span>}
        </button>
      </div>
    </aside>
  );
}
