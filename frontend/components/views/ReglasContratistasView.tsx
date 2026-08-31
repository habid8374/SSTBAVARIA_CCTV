"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useDialog } from "@/components/DialogProvider";
import {
  ApiError,
  actualizarConfiguracionAlertas,
  actualizarCurso,
  actualizarPermisoTrabajo,
  crearCurso,
  crearPermisoTrabajo,
  eliminarCurso,
  eliminarPermisoTrabajo,
  listarCursos,
  listarPermisosTrabajo,
  obtenerConfiguracionAlertas,
  type ConfiguracionAlertas,
  type CursoSafetyAcademy,
  type PermisoTrabajo,
} from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-corp-border px-3 py-2 text-sm text-corp-navy outline-none focus:border-corp-blue focus:ring-2 focus:ring-corp-blue/20";

export default function ReglasContratistasView({ token }: { token: string }) {
  return (
    <div className="space-y-8">
      <p className="text-sm text-corp-muted">
        Catálogos y umbrales que antes estaban fijos en el código — ahora se pueden ajustar acá sin
        necesidad de tocar nada de programación.
      </p>
      <DiasAlerta token={token} />
      <Cursos token={token} />
      <Permisos token={token} />
    </div>
  );
}

function DiasAlerta({ token }: { token: string }) {
  const [config, setConfig] = useState<ConfiguracionAlertas | null>(null);
  const [dias, setDias] = useState("");
  const [correoRevisor, setCorreoRevisor] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardado, setGuardado] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    obtenerConfiguracionAlertas(token)
      .then((c) => {
        setConfig(c);
        setDias(String(c.dias_alerta_vencimiento));
        setCorreoRevisor(c.correo_revisor);
      })
      .catch(() => setError("No se pudo cargar la configuración de alertas."));
  }, [token]);

  async function guardar(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setGuardado(false);
    setEnviando(true);
    try {
      const actualizado = await actualizarConfiguracionAlertas(token, {
        dias_alerta_vencimiento: Number(dias),
        correo_revisor: correoRevisor,
      });
      setConfig(actualizado);
      setGuardado(true);
      setTimeout(() => setGuardado(false), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="rounded-xl border border-corp-border bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-corp-navy">Alertas y avisos por correo</h3>
      {config && (
        <form onSubmit={guardar} className="mt-3 space-y-4">
          <div>
            <label className="space-y-1.5">
              <span className="text-sm font-medium text-corp-navy">Días de alerta de vencimiento</span>
              <p className="text-xs text-corp-muted">
                A cuántos días de vencer una planilla de seguridad social se considera &quot;por
                vencer&quot; en el banner de aviso de Contratistas.
              </p>
              <input
                type="number"
                min={1}
                required
                value={dias}
                onChange={(e) => setDias(e.target.value)}
                className={`${INPUT} w-28`}
              />
            </label>
          </div>
          <div>
            <label className="space-y-1.5">
              <span className="text-sm font-medium text-corp-navy">Correo para avisos de revisión pendiente</span>
              <p className="text-xs text-corp-muted">
                A dónde avisar cuando se radica seguridad social o se envía una declaración de método que
                queda pendiente de revisión. Vacío = no se envía ese aviso (el de aprobado/rechazado sigue
                yendo siempre al contacto de la empresa contratista).
              </p>
              <input
                type="email"
                value={correoRevisor}
                onChange={(e) => setCorreoRevisor(e.target.value)}
                placeholder="revisor@empresa.com"
                className={`${INPUT} max-w-sm`}
              />
            </label>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={enviando}
              className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy disabled:opacity-60"
            >
              {enviando ? "Guardando…" : "Guardar"}
            </button>
            {guardado && <span className="text-sm text-emerald-700">Guardado ✓</span>}
          </div>
        </form>
      )}
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
    </div>
  );
}

function Cursos({ token }: { token: string }) {
  const { confirmar } = useDialog();
  const [cursos, setCursos] = useState<CursoSafetyAcademy[] | null>(null);
  const [clave, setClave] = useState("");
  const [etiqueta, setEtiqueta] = useState("");
  const [error, setError] = useState<string | null>(null);

  function cargar() {
    listarCursos(token).then(setCursos).catch(() => setError("No se pudo cargar la lista de cursos."));
  }

  useEffect(cargar, [token]);

  async function agregar(event: FormEvent) {
    event.preventDefault();
    if (!clave.trim() || !etiqueta.trim()) return;
    setError(null);
    try {
      await crearCurso(token, { clave: clave.trim(), etiqueta: etiqueta.trim() });
      setClave("");
      setEtiqueta("");
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el curso.");
    }
  }

  async function alternarActivo(curso: CursoSafetyAcademy) {
    try {
      await actualizarCurso(token, curso.id, { activo: !curso.activo });
      cargar();
    } catch {
      setError("No se pudo actualizar el curso.");
    }
  }

  async function alternarObligatorio(curso: CursoSafetyAcademy) {
    try {
      await actualizarCurso(token, curso.id, { obligatorio: !curso.obligatorio });
      cargar();
    } catch {
      setError("No se pudo actualizar el curso.");
    }
  }

  async function eliminar(curso: CursoSafetyAcademy) {
    const ok = await confirmar({
      titulo: "Eliminar curso",
      mensaje: `¿Eliminar "${curso.etiqueta}"? Ya no aparecerá como opción al registrar trabajadores.`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
    try {
      await eliminarCurso(token, curso.id);
      cargar();
    } catch {
      setError("No se pudo eliminar el curso.");
    }
  }

  return (
    <div className="rounded-xl border border-corp-border bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-corp-navy">Cursos Safety Academy</h3>
      <p className="mt-1 text-sm text-corp-muted">
        Marcar un curso como obligatorio avisa (en Indicadores y en la ficha del trabajador) cuando algún
        trabajador activo no lo tiene completado.
      </p>
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
      <div className="mt-3 space-y-2">
        {cursos?.map((c) => (
          <div key={c.id} className="flex items-center justify-between rounded-lg border border-corp-border px-3 py-2 text-sm">
            <div>
              <span className={c.activo ? "text-corp-navy" : "text-corp-muted line-through"}>{c.etiqueta}</span>
              <span className="ml-2 text-xs text-corp-muted">({c.clave})</span>
              {c.obligatorio && (
                <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                  Obligatorio
                </span>
              )}
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={() => alternarObligatorio(c)} className="text-corp-blue hover:underline">
                {c.obligatorio ? "Quitar obligatoriedad" : "Marcar obligatorio"}
              </button>
              <button type="button" onClick={() => alternarActivo(c)} className="text-corp-blue hover:underline">
                {c.activo ? "Desactivar" : "Activar"}
              </button>
              <button type="button" onClick={() => eliminar(c)} className="text-red-600 hover:underline">
                Eliminar
              </button>
            </div>
          </div>
        ))}
      </div>
      <form onSubmit={agregar} className="mt-4 flex flex-wrap items-end gap-3">
        <label className="space-y-1.5">
          <span className="text-sm font-medium text-corp-navy">Clave</span>
          <input
            value={clave}
            onChange={(e) => setClave(e.target.value)}
            placeholder="ej. trabajo_alturas"
            className={`${INPUT} w-44`}
          />
        </label>
        <label className="flex-1 space-y-1.5">
          <span className="text-sm font-medium text-corp-navy">Nombre del curso</span>
          <input value={etiqueta} onChange={(e) => setEtiqueta(e.target.value)} className={INPUT} />
        </label>
        <button
          type="submit"
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy"
        >
          + Agregar
        </button>
      </form>
    </div>
  );
}

function Permisos({ token }: { token: string }) {
  const { confirmar } = useDialog();
  const [permisos, setPermisos] = useState<PermisoTrabajo[] | null>(null);
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState<string | null>(null);

  function cargar() {
    listarPermisosTrabajo(token).then(setPermisos).catch(() => setError("No se pudo cargar la lista de permisos."));
  }

  useEffect(cargar, [token]);

  async function agregar(event: FormEvent) {
    event.preventDefault();
    if (!nombre.trim()) return;
    setError(null);
    try {
      await crearPermisoTrabajo(token, { nombre: nombre.trim() });
      setNombre("");
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el permiso.");
    }
  }

  async function alternarActivo(permiso: PermisoTrabajo) {
    try {
      await actualizarPermisoTrabajo(token, permiso.id, { activo: !permiso.activo });
      cargar();
    } catch {
      setError("No se pudo actualizar el permiso.");
    }
  }

  async function eliminar(permiso: PermisoTrabajo) {
    const ok = await confirmar({
      titulo: "Eliminar permiso de trabajo",
      mensaje: `¿Eliminar "${permiso.nombre}"? Ya no aparecerá como opción en las actividades de una declaración de método.`,
      textoConfirmar: "Eliminar",
      peligroso: true,
    });
    if (!ok) return;
    try {
      await eliminarPermisoTrabajo(token, permiso.id);
      cargar();
    } catch {
      setError("No se pudo eliminar el permiso.");
    }
  }

  return (
    <div className="rounded-xl border border-corp-border bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-corp-navy">Permisos de trabajo / certificados requeridos</h3>
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
      <div className="mt-3 space-y-2">
        {permisos?.map((p) => (
          <div key={p.id} className="flex items-center justify-between rounded-lg border border-corp-border px-3 py-2 text-sm">
            <span className={p.activo ? "text-corp-navy" : "text-corp-muted line-through"}>{p.nombre}</span>
            <div className="flex gap-3">
              <button type="button" onClick={() => alternarActivo(p)} className="text-corp-blue hover:underline">
                {p.activo ? "Desactivar" : "Activar"}
              </button>
              <button type="button" onClick={() => eliminar(p)} className="text-red-600 hover:underline">
                Eliminar
              </button>
            </div>
          </div>
        ))}
      </div>
      <form onSubmit={agregar} className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex-1 space-y-1.5">
          <span className="text-sm font-medium text-corp-navy">Nombre del permiso</span>
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} className={INPUT} />
        </label>
        <button
          type="submit"
          className="rounded-lg bg-corp-blue px-4 py-2 text-sm font-semibold text-white transition hover:bg-corp-navy"
        >
          + Agregar
        </button>
      </form>
    </div>
  );
}
