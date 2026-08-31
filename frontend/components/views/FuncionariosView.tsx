"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useDialog } from "@/components/DialogProvider";
import {
  ApiError,
  actualizarFuncionario,
  crearFuncionario,
  eliminarFuncionario,
  listarFuncionarios,
  type Funcionario,
  type NuevoFuncionario,
  type Rol,
  type RolFuncionario,
} from "@/lib/api";

const ROLES: { clave: RolFuncionario; etiqueta: string }[] = [
  { clave: "delegado_abi", etiqueta: "Delegado (Contratante)" },
  { clave: "seguridad_planta", etiqueta: "Seguridad de Planta (Site)" },
  { clave: "lider_area", etiqueta: "Líder de Área" },
  { clave: "dueno_territorio", etiqueta: "Dueño de Territorio" },
];

const INPUT =
  "w-full rounded-lg border border-corp-border px-3 py-2 text-sm text-corp-navy outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20";

export default function FuncionariosView({ token, rol }: { token: string; rol: Rol | null }) {
  const esAdmin = rol === "administrador";
  const { confirmar } = useDialog();
  const [funcionarios, setFuncionarios] = useState<Funcionario[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formulario, setFormulario] = useState<"nuevo" | Funcionario | null>(null);

  function cargar() {
    listarFuncionarios(token)
      .then(setFuncionarios)
      .catch(() => setError("No se pudo cargar la lista de funcionarios."));
  }

  useEffect(cargar, [token]);

  async function eliminar(funcionario: Funcionario) {
    const ok = await confirmar({
      titulo: "Eliminar funcionario",
      mensaje: `¿Eliminar a ${funcionario.nombre}? Ya no aparecerá para elegir al firmar declaraciones.`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
    try {
      await eliminarFuncionario(token, funcionario.id);
      cargar();
    } catch {
      setError("No se pudo eliminar el funcionario.");
    }
  }

  return (
    <div>
      <p className="text-sm text-corp-muted">
        Personas autorizadas a firmar electrónicamente declaraciones de método por rol interno de la
        empresa — el formulario de firma ofrece esta lista en vez de un texto libre.
      </p>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={() => setFormulario("nuevo")}
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy"
        >
          + Nuevo funcionario
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {funcionarios?.length === 0 && (
        <p className="mt-6 text-sm text-corp-muted">
          Todavía no hay funcionarios registrados — usa el botón &quot;+ Nuevo funcionario&quot; de arriba.
        </p>
      )}

      <div className="mt-6 space-y-6">
        {ROLES.map((r) => {
          const deEsteRol = funcionarios?.filter((f) => f.rol_firma === r.clave) ?? [];
          if (deEsteRol.length === 0) return null;
          return (
            <div key={r.clave}>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-corp-muted">{r.etiqueta}</h3>
              <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {deEsteRol.map((f) => (
                  <div key={f.id} className="rounded-xl border border-corp-border bg-white p-4 shadow-sm">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-corp-navy">{f.nombre}</p>
                        {f.cargo && <p className="text-sm text-corp-muted">{f.cargo}</p>}
                      </div>
                      {!f.activo && (
                        <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-corp-muted">
                          Inactivo
                        </span>
                      )}
                    </div>
                    {(f.correo || f.telefono) && (
                      <p className="mt-2 text-xs text-corp-muted">
                        {f.correo}
                        {f.correo && f.telefono && " · "}
                        {f.telefono}
                      </p>
                    )}
                    <div className="mt-3 flex gap-3 text-sm">
                      <button
                        type="button"
                        onClick={() => setFormulario(f)}
                        className="font-medium text-corp-blue hover:underline"
                      >
                        Editar
                      </button>
                      {esAdmin && (
                        <button
                          type="button"
                          onClick={() => eliminar(f)}
                          className="font-medium text-red-600 hover:underline"
                        >
                          Eliminar
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {formulario && (
        <FormularioFuncionario
          token={token}
          funcionario={formulario === "nuevo" ? null : formulario}
          onCerrar={() => setFormulario(null)}
          onGuardado={() => {
            setFormulario(null);
            cargar();
          }}
        />
      )}
    </div>
  );
}

function FormularioFuncionario({
  token,
  funcionario,
  onCerrar,
  onGuardado,
}: {
  token: string;
  funcionario: Funcionario | null;
  onCerrar: () => void;
  onGuardado: () => void;
}) {
  const [nombre, setNombre] = useState(funcionario?.nombre ?? "");
  const [cargo, setCargo] = useState(funcionario?.cargo ?? "");
  const [rolFirma, setRolFirma] = useState<RolFuncionario>(funcionario?.rol_firma ?? ROLES[0].clave);
  const [correo, setCorreo] = useState(funcionario?.correo ?? "");
  const [telefono, setTelefono] = useState(funcionario?.telefono ?? "");
  const [activo, setActivo] = useState(funcionario?.activo ?? true);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    const datos: NuevoFuncionario = { nombre, cargo, rol_firma: rolFirma, correo, telefono, activo };
    try {
      if (funcionario) {
        await actualizarFuncionario(token, funcionario.id, datos);
      } else {
        await crearFuncionario(token, datos);
      }
      onGuardado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el funcionario.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 px-4 py-8">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-corp-navy">
          {funcionario ? "Editar funcionario" : "Nuevo funcionario"}
        </h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-corp-navy">Nombre completo</span>
            <input required value={nombre} onChange={(e) => setNombre(e.target.value)} className={INPUT} />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-corp-navy">Cargo</span>
            <input value={cargo} onChange={(e) => setCargo(e.target.value)} className={INPUT} />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-corp-navy">Rol de firma</span>
            <select
              value={rolFirma}
              onChange={(e) => setRolFirma(e.target.value as RolFuncionario)}
              className={INPUT}
            >
              {ROLES.map((r) => (
                <option key={r.clave} value={r.clave}>
                  {r.etiqueta}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block space-y-1.5">
              <span className="text-sm font-medium text-corp-navy">Correo</span>
              <input
                type="email"
                value={correo}
                onChange={(e) => setCorreo(e.target.value)}
                className={INPUT}
              />
            </label>
            <label className="block space-y-1.5">
              <span className="text-sm font-medium text-corp-navy">Teléfono</span>
              <input value={telefono} onChange={(e) => setTelefono(e.target.value)} className={INPUT} />
            </label>
          </div>
          <label className="flex items-center gap-2 text-sm text-corp-navy">
            <input
              type="checkbox"
              checked={activo}
              onChange={(e) => setActivo(e.target.checked)}
              className="h-4 w-4 rounded border-corp-border accent-corp-blue"
            />
            Activo (aparece como opción al firmar)
          </label>

          {error && (
            <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
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
              {enviando ? "Guardando…" : funcionario ? "Guardar cambios" : "Crear funcionario"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
