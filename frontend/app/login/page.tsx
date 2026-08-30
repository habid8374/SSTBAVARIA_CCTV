"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { ApiError, login } from "@/lib/api";
import { guardarSesion } from "@/lib/auth";
import { IconCandado, IconUsuario } from "@/components/icons";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [recordarme, setRecordarme] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [avisoClave, setAvisoClave] = useState(false);
  const [cargando, setCargando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setCargando(true);
    try {
      const { token, usuario } = await login(username, password);
      guardarSesion({ token, nombre: usuario.nombre, rol: usuario.rol });
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("No se pudo conectar con el servidor. Intenta de nuevo.");
      }
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-white lg:flex-row">
      <PanelIlustracion />

      <div className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo-lockup-light.png" alt="SST Bavaria" className="mb-5 h-28 w-auto" />
            <h1 className="text-2xl font-semibold text-corp-navy">Iniciar sesión</h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="username" className="text-sm font-medium text-corp-navy">
                Usuario
              </label>
              <div className="relative">
                <IconUsuario className="pointer-events-none absolute left-3.5 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-corp-muted" />
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="usuario@sstbavaria.com"
                  className="w-full rounded-lg border border-corp-border py-2.5 pl-10 pr-3 text-sm text-corp-navy outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium text-corp-navy">
                Contraseña
              </label>
              <div className="relative">
                <IconCandado className="pointer-events-none absolute left-3.5 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-corp-muted" />
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-corp-border py-2.5 pl-10 pr-3 text-sm text-corp-navy outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <label className="flex items-center gap-2 text-corp-muted">
                <input
                  type="checkbox"
                  checked={recordarme}
                  onChange={(event) => setRecordarme(event.target.checked)}
                  className="h-3.5 w-3.5 rounded border-corp-border accent-corp-blue"
                />
                Recordarme
              </label>
              <button
                type="button"
                onClick={() => setAvisoClave(true)}
                className="font-medium text-corp-blue hover:underline"
              >
                ¿Olvidaste tu contraseña?
              </button>
            </div>

            {avisoClave && (
              <p className="rounded-lg border border-corp-border bg-corp-blue-light px-3 py-2 text-xs text-corp-navy">
                Contacta a tu administrador para restablecer tu contraseña.
              </p>
            )}

            {error && (
              <div
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={cargando}
              className="w-full rounded-lg bg-corp-blue py-2.5 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:cursor-not-allowed disabled:opacity-60"
            >
              {cargando ? "Verificando…" : "Entrar"}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-corp-muted">
            Acceso exclusivo para personal autorizado.
          </p>
        </div>
      </div>
    </div>
  );
}

function PanelIlustracion() {
  return (
    <div className="relative flex h-48 shrink-0 overflow-hidden bg-corp-navy sm:h-56 lg:h-auto lg:w-1/2">
      <video
        autoPlay
        loop
        muted
        playsInline
        poster="/login-poster.jpg"
        className="absolute inset-0 h-full w-full object-cover"
      >
        <source src="/login-animacion.mp4" type="video/mp4" />
      </video>

      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          background: "linear-gradient(190deg, rgba(11,31,58,0.15) 0%, rgba(6,15,33,0.85) 100%)",
        }}
      />

      <div className="relative z-10 flex w-full flex-col justify-end p-8 lg:p-12">
        <div className="hidden lg:block">
          <h2 className="text-2xl font-semibold leading-snug text-white">
            Videovigilancia con IA para tu planta
          </h2>
          <p className="mt-2 max-w-sm text-sm text-white/60">
            Detección automática de zonas restringidas por horario, con evidencia
            en tiempo real — las 24 horas, sin turnos de vigilancia manual.
          </p>
        </div>
      </div>
    </div>
  );
}
