"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import AppShell from "@/components/AppShell";
import type { SeccionId } from "@/components/Sidebar";
import AlertasView from "@/components/views/AlertasView";
import AutorizacionIngresoView from "@/components/views/AutorizacionIngresoView";
import AyudaView from "@/components/views/AyudaView";
import CamarasView from "@/components/views/CamarasView";
import CapacitacionView from "@/components/views/CapacitacionView";
import ContratistasView from "@/components/views/ContratistasView";
import DeclaracionMetodoView from "@/components/views/DeclaracionMetodoView";
import FuncionariosView from "@/components/views/FuncionariosView";
import IndicadoresContratistasView from "@/components/views/IndicadoresContratistasView";
import NotificacionesView from "@/components/views/NotificacionesView";
import SistemaView from "@/components/views/SistemaView";
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
  notificaciones: "Notificaciones",
  contratistas: "Contratistas",
  "declaracion-metodo": "Declaración de Método",
  "autorizacion-ingreso": "Autorización de Ingreso",
  capacitacion: "Capacitación",
  funcionarios: "Funcionarios firmantes",
  "indicadores-contratistas": "Indicadores",
  sistema: "Sistema",
  usuarios: "Gestión de usuarios",
  ayuda: "Ayuda",
};

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardContent />
    </Suspense>
  );
}

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [token, setToken] = useState<string | null>(null);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [seccion, setSeccion] = useState<SeccionId>("tablero");

  // "?ir=<seccion>" — a dónde abrir al tocar una notificación push (con la
  // app cerrada), igual que hace clic en la campanita adentro de la app.
  const irInicial = searchParams.get("ir");

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
        if (irInicial && irInicial in TITULOS) {
          setSeccion(irInicial as SeccionId);
        } else if (data.rol === "contratista") {
          setSeccion("declaracion-metodo");
        }
      })
      .catch(() => {
        borrarSesion();
        router.replace("/login");
      });
  }, [router, irInicial]);

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
      token={token}
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
      {seccion === "notificaciones" && <NotificacionesView token={token} rol={usuario.rol} />}
      {seccion === "contratistas" && <ContratistasView token={token} rol={usuario.rol} />}
      {seccion === "declaracion-metodo" && <DeclaracionMetodoView token={token} rol={usuario.rol} />}
      {seccion === "autorizacion-ingreso" && <AutorizacionIngresoView token={token} rol={usuario.rol} />}
      {seccion === "capacitacion" && <CapacitacionView token={token} rol={usuario.rol} />}
      {seccion === "funcionarios" && <FuncionariosView token={token} rol={usuario.rol} />}
      {seccion === "indicadores-contratistas" && <IndicadoresContratistasView token={token} />}
      {seccion === "sistema" && usuario.rol === "administrador" && <SistemaView token={token} />}
      {seccion === "usuarios" && usuario.rol === "administrador" && (
        <UsuariosView token={token} usuarioActualId={usuario.id} />
      )}
      {seccion === "ayuda" && <AyudaView rol={usuario.rol} />}
    </AppShell>
  );
}
