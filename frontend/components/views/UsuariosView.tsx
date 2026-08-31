"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { useDialog } from "@/components/DialogProvider";
import {
  ApiError,
  actualizarUsuario,
  crearUsuario,
  eliminarUsuario,
  listarUsuarios,
  type Rol,
  type UsuarioGestionado,
} from "@/lib/api";

type Props = { token: string; usuarioActualId: number };

export default function UsuariosView({ token, usuarioActualId }: Props) {
  const [usuarios, setUsuarios] = useState<UsuarioGestionado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const { confirmar } = useDialog();

  function cargar() {
    listarUsuarios(token)
      .then(setUsuarios)
      .catch(() => setError("No se pudo cargar la lista de usuarios."));
  }

  useEffect(cargar, [token]);

  async function cambiarRol(usuario: UsuarioGestionado, rol: Rol) {
    try {
      await actualizarUsuario(token, usuario.id, { rol });
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el rol.");
    }
  }

  async function alternarActivo(usuario: UsuarioGestionado) {
    try {
      await actualizarUsuario(token, usuario.id, { is_active: !usuario.is_active });
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el estado.");
    }
  }

  async function eliminar(usuario: UsuarioGestionado) {
    const ok = await confirmar({
      titulo: "Eliminar usuario",
      mensaje: `¿Eliminar a ${usuario.username}? Esta acción no se puede deshacer.`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) {
      return;
    }
    try {
      await eliminarUsuario(token, usuario.id);
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar el usuario.");
    }
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-corp-muted">Usuarios con acceso al panel.</p>
        <button
          type="button"
          onClick={() => setMostrarFormulario(true)}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy"
        >
          + Nuevo usuario
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-6 overflow-x-auto rounded-xl border border-corp-border bg-white">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-corp-border bg-corp-blue-light text-xs uppercase text-corp-muted">
            <tr>
              <th className="px-4 py-3">Usuario</th>
              <th className="px-4 py-3">Correo</th>
              <th className="px-4 py-3">Rol</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios?.map((usuario) => {
              const esUsuarioActual = usuario.id === usuarioActualId;
              return (
                <tr key={usuario.id} className="border-b border-corp-border last:border-0">
                  <td className="px-4 py-3 font-medium text-corp-navy">{usuario.username}</td>
                  <td className="px-4 py-3 text-corp-muted">{usuario.email || "—"}</td>
                  <td className="px-4 py-3">
                    <select
                      value={usuario.rol}
                      disabled={esUsuarioActual}
                      onChange={(event) => cambiarRol(usuario, event.target.value as Rol)}
                      className="rounded-md border border-corp-border px-2 py-1 text-sm disabled:opacity-50"
                    >
                      <option value="administrador">Administrador</option>
                      <option value="operador">Operador</option>
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        usuario.is_active ? "bg-green-100 text-green-700" : "bg-zinc-100 text-zinc-500"
                      }`}
                    >
                      {usuario.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        disabled={esUsuarioActual}
                        onClick={() => alternarActivo(usuario)}
                        className="rounded-md border border-corp-border px-2.5 py-1 text-xs font-medium text-corp-navy transition hover:border-corp-blue disabled:opacity-40"
                      >
                        {usuario.is_active ? "Desactivar" : "Activar"}
                      </button>
                      <button
                        type="button"
                        disabled={esUsuarioActual}
                        onClick={() => eliminar(usuario)}
                        className="rounded-md border border-red-200 px-2.5 py-1 text-xs font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-40"
                      >
                        Eliminar
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {usuarios?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-corp-muted">No hay usuarios todavía.</p>
        )}
      </div>

      {mostrarFormulario && (
        <FormularioNuevoUsuario
          token={token}
          onCerrar={() => setMostrarFormulario(false)}
          onCreado={() => {
            setMostrarFormulario(false);
            cargar();
          }}
        />
      )}
    </div>
  );
}

function FormularioNuevoUsuario({
  token,
  onCerrar,
  onCreado,
}: {
  token: string;
  onCerrar: () => void;
  onCreado: () => void;
}) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rol, setRol] = useState<Rol>("operador");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await crearUsuario(token, { username, email, password, rol });
      onCreado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el usuario.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">Nuevo usuario</h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <Campo label="Usuario">
            <input
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <Campo label="Correo">
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <Campo label="Contraseña">
            <input
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            />
          </Campo>
          <Campo label="Rol">
            <select
              value={rol}
              onChange={(event) => setRol(event.target.value as Rol)}
              className="w-full rounded-lg border border-corp-border px-3 py-2 text-sm outline-none transition focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20"
            >
              <option value="operador">Operador</option>
              <option value="administrador">Administrador</option>
            </select>
          </Campo>

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onCerrar}
              className="rounded-lg px-4 py-2 text-sm font-medium text-corp-muted hover:bg-zinc-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:opacity-60"
            >
              {enviando ? "Creando…" : "Crear usuario"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Campo({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-corp-navy">{label}</span>
      {children}
    </label>
  );
}
