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
import { ApiError, logout as apiLogout, obtenerPerfil, type Usuario } from "@/lib/api";
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
  const [errorCarga, setErrorCarga] = useState(false);

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
        if (data.rol === "visitante") {
          // Único módulo al que este rol tiene acceso (ver Sidebar.tsx y
          // core.middleware.RestringirVisitanteMiddleware) — nunca desvía a
          // otra sección, ni siquiera con un "?ir=" viejo de una notificación.
          setSeccion("capacitacion");
        } else if (irInicial && irInicial in TITULOS) {
          setSeccion(irInicial as SeccionId);
        } else if (data.rol === "contratista") {
          setSeccion("declaracion-metodo");
        }
      })
      .catch((err) => {
        // Solo un token rechazado cierra la sesión. Un fallo de red (incluida
        // la petición que cancela el navegador al recargar) no debe sacar al
        // usuario: antes borraba la sesión y cada recarga rápida o reinicio
        // del backend dejaba a todos en el login.
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          borrarSesion();
          router.replace("/login");
        } else {
          setErrorCarga(true);
        }
      });
  }, [router, irInicial]);

  const handleLogout = useCallback(() => {
    if (token) {
      apiLogout(token).catch(() => {});
    }
    borrarSesion();
    router.replace("/login");
  }, [token, router]);

  if (errorCarga) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 px-4 text-center">
        <p className="text-sm text-corp-navy">No se pudo conectar con el servidor.</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-black transition hover:bg-corp-navy hover:text-white"
        >
          Reintentar
        </button>
      </div>
    );
  }

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
      {seccion === "sistema" && usuario.rol === "administrador" && (
        <SistemaView token={token} esSuperusuario={usuario.es_superusuario} />
      )}
      {seccion === "usuarios" && usuario.rol === "administrador" && (
        <UsuariosView token={token} usuarioActualId={usuario.id} />
      )}
      {seccion === "ayuda" && <AyudaView rol={usuario.rol} />}
    </AppShell>
  );
}
