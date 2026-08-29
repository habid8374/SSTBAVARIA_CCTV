import type { Rol } from "./api";

const STORAGE_KEY = "sstbavaria_cctv_auth";

export type SesionGuardada = {
  token: string;
  nombre: string;
  rol: Rol | null;
};

export function guardarSesion(sesion: SesionGuardada) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sesion));
}

export function leerSesion(): SesionGuardada | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SesionGuardada;
  } catch {
    return null;
  }
}

export function borrarSesion() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}
