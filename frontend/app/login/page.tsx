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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <FondoAtardecer />

      <div className="relative z-10 w-full max-w-sm rounded-3xl border border-white/20 bg-white/10 p-8 shadow-2xl backdrop-blur-xl">
        <div className="mb-7 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15 text-lg font-bold text-white ring-1 ring-white/30">
            SB
          </div>
          <h1 className="text-2xl font-semibold text-white">Iniciar sesión</h1>
          <p className="mt-1 text-sm text-white/70">
            SST Bavaria · Módulo de Cámaras IA
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <IconUsuario className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-white/60" />
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Usuario"
              className="w-full rounded-full border border-white/25 bg-white/10 py-3 pl-11 pr-4 text-sm text-white placeholder-white/50 outline-none transition focus:border-white/60 focus:bg-white/15"
            />
          </div>

          <div className="relative">
            <IconCandado className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-white/60" />
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Contraseña"
              className="w-full rounded-full border border-white/25 bg-white/10 py-3 pl-11 pr-4 text-sm text-white placeholder-white/50 outline-none transition focus:border-white/60 focus:bg-white/15"
            />
          </div>

          <div className="flex items-center justify-between text-xs text-white/70">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={recordarme}
                onChange={(event) => setRecordarme(event.target.checked)}
                className="h-3.5 w-3.5 rounded border-white/40 bg-white/10 accent-white"
              />
              Recordarme
            </label>
            <button
              type="button"
              onClick={() => setAvisoClave(true)}
              className="font-medium text-white/80 hover:text-white hover:underline"
            >
              ¿Olvidaste tu contraseña?
            </button>
          </div>

          {avisoClave && (
            <p className="rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-xs text-white/80">
              Contacta a tu administrador para restablecer tu contraseña.
            </p>
          )}

          {error && (
            <div
              role="alert"
              className="rounded-xl border border-red-300/40 bg-red-500/20 px-3 py-2 text-sm text-white"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={cargando}
            className="w-full rounded-full bg-white py-3 text-sm font-semibold text-corp-navy shadow-lg transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {cargando ? "Verificando…" : "Entrar"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-white/50">
          Acceso exclusivo para personal autorizado.
        </p>
      </div>
    </div>
  );
}

function FondoAtardecer() {
  return (
    <div
      aria-hidden
      className="absolute inset-0 -z-10"
      style={{
        background:
          "radial-gradient(80% 60% at 50% 10%, var(--color-dusk-3) 0%, transparent 60%), linear-gradient(180deg, var(--color-dusk-1) 0%, var(--color-dusk-2) 45%, var(--color-dusk-3) 75%, var(--color-dusk-4) 100%)",
      }}
    >
      <div
        className="absolute left-[18%] top-[14%] h-28 w-28 rounded-full opacity-90 blur-[2px] sm:h-36 sm:w-36"
        style={{
          background:
            "radial-gradient(circle at 35% 35%, #fff2d6 0%, var(--color-dusk-4) 55%, transparent 75%)",
        }}
      />
      <svg
        viewBox="0 0 1280 400"
        preserveAspectRatio="none"
        className="absolute bottom-0 left-0 h-[38%] w-full opacity-90"
      >
        <polygon
          points="0,400 0,220 180,300 340,150 520,260 700,120 900,260 1080,180 1280,280 1280,400"
          fill="var(--color-corp-navy-deep)"
        />
      </svg>
      <div className="absolute inset-0 bg-black/10" />
    </div>
  );
}
