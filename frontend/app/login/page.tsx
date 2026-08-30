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
            <img src="/logo-sstbavaria.png" alt="SST Bavaria" className="mb-3 h-11 w-11 rounded-xl" />
            <h1 className="text-2xl font-semibold text-corp-navy">Iniciar sesión</h1>
            <p className="mt-1 text-sm text-corp-muted">SST Bavaria · Módulo de Cámaras IA</p>
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
    <div className="relative hidden h-56 shrink-0 overflow-hidden bg-corp-navy sm:flex lg:h-auto lg:w-1/2">
      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          background: "linear-gradient(160deg, var(--color-corp-navy) 0%, var(--color-corp-navy-deep) 100%)",
        }}
      />
      <div
        aria-hidden
        className="absolute inset-0 opacity-[0.15]"
        style={{
          backgroundImage: "radial-gradient(circle, #ffffff 1px, transparent 1px)",
          backgroundSize: "22px 22px",
        }}
      />
      <div
        aria-hidden
        className="absolute -left-20 -top-20 h-72 w-72 rounded-full opacity-30 blur-3xl"
        style={{ background: "var(--color-corp-blue)" }}
      />

      <div className="relative z-10 flex w-full flex-col justify-between p-8 lg:p-12">
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-sstbavaria.png" alt="SST Bavaria" className="h-9 w-9 rounded-lg" />
          <span className="text-sm font-semibold tracking-wide text-white">SST BAVARIA</span>
        </div>

        <EscenaMonitoreo className="mx-auto hidden w-full max-w-sm lg:block" />

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

function EscenaMonitoreo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 360 260" className={className} fill="none">
      <rect x="20" y="20" width="320" height="200" rx="14" stroke="white" strokeOpacity="0.18" strokeWidth="2" />

      <polygon
        points="120,70 260,70 280,160 100,160"
        fill="var(--color-corp-blue)"
        fillOpacity="0.18"
        stroke="var(--color-corp-blue)"
        strokeWidth="2"
        strokeDasharray="6 5"
      />
      <circle cx="120" cy="70" r="3.5" fill="var(--color-corp-blue)" />
      <circle cx="260" cy="70" r="3.5" fill="var(--color-corp-blue)" />
      <circle cx="280" cy="160" r="3.5" fill="var(--color-corp-blue)" />
      <circle cx="100" cy="160" r="3.5" fill="var(--color-corp-blue)" />

      <g transform="translate(175, 105)">
        <circle cx="10" cy="10" r="9" fill="white" fillOpacity="0.85" />
        <path d="M0 46c0-12 9-20 20-20s20 8 20 20" fill="white" fillOpacity="0.85" />
        <rect x="-8" y="-4" width="56" height="52" rx="6" fill="none" stroke="#22c55e" strokeWidth="2" />
      </g>
      <rect x="134" y="150" width="130" height="17" rx="8.5" fill="#22c55e" fillOpacity="0.9" />
      <text x="199" y="161.5" textAnchor="middle" fontSize="8.5" fontWeight="700" fill="var(--color-corp-navy-deep)">
        PERSONA DETECTADA
      </text>

      <g transform="translate(160, 4)">
        <path d="M0 20a20 20 0 0 1 40 0z" fill="white" fillOpacity="0.92" />
        <rect x="9" y="20" width="22" height="5" rx="2" fill="white" fillOpacity="0.92" />
        <circle cx="20" cy="15" r="6.5" fill="var(--color-corp-navy)" />
        <circle cx="20" cy="15" r="2.5" fill="white" fillOpacity="0.7" />
        <circle cx="35" cy="5" r="3.5" fill="#ef4444" />
      </g>
    </svg>
  );
}
