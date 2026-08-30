"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import AppShell from "@/components/AppShell";
import type { SeccionId } from "@/components/Sidebar";
import AlertasView from "@/components/views/AlertasView";
import CamarasView from "@/components/views/CamarasView";
import TableroView from "@/components/views/TableroView";
import UsuariosView from "@/components/views/UsuariosView";
import ZonasView from "@/components/views/ZonasView";
import { logout as apiLogout, obtenerPerfil, type Usuario } from "@/lib/api";
import { borrarSesion, guardarSesion, leerSesion } from "@/lib/auth";

const TITULOS: Record<SeccionId, string> = {
  tablero: "Tablero",
  camaras: "Cámaras IA",
  zonas: "Zonas y horarios",
  alertas: "Alertas",
  usuarios: "Gestión de usuarios",
};

export default function DashboardPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [seccion, setSeccion] = useState<SeccionId>("tablero");

  useEffect(() => {
    const sesion = leerSesion();
    if (!sesion) {
      router.replace("/login");
      return;
    }

    obtenerPerfil(sesion.token)
      .then((data) => {
        guardarSesion({ token: sesion.token, nombre: data.nombre, rol: data.rol });
        setToken(sesion.token);
        setUsuario(data);
      })
      .catch(() => {
        borrarSesion();
        router.replace("/login");
      });
  }, [router]);

  const handleLogout = useCallback(() => {
    if (token) {
      apiLogout(token).catch(() => {});
    }
    borrarSesion();
    router.replace("/login");
  }, [token, router]);

  if (!token || !usuario) {
    return null;
  }

  return (
    <AppShell
      nombre={usuario.nombre}
      rol={usuario.rol}
      seccionActiva={seccion}
      onSeleccionar={setSeccion}
      onCerrarSesion={handleLogout}
      tituloSeccion={TITULOS[seccion]}
    >
      {seccion === "tablero" && <TableroView token={token} />}
      {seccion === "camaras" && <CamarasView token={token} rol={usuario.rol} />}
      {seccion === "zonas" && <ZonasView token={token} rol={usuario.rol} />}
      {seccion === "alertas" && <AlertasView token={token} />}
      {seccion === "usuarios" && usuario.rol === "administrador" && (
        <UsuariosView token={token} usuarioActualId={usuario.id} />
      )}
    </AppShell>
  );
}
