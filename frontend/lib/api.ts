export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** DRF devuelve errores como {"detail": "..."} (permisos, throttle, etc.) o
 * como {"campo": ["mensaje", ...], ...} (errores de validación por campo,
 * p. ej. un archivo con extensión no permitida) — ambos formatos posibles. */
function extraerMensajeError(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const registro = body as Record<string, unknown>;
  if (typeof registro.detail === "string") return registro.detail;
  for (const valor of Object.values(registro)) {
    if (Array.isArray(valor) && typeof valor[0] === "string") {
      return valor[0];
    }
  }
  return null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const esFormData = options.body instanceof FormData;
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(esFormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let detail = "Ocurrió un error inesperado.";
    try {
      const body = await response.json();
      detail = extraerMensajeError(body) ?? detail;
    } catch {
      // sin cuerpo JSON, se usa el mensaje genérico
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export type Rol = "administrador" | "operador" | "contratista";

export type Usuario = {
  id: number;
  username: string;
  nombre: string;
  email: string;
  is_staff: boolean;
  es_superusuario: boolean;
  rol: Rol | null;
  contratista_id: number | null;
  contratista_nombre: string | null;
};

export type LoginResponse = {
  token: string;
  usuario: Usuario;
};

export type UsuarioGestionado = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  is_active: boolean;
  rol: Rol;
  contratista: number | null;
  contratista_nombre: string | null;
  date_joined: string;
};

export type NuevoUsuario = {
  username: string;
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  rol: Rol;
  contratista?: number | null;
};

export type Resumen = {
  camaras_activas: number;
  eventos_nuevos: number;
  alertas_hoy: number;
};

export function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout(token: string): Promise<void> {
  return request<void>("/api/auth/logout/", {
    method: "POST",
    headers: { Authorization: `Token ${token}` },
  });
}

export function obtenerPerfil(token: string): Promise<Usuario> {
  return request<Usuario>("/api/auth/perfil/", {
    headers: { Authorization: `Token ${token}` },
  });
}

export function obtenerResumen(token: string): Promise<Resumen> {
  return request<Resumen>("/api/auth/resumen/", {
    headers: { Authorization: `Token ${token}` },
  });
}

export function obtenerClavePublicaPush(token: string): Promise<{ clave_publica: string }> {
  return request<{ clave_publica: string }>("/api/auth/push/vapid-public-key/", {
    headers: { Authorization: `Token ${token}` },
  });
}

export function suscribirPush(token: string, suscripcion: PushSubscriptionJSON): Promise<void> {
  return request<void>("/api/auth/push/suscribir/", {
    method: "POST",
    headers: { Authorization: `Token ${token}` },
    body: JSON.stringify(suscripcion),
  });
}

export function desuscribirPush(token: string, endpoint: string): Promise<void> {
  return request<void>("/api/auth/push/desuscribir/", {
    method: "DELETE",
    headers: { Authorization: `Token ${token}` },
    body: JSON.stringify({ endpoint }),
  });
}

export function listarUsuarios(token: string): Promise<UsuarioGestionado[]> {
  return request<UsuarioGestionado[]>("/api/auth/usuarios/", {
    headers: { Authorization: `Token ${token}` },
  });
}

export function crearUsuario(token: string, datos: NuevoUsuario): Promise<UsuarioGestionado> {
  return request<UsuarioGestionado>("/api/auth/usuarios/", {
    method: "POST",
    headers: { Authorization: `Token ${token}` },
    body: JSON.stringify(datos),
  });
}

export function actualizarUsuario(
  token: string,
  id: number,
  cambios: Partial<
    Pick<UsuarioGestionado, "rol" | "is_active" | "first_name" | "last_name" | "email" | "contratista">
  >
): Promise<UsuarioGestionado> {
  return request<UsuarioGestionado>(`/api/auth/usuarios/${id}/`, {
    method: "PATCH",
    headers: { Authorization: `Token ${token}` },
    body: JSON.stringify(cambios),
  });
}

export function eliminarUsuario(token: string, id: number): Promise<void> {
  return request<void>(`/api/auth/usuarios/${id}/`, {
    method: "DELETE",
    headers: { Authorization: `Token ${token}` },
  });
}

// --- Dashboard de cámaras: indicadores, eventos, cámaras, zonas, reglas ---

export type Indicadores = {
  camaras_activas: number;
  camaras_total: number;
  alertas_hoy: number;
  disponibilidad: number;
};

export type EventoPorZona = {
  zona: string;
  camara: string;
  total: number;
};

export type EstadoEvento = "nuevo" | "revisado";

export type EventoDashboard = {
  id: number;
  camara: number;
  camara_nombre: string;
  zona: number | null;
  zona_nombre: string | null;
  timestamp: string;
  snapshot: string | null;
  punto_x: number | null;
  punto_y: number | null;
  disparo_alerta: boolean;
  canal_notificacion: "whatsapp" | "correo" | "";
  notificacion_enviada: boolean;
  notificacion_detalle: string;
  estado: EstadoEvento;
};

export type ReglaAlerta = {
  id: number;
  zona: number;
  zona_nombre: string;
  nombre: string;
  hora_inicio: string;
  hora_fin: string;
  dias_semana: number[];
  canal_notificacion: "whatsapp" | "correo";
  destinatario: string;
  activa: boolean;
};

export type NuevaRegla = Omit<ReglaAlerta, "id" | "zona_nombre" | "activa"> & { activa?: boolean };

export type ZonaDashboard = {
  id: number;
  camara: number;
  camara_nombre: string;
  nombre: string;
  poligono: number[][];
  activa: boolean;
  reglas: ReglaAlerta[];
};

export type NuevaZona = {
  camara: number;
  nombre: string;
  poligono: number[][];
  activa?: boolean;
};

export type UltimoEvento = {
  id: number;
  zona: number | null;
  zona_nombre: string | null;
  timestamp: string;
  snapshot: string | null;
  punto_x: number | null;
  punto_y: number | null;
  disparo_alerta: boolean;
};

export type CamaraDashboard = {
  id: number;
  nombre: string;
  ip: string;
  puerto_onvif: number;
  usuario_onvif: string;
  password_onvif: string;
  rtsp_url: string;
  ubicacion: string;
  activa: boolean;
  snapshot_referencia: string | null;
  zonas: ZonaDashboard[];
  ultimo_evento: UltimoEvento | null;
};

export type NuevaCamara = {
  nombre: string;
  ip: string;
  puerto_onvif?: number;
  usuario_onvif?: string;
  password_onvif?: string;
  rtsp_url?: string;
  ubicacion?: string;
  activa?: boolean;
};

function authHeaders(token: string) {
  return { Authorization: `Token ${token}` };
}

export function obtenerIndicadores(token: string): Promise<Indicadores> {
  return request<Indicadores>("/api/camaras-ia/dashboard/indicadores/", { headers: authHeaders(token) });
}

export function obtenerEventosPorZona(token: string): Promise<EventoPorZona[]> {
  return request<EventoPorZona[]>("/api/camaras-ia/dashboard/eventos-por-zona/", {
    headers: authHeaders(token),
  });
}

export function listarEventos(
  token: string,
  filtros: {
    estado?: EstadoEvento;
    disparo_alerta?: boolean;
    camara?: number;
    canal_notificacion?: "whatsapp" | "correo";
  } = {}
): Promise<EventoDashboard[]> {
  const params = new URLSearchParams();
  if (filtros.estado) params.set("estado", filtros.estado);
  if (filtros.disparo_alerta !== undefined) params.set("disparo_alerta", String(filtros.disparo_alerta));
  if (filtros.camara !== undefined) params.set("camara", String(filtros.camara));
  if (filtros.canal_notificacion) params.set("canal_notificacion", filtros.canal_notificacion);
  const query = params.toString();
  return request<EventoDashboard[]>(`/api/camaras-ia/dashboard/eventos/${query ? `?${query}` : ""}`, {
    headers: authHeaders(token),
  });
}

export function actualizarEvento(token: string, id: number, estado: EstadoEvento): Promise<EventoDashboard> {
  return request<EventoDashboard>(`/api/camaras-ia/dashboard/eventos/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify({ estado }),
  });
}

export function listarCamarasDashboard(token: string): Promise<CamaraDashboard[]> {
  return request<CamaraDashboard[]>("/api/camaras-ia/dashboard/camaras/", { headers: authHeaders(token) });
}

export function crearCamara(token: string, datos: NuevaCamara): Promise<CamaraDashboard> {
  return request<CamaraDashboard>("/api/camaras-ia/dashboard/camaras/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarCamara(
  token: string,
  id: number,
  cambios: Partial<NuevaCamara>
): Promise<CamaraDashboard> {
  return request<CamaraDashboard>(`/api/camaras-ia/dashboard/camaras/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function subirSnapshotReferencia(
  token: string,
  camaraId: number,
  archivo: File
): Promise<CamaraDashboard> {
  const formData = new FormData();
  formData.append("snapshot_referencia", archivo);
  return request<CamaraDashboard>(`/api/camaras-ia/dashboard/camaras/${camaraId}/snapshot-referencia/`, {
    method: "POST",
    headers: authHeaders(token),
    body: formData,
  });
}

export function crearZona(token: string, datos: NuevaZona): Promise<ZonaDashboard> {
  return request<ZonaDashboard>("/api/camaras-ia/dashboard/zonas/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarZona(
  token: string,
  id: number,
  cambios: Partial<Pick<ZonaDashboard, "nombre" | "poligono" | "activa">>
): Promise<ZonaDashboard> {
  return request<ZonaDashboard>(`/api/camaras-ia/dashboard/zonas/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function eliminarZona(token: string, id: number): Promise<void> {
  return request<void>(`/api/camaras-ia/dashboard/zonas/${id}/`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export function crearRegla(token: string, datos: NuevaRegla): Promise<ReglaAlerta> {
  return request<ReglaAlerta>("/api/camaras-ia/dashboard/reglas/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarRegla(
  token: string,
  id: number,
  cambios: Partial<NuevaRegla & { activa: boolean }>
): Promise<ReglaAlerta> {
  return request<ReglaAlerta>(`/api/camaras-ia/dashboard/reglas/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function eliminarRegla(token: string, id: number): Promise<void> {
  return request<void>(`/api/camaras-ia/dashboard/reglas/${id}/`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

// --- Sistema: credenciales Brevo + gestión de equipos locales ---

export type ConfiguracionNotificaciones = {
  brevo_api_key_configurada: boolean;
  brevo_remitente_email: string;
  brevo_remitente_nombre: string;
  actualizada_en: string;
};

export type CambiosConfiguracionNotificaciones = {
  brevo_api_key?: string;
  brevo_remitente_email?: string;
  brevo_remitente_nombre?: string;
};

export function obtenerConfiguracionNotificaciones(token: string): Promise<ConfiguracionNotificaciones> {
  return request<ConfiguracionNotificaciones>("/api/camaras-ia/dashboard/configuracion-notificaciones/", {
    headers: authHeaders(token),
  });
}

export function actualizarConfiguracionNotificaciones(
  token: string,
  cambios: CambiosConfiguracionNotificaciones
): Promise<ConfiguracionNotificaciones> {
  return request<ConfiguracionNotificaciones>("/api/camaras-ia/dashboard/configuracion-notificaciones/", {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export type EquipoLocal = {
  id: number;
  nombre: string;
  api_key: string;
  activo: boolean;
  ultima_conexion: string | null;
  conectado: boolean;
  creado_en: string;
};

export function listarEquiposLocales(token: string): Promise<EquipoLocal[]> {
  return request<EquipoLocal[]>("/api/camaras-ia/dashboard/equipos-locales/", { headers: authHeaders(token) });
}

export function crearEquipoLocal(token: string, nombre: string): Promise<EquipoLocal> {
  return request<EquipoLocal>("/api/camaras-ia/dashboard/equipos-locales/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ nombre }),
  });
}

export function actualizarEquipoLocal(
  token: string,
  id: number,
  cambios: Partial<Pick<EquipoLocal, "nombre" | "activo">>
): Promise<EquipoLocal> {
  return request<EquipoLocal>(`/api/camaras-ia/dashboard/equipos-locales/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function eliminarEquipoLocal(token: string, id: number): Promise<void> {
  return request<void>(`/api/camaras-ia/dashboard/equipos-locales/${id}/`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export function descargarEquipoLocalZip(token: string): Promise<void> {
  return descargarArchivo(token, "/api/camaras-ia/dashboard/equipos-locales/descargar-zip/", "equipo_local.zip");
}

// --- Contratistas: empresas, trabajadores, seguridad social, declaración de método ---

export type Opcion = { clave: string; etiqueta: string };

export type Catalogos = {
  cursos_safety_academy: (Opcion & { obligatorio: boolean })[];
  permisos_trabajo: string[];
  equipos_epp: string[];
  roles_firma: Opcion[];
};

export function obtenerCatalogosContratistas(token: string): Promise<Catalogos> {
  return request<Catalogos>("/api/contratistas/catalogos/", { headers: authHeaders(token) });
}

export type CursoSafetyAcademy = {
  id: number;
  clave: string;
  etiqueta: string;
  activo: boolean;
  obligatorio: boolean;
  orden: number;
};

export type NuevoCursoSafetyAcademy = {
  clave: string;
  etiqueta: string;
  activo?: boolean;
  obligatorio?: boolean;
  orden?: number;
};

export function listarCursos(token: string): Promise<CursoSafetyAcademy[]> {
  return request<CursoSafetyAcademy[]>("/api/contratistas/cursos/", { headers: authHeaders(token) });
}

export function crearCurso(token: string, datos: NuevoCursoSafetyAcademy): Promise<CursoSafetyAcademy> {
  return request<CursoSafetyAcademy>("/api/contratistas/cursos/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarCurso(
  token: string,
  id: number,
  cambios: Partial<NuevoCursoSafetyAcademy>
): Promise<CursoSafetyAcademy> {
  return request<CursoSafetyAcademy>(`/api/contratistas/cursos/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function eliminarCurso(token: string, id: number): Promise<void> {
  return request<void>(`/api/contratistas/cursos/${id}/`, { method: "DELETE", headers: authHeaders(token) });
}

export type PermisoTrabajo = { id: number; nombre: string; activo: boolean; orden: number };

export type NuevoPermisoTrabajo = { nombre: string; activo?: boolean; orden?: number };

export function listarPermisosTrabajo(token: string): Promise<PermisoTrabajo[]> {
  return request<PermisoTrabajo[]>("/api/contratistas/permisos-trabajo/", { headers: authHeaders(token) });
}

export function crearPermisoTrabajo(token: string, datos: NuevoPermisoTrabajo): Promise<PermisoTrabajo> {
  return request<PermisoTrabajo>("/api/contratistas/permisos-trabajo/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarPermisoTrabajo(
  token: string,
  id: number,
  cambios: Partial<NuevoPermisoTrabajo>
): Promise<PermisoTrabajo> {
  return request<PermisoTrabajo>(`/api/contratistas/permisos-trabajo/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function eliminarPermisoTrabajo(token: string, id: number): Promise<void> {
  return request<void>(`/api/contratistas/permisos-trabajo/${id}/`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export type EquipoProteccionPersonal = { id: number; nombre: string; activo: boolean; orden: number };

export type NuevoEquipoProteccionPersonal = { nombre: string; activo?: boolean; orden?: number };

export function listarEquiposEpp(token: string): Promise<EquipoProteccionPersonal[]> {
  return request<EquipoProteccionPersonal[]>("/api/contratistas/equipos-epp/", { headers: authHeaders(token) });
}

export function crearEquipoEpp(
  token: string,
  datos: NuevoEquipoProteccionPersonal
): Promise<EquipoProteccionPersonal> {
  return request<EquipoProteccionPersonal>("/api/contratistas/equipos-epp/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarEquipoEpp(
  token: string,
  id: number,
  cambios: Partial<NuevoEquipoProteccionPersonal>
): Promise<EquipoProteccionPersonal> {
  return request<EquipoProteccionPersonal>(`/api/contratistas/equipos-epp/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function eliminarEquipoEpp(token: string, id: number): Promise<void> {
  return request<void>(`/api/contratistas/equipos-epp/${id}/`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export type ConfiguracionAlertas = {
  dias_alerta_vencimiento: number;
  correo_revisor: string;
  actualizada_en: string;
};

export function obtenerConfiguracionAlertas(token: string): Promise<ConfiguracionAlertas> {
  return request<ConfiguracionAlertas>("/api/contratistas/configuracion-alertas/", { headers: authHeaders(token) });
}

export function actualizarConfiguracionAlertas(
  token: string,
  cambios: Partial<ConfiguracionAlertas>
): Promise<ConfiguracionAlertas> {
  return request<ConfiguracionAlertas>("/api/contratistas/configuracion-alertas/", {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export type RegistroAuditoria = {
  id: number;
  modelo: string;
  objeto_id: number;
  objeto_str: string;
  accion: "creado" | "actualizado" | "eliminado";
  accion_display: string;
  usuario_nombre: string;
  cambios: Record<string, { antes: unknown; despues: unknown }>;
  fecha: string;
};

export function listarAuditoria(
  token: string,
  filtros?: { modelo?: string; objeto_id?: number }
): Promise<RegistroAuditoria[]> {
  const parametros = new URLSearchParams();
  if (filtros?.modelo) parametros.set("modelo", filtros.modelo);
  if (filtros?.objeto_id) parametros.set("objeto_id", String(filtros.objeto_id));
  const query = parametros.toString();
  return request<RegistroAuditoria[]>(`/api/contratistas/auditoria/${query ? `?${query}` : ""}`, {
    headers: authHeaders(token),
  });
}

export function exportarAuditoriaExcel(
  token: string,
  filtros?: { modelo?: string; objeto_id?: number }
): Promise<void> {
  const parametros = new URLSearchParams();
  if (filtros?.modelo) parametros.set("modelo", filtros.modelo);
  if (filtros?.objeto_id) parametros.set("objeto_id", String(filtros.objeto_id));
  const query = parametros.toString();
  return descargarArchivo(
    token,
    `/api/contratistas/auditoria/exportar/${query ? `?${query}` : ""}`,
    "auditoria.xlsx"
  );
}

export type RegistroInicioSesion = {
  id: number;
  usuario: number | null;
  usuario_nombre: string;
  username_intentado: string;
  ip: string | null;
  user_agent: string;
  exitoso: boolean;
  fecha: string;
};

type FiltrosInicioSesion = { usuario?: number; exitoso?: boolean; desde?: string; hasta?: string };

function paramsInicioSesion(filtros?: FiltrosInicioSesion): URLSearchParams {
  const parametros = new URLSearchParams();
  if (filtros?.usuario !== undefined) parametros.set("usuario", String(filtros.usuario));
  if (filtros?.exitoso !== undefined) parametros.set("exitoso", String(filtros.exitoso));
  if (filtros?.desde) parametros.set("desde", filtros.desde);
  if (filtros?.hasta) parametros.set("hasta", filtros.hasta);
  return parametros;
}

export function listarInicioSesion(
  token: string,
  filtros?: FiltrosInicioSesion
): Promise<RegistroInicioSesion[]> {
  const query = paramsInicioSesion(filtros).toString();
  return request<RegistroInicioSesion[]>(`/api/auth/inicios-sesion/${query ? `?${query}` : ""}`, {
    headers: authHeaders(token),
  });
}

export function exportarInicioSesionExcel(token: string, filtros?: FiltrosInicioSesion): Promise<void> {
  const query = paramsInicioSesion(filtros).toString();
  return descargarArchivo(
    token,
    `/api/auth/inicios-sesion/exportar/${query ? `?${query}` : ""}`,
    "inicios_de_sesion.xlsx"
  );
}

export type TipoNotificacionInterna =
  | "declaracion_pendiente"
  | "declaracion_subsanada"
  | "radicacion_pendiente";

export type NotificacionInterna = {
  id: number;
  tipo: TipoNotificacionInterna;
  tipo_display: string;
  mensaje: string;
  modelo: string;
  objeto_id: number;
  leida: boolean;
  creada_en: string;
};

export function listarNotificacionesInternas(
  token: string,
  filtros?: { leida?: boolean }
): Promise<NotificacionInterna[]> {
  const parametros = new URLSearchParams();
  if (filtros?.leida !== undefined) parametros.set("leida", filtros.leida ? "1" : "0");
  const query = parametros.toString();
  return request<NotificacionInterna[]>(
    `/api/contratistas/notificaciones-internas/${query ? `?${query}` : ""}`,
    { headers: authHeaders(token) }
  );
}

export function marcarNotificacionLeida(token: string, id: number): Promise<NotificacionInterna> {
  return request<NotificacionInterna>(`/api/contratistas/notificaciones-internas/${id}/marcar-leida/`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export function marcarTodasNotificacionesLeidas(token: string): Promise<void> {
  return request<void>("/api/contratistas/notificaciones-internas/marcar-todas-leidas/", {
    method: "POST",
    headers: authHeaders(token),
  });
}

export function eliminarNotificacionInterna(token: string, id: number): Promise<void> {
  return request<void>(`/api/contratistas/notificaciones-internas/${id}/`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export function eliminarNotificacionesInternasLeidas(token: string): Promise<void> {
  return request<void>("/api/contratistas/notificaciones-internas/eliminar-leidas/", {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export type EmpresaContratista = {
  id: number;
  nombre: string;
  nit: string;
  contacto_nombre: string;
  contacto_telefono: string;
  contacto_correo: string;
  responsable_sst_nombre: string;
  responsable_sst_telefono: string;
  activa: boolean;
  capacitacion_habilitada_manual: boolean;
  capacitacion_habilitada: boolean;
  creada_en: string;
  trabajadores_count: number;
};

export type NuevaEmpresaContratista = Omit<
  EmpresaContratista,
  "id" | "creada_en" | "trabajadores_count" | "capacitacion_habilitada"
>;

export function listarContratistas(token: string): Promise<EmpresaContratista[]> {
  return request<EmpresaContratista[]>("/api/contratistas/empresas/", { headers: authHeaders(token) });
}

export function crearContratista(
  token: string,
  datos: Partial<NuevaEmpresaContratista>
): Promise<EmpresaContratista> {
  return request<EmpresaContratista>("/api/contratistas/empresas/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarContratista(
  token: string,
  id: number,
  cambios: Partial<NuevaEmpresaContratista>
): Promise<EmpresaContratista> {
  return request<EmpresaContratista>(`/api/contratistas/empresas/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export type TipoVinculacion = "fijo" | "temporal";

export type RadicacionResumen = {
  id: number;
  anio: number;
  mes: string;
  estado: EstadoRadicacion;
  fecha_vencimiento: string | null;
  vencida: boolean;
  dias_para_vencer: number | null;
};

export type Trabajador = {
  id: number;
  contratista: number;
  contratista_nombre: string;
  nombres: string;
  apellidos: string;
  documento: string;
  eps: string;
  arl: string;
  afp: string;
  tipo_vinculacion: TipoVinculacion;
  fecha_inicio_contrato: string | null;
  cursos_safety_academy: Record<string, string | null>;
  cursos_pendientes: Opcion[];
  fecha_vencimiento_examen_medico: string | null;
  examen_medico_vencido: boolean;
  dias_para_vencer_examen_medico: number | null;
  fecha_vencimiento_certificacion_alturas: string | null;
  certificacion_alturas_vencida: boolean;
  dias_para_vencer_certificacion_alturas: number | null;
  activo: boolean;
  creado_en: string;
  autorizacion_datos: boolean;
  autorizacion_datos_en: string | null;
  soporte_autorizacion_datos: string | null;
  ultima_radicacion: RadicacionResumen | null;
};

export type NuevoTrabajador = {
  contratista: number;
  nombres: string;
  apellidos: string;
  documento: string;
  eps?: string;
  arl?: string;
  afp?: string;
  tipo_vinculacion?: TipoVinculacion;
  fecha_inicio_contrato?: string | null;
  cursos_safety_academy?: Record<string, string | null>;
  fecha_vencimiento_examen_medico?: string | null;
  fecha_vencimiento_certificacion_alturas?: string | null;
  activo?: boolean;
  autorizacion_datos: boolean;
};

export function listarTrabajadores(token: string, contratistaId?: number): Promise<Trabajador[]> {
  const query = contratistaId ? `?contratista=${contratistaId}` : "";
  return request<Trabajador[]>(`/api/contratistas/trabajadores/${query}`, { headers: authHeaders(token) });
}

function datosTrabajadorFormData(datos: NuevoTrabajador | Partial<NuevoTrabajador>, evidencia: File): FormData {
  const formData = new FormData();
  Object.entries(datos).forEach(([clave, valor]) => {
    if (valor === undefined || valor === null) return;
    formData.append(clave, typeof valor === "object" ? JSON.stringify(valor) : String(valor));
  });
  formData.append("soporte_autorizacion_datos", evidencia);
  return formData;
}

export function crearTrabajador(token: string, datos: NuevoTrabajador, evidencia?: File): Promise<Trabajador> {
  return request<Trabajador>("/api/contratistas/trabajadores/", {
    method: "POST",
    headers: authHeaders(token),
    body: evidencia ? datosTrabajadorFormData(datos, evidencia) : JSON.stringify(datos),
  });
}

export function actualizarTrabajador(
  token: string,
  id: number,
  cambios: Partial<NuevoTrabajador>,
  evidencia?: File
): Promise<Trabajador> {
  return request<Trabajador>(`/api/contratistas/trabajadores/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: evidencia ? datosTrabajadorFormData(cambios, evidencia) : JSON.stringify(cambios),
  });
}

export type EstadoRadicacion = "pendiente" | "aprobada" | "rechazada";

export type RadicacionSeguridadSocial = {
  id: number;
  trabajador: number;
  trabajador_nombre: string;
  contratista_nombre: string;
  anio: number;
  mes: string;
  numero_planilla: string;
  fecha_vencimiento: string | null;
  vencida: boolean;
  dias_para_vencer: number | null;
  soporte_pago: string | null;
  interventor: string;
  estado: EstadoRadicacion;
  observaciones: string;
  radicada_en: string;
  revisada_en: string | null;
};

export type NuevaRadicacion = {
  trabajador: number;
  anio: number;
  mes: string;
  numero_planilla?: string;
  fecha_vencimiento?: string | null;
  interventor?: string;
};

type FiltrosRadicaciones = {
  trabajador?: number;
  contratista?: number;
  estado?: EstadoRadicacion;
  vencida?: boolean;
};

function paramsRadicaciones(filtros: FiltrosRadicaciones): URLSearchParams {
  const params = new URLSearchParams();
  if (filtros.trabajador !== undefined) params.set("trabajador", String(filtros.trabajador));
  if (filtros.contratista !== undefined) params.set("contratista", String(filtros.contratista));
  if (filtros.estado) params.set("estado", filtros.estado);
  if (filtros.vencida !== undefined) params.set("vencida", String(filtros.vencida));
  return params;
}

export function listarRadicaciones(
  token: string,
  filtros: FiltrosRadicaciones = {}
): Promise<RadicacionSeguridadSocial[]> {
  const query = paramsRadicaciones(filtros).toString();
  return request<RadicacionSeguridadSocial[]>(`/api/contratistas/radicaciones/${query ? `?${query}` : ""}`, {
    headers: authHeaders(token),
  });
}

async function descargarArchivo(token: string, ruta: string, nombreArchivo: string): Promise<void> {
  const respuesta = await fetch(`${API_URL}${ruta}`, { headers: authHeaders(token) });
  if (!respuesta.ok) {
    throw new ApiError("No se pudo generar el archivo.", respuesta.status);
  }
  const blob = await respuesta.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}

export function exportarRadicacionesExcel(token: string, filtros: FiltrosRadicaciones = {}): Promise<void> {
  const query = paramsRadicaciones(filtros).toString();
  return descargarArchivo(
    token,
    `/api/contratistas/radicaciones/exportar/${query ? `?${query}` : ""}`,
    "radicaciones_seguridad_social.xlsx"
  );
}

export type IndicadoresContratistas = {
  radicaciones_vencidas: number;
  radicaciones_por_vencer: number;
  examenes_medicos_vencidos: number;
  examenes_medicos_por_vencer: number;
  certificaciones_alturas_vencidas: number;
  certificaciones_alturas_por_vencer: number;
};

export function obtenerIndicadoresContratistas(token: string): Promise<IndicadoresContratistas> {
  return request<IndicadoresContratistas>("/api/contratistas/indicadores/", { headers: authHeaders(token) });
}

export type TopRiesgo = {
  declaracion_id: number;
  contratista: string;
  secuencia: string;
  riesgo_sin: number;
  nivel_sin: string;
  riesgo_con: number;
};

export type ContratistaResumen = {
  contratista: string;
  trabajadores: number;
  radicaciones_pendientes: number;
  declaraciones_pendientes: number;
};

export type MesResumen = {
  mes: string;
  declaraciones: number;
  radicaciones: number;
};

export type IndicadoresDashboard = {
  contratistas_activos: number;
  trabajadores_activos: number;
  trabajadores_con_cursos_pendientes: number;
  radicaciones_por_estado: Record<EstadoRadicacion, number>;
  declaraciones_por_estado: Record<EstadoDeclaracion, number>;
  riesgo_promedio_sin: number;
  riesgo_promedio_con: number;
  top_riesgos: TopRiesgo[];
  tiempo_promedio_aprobacion_dias: number | null;
  por_contratista: ContratistaResumen[];
  tendencia_mensual: MesResumen[];
};

export function obtenerIndicadoresDashboard(token: string): Promise<IndicadoresDashboard> {
  return request<IndicadoresDashboard>("/api/contratistas/indicadores/dashboard/", { headers: authHeaders(token) });
}

export function crearRadicacion(
  token: string,
  datos: NuevaRadicacion,
  soporte?: File
): Promise<RadicacionSeguridadSocial> {
  if (soporte) {
    const formData = new FormData();
    Object.entries(datos).forEach(([clave, valor]) => {
      if (valor !== undefined && valor !== null) formData.append(clave, String(valor));
    });
    formData.append("soporte_pago", soporte);
    return request<RadicacionSeguridadSocial>("/api/contratistas/radicaciones/", {
      method: "POST",
      headers: authHeaders(token),
      body: formData,
    });
  }
  return request<RadicacionSeguridadSocial>("/api/contratistas/radicaciones/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function aprobarRadicacion(
  token: string,
  id: number,
  observaciones = ""
): Promise<RadicacionSeguridadSocial> {
  return request<RadicacionSeguridadSocial>(`/api/contratistas/radicaciones/${id}/aprobar/`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ observaciones }),
  });
}

export function rechazarRadicacion(
  token: string,
  id: number,
  observaciones = ""
): Promise<RadicacionSeguridadSocial> {
  return request<RadicacionSeguridadSocial>(`/api/contratistas/radicaciones/${id}/rechazar/`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ observaciones }),
  });
}

export type NivelRiesgo = { clave: string; etiqueta: string };

export type ActividadMetodo = {
  id: number;
  orden: number;
  secuencia: string;
  tecnicas_herramientas: string;
  descripcion_riesgo: string;
  probabilidad_sin: number;
  frecuencia_sin: number;
  impacto_sin: number;
  riesgo_sin: number;
  nivel_riesgo_sin: NivelRiesgo;
  medidas_mitigacion: string;
  probabilidad_con: number;
  frecuencia_con: number;
  impacto_con: number;
  riesgo_con: number;
  nivel_riesgo_con: NivelRiesgo;
  permisos_requeridos: string[];
  epp_requerido: string[];
  tarea_sif: boolean;
  altura_trabajo_metros: number | null;
  profundidad_excavacion_metros: number | null;
};

export type NuevaActividadMetodo = Omit<
  ActividadMetodo,
  "id" | "riesgo_sin" | "nivel_riesgo_sin" | "riesgo_con" | "nivel_riesgo_con"
>;

export type RolFirma =
  | "supervisor_contratista"
  | "delegado_abi"
  | "seguridad_planta"
  | "lider_area"
  | "dueno_territorio";

export type FirmaMetodo = {
  id: number;
  rol: RolFirma;
  rol_display: string;
  nombre_firmante: string;
  firmante_usuario_nombre: string;
  hash_documento: string;
  documento_modificado_despues_de_firmar: boolean;
  firmado_en: string;
};

export type RolFuncionario = Exclude<RolFirma, "supervisor_contratista">;

export type Funcionario = {
  id: number;
  nombre: string;
  cargo: string;
  rol_firma: RolFuncionario;
  rol_firma_display: string;
  correo: string;
  telefono: string;
  activo: boolean;
  creado_en: string;
};

export type NuevoFuncionario = {
  nombre: string;
  cargo?: string;
  rol_firma: RolFuncionario;
  correo?: string;
  telefono?: string;
  activo?: boolean;
};

export function listarFuncionarios(
  token: string,
  filtros: { rol_firma?: RolFuncionario; activo?: boolean } = {}
): Promise<Funcionario[]> {
  const params = new URLSearchParams();
  if (filtros.rol_firma) params.set("rol_firma", filtros.rol_firma);
  if (filtros.activo !== undefined) params.set("activo", String(filtros.activo));
  const query = params.toString();
  return request<Funcionario[]>(`/api/contratistas/funcionarios/${query ? `?${query}` : ""}`, {
    headers: authHeaders(token),
  });
}

export function crearFuncionario(token: string, datos: NuevoFuncionario): Promise<Funcionario> {
  return request<Funcionario>("/api/contratistas/funcionarios/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarFuncionario(
  token: string,
  id: number,
  cambios: Partial<NuevoFuncionario>
): Promise<Funcionario> {
  return request<Funcionario>(`/api/contratistas/funcionarios/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function eliminarFuncionario(token: string, id: number): Promise<void> {
  return request<void>(`/api/contratistas/funcionarios/${id}/`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export type EstadoDeclaracion = "borrador" | "enviada" | "aprobada" | "rechazada";

export type DeclaracionMetodo = {
  id: number;
  contratista: number;
  contratista_nombre: string;
  planta_area: string;
  numero_pedido: string;
  gerente_proyecto: string;
  contacto_nombre: string;
  contacto_telefono: string;
  fecha_elaboracion: string;
  duracion_dias: number;
  descripcion_trabajo: string;
  estado: EstadoDeclaracion;
  observaciones: string;
  archivo_origen_excel: string | null;
  creada_en: string;
  actualizada_en: string;
  actividades: ActividadMetodo[];
  firmas: FirmaMetodo[];
};

export type NuevaDeclaracion = {
  contratista: number;
  planta_area?: string;
  numero_pedido?: string;
  gerente_proyecto?: string;
  contacto_nombre?: string;
  contacto_telefono?: string;
  fecha_elaboracion: string;
  duracion_dias?: number;
  descripcion_trabajo: string;
  estado?: EstadoDeclaracion;
  observaciones?: string;
  actividades?: Partial<NuevaActividadMetodo>[];
};

export type DeclaracionImportadaExcel = {
  planta_area: string;
  numero_pedido: string;
  gerente_proyecto: string;
  contacto_telefono: string;
  fecha_elaboracion: string | null;
  duracion_dias: number;
  descripcion_trabajo: string;
  actividades: NuevaActividadMetodo[];
  avisos: string[];
};

export function importarDeclaracionExcel(token: string, archivo: File): Promise<DeclaracionImportadaExcel> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  return request<DeclaracionImportadaExcel>("/api/contratistas/declaraciones/importar-excel/", {
    method: "POST",
    headers: authHeaders(token),
    body: formData,
  });
}

export function subirArchivoOrigenDeclaracion(
  token: string,
  id: number,
  archivo: File
): Promise<DeclaracionMetodo> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  return request<DeclaracionMetodo>(`/api/contratistas/declaraciones/${id}/archivo-origen/`, {
    method: "POST",
    headers: authHeaders(token),
    body: formData,
  });
}

export function listarDeclaraciones(
  token: string,
  filtros: { contratista?: number; estado?: EstadoDeclaracion } = {}
): Promise<DeclaracionMetodo[]> {
  const params = new URLSearchParams();
  if (filtros.contratista !== undefined) params.set("contratista", String(filtros.contratista));
  if (filtros.estado) params.set("estado", filtros.estado);
  const query = params.toString();
  return request<DeclaracionMetodo[]>(`/api/contratistas/declaraciones/${query ? `?${query}` : ""}`, {
    headers: authHeaders(token),
  });
}

export function obtenerDeclaracion(token: string, id: number): Promise<DeclaracionMetodo> {
  return request<DeclaracionMetodo>(`/api/contratistas/declaraciones/${id}/`, {
    headers: authHeaders(token),
  });
}

export function crearDeclaracion(token: string, datos: NuevaDeclaracion): Promise<DeclaracionMetodo> {
  return request<DeclaracionMetodo>("/api/contratistas/declaraciones/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarDeclaracion(
  token: string,
  id: number,
  cambios: Partial<NuevaDeclaracion>
): Promise<DeclaracionMetodo> {
  return request<DeclaracionMetodo>(`/api/contratistas/declaraciones/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function firmarDeclaracion(
  token: string,
  id: number,
  datos: { rol: RolFirma; nombre_firmante: string; consiento_firma: boolean }
): Promise<FirmaMetodo> {
  return request<FirmaMetodo>(`/api/contratistas/declaraciones/${id}/firmar/`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function descargarDeclaracionPdf(token: string, id: number): Promise<void> {
  return descargarArchivo(token, `/api/contratistas/declaraciones/${id}/pdf/`, `declaracion-metodo-${id}.pdf`);
}

export function descargarDeclaracionExcel(token: string, id: number): Promise<void> {
  return descargarArchivo(token, `/api/contratistas/declaraciones/${id}/excel/`, `declaracion-metodo-${id}.xlsx`);
}

export function eliminarDeclaracion(token: string, id: number): Promise<void> {
  return request<void>(`/api/contratistas/declaraciones/${id}/`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export type AlertaAutomatica = {
  codigo: string;
  actividad_id: number;
  actividad_orden: number;
  titulo: string;
  mensaje: string;
  motivo_sugerido: string;
  fuente: string;
};

export function listarAlertasDeclaracion(token: string, id: number): Promise<AlertaAutomatica[]> {
  return request<AlertaAutomatica[]>(`/api/contratistas/declaraciones/${id}/alertas/`, {
    headers: authHeaders(token),
  });
}

export type NotaAlerta = {
  id: number;
  codigo_alerta: string;
  actividad_orden: number;
  autor_nombre: string;
  texto: string;
  creada_en: string;
};

export function listarNotasAlertas(token: string, id: number): Promise<NotaAlerta[]> {
  return request<NotaAlerta[]>(`/api/contratistas/declaraciones/${id}/notas-alertas/`, {
    headers: authHeaders(token),
  });
}

export function crearNotaAlerta(
  token: string,
  id: number,
  datos: { codigo_alerta: string; actividad_orden: number; texto: string }
): Promise<NotaAlerta> {
  return request<NotaAlerta>(`/api/contratistas/declaraciones/${id}/notas-alertas/`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export type TrabajadorAutorizacionIngreso = {
  id: number;
  trabajador: number;
  trabajador_nombre: string;
  trabajador_documento: string;
  incluido: boolean;
  motivo_exclusion: string;
};

export type NuevoTrabajadorAutorizacionIngreso = Omit<
  TrabajadorAutorizacionIngreso,
  "id" | "trabajador_nombre" | "trabajador_documento"
>;

export type AutorizacionIngreso = {
  id: number;
  contratista: number;
  contratista_nombre: string;
  declaracion: number | null;
  fecha_inicio: string;
  fecha_fin: string;
  hora_inicio: string | null;
  hora_fin: string | null;
  area_trabajo: string;
  sitio_encuentro_emergencia: string;
  responsable_siso_nombre: string;
  responsable_siso_cargo: string;
  responsable_siso_telefono: string;
  estado: EstadoDeclaracion;
  observaciones: string;
  vigente: boolean;
  creada_en: string;
  actualizada_en: string;
  trabajadores: TrabajadorAutorizacionIngreso[];
};

export type NuevaAutorizacionIngreso = {
  contratista: number;
  declaracion?: number | null;
  fecha_inicio: string;
  fecha_fin: string;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  area_trabajo: string;
  sitio_encuentro_emergencia?: string;
  responsable_siso_nombre: string;
  responsable_siso_cargo?: string;
  responsable_siso_telefono?: string;
  estado?: EstadoDeclaracion;
  observaciones?: string;
  trabajadores?: Partial<NuevoTrabajadorAutorizacionIngreso>[];
};

export function listarAutorizacionesIngreso(
  token: string,
  filtros: { contratista?: number; estado?: EstadoDeclaracion } = {}
): Promise<AutorizacionIngreso[]> {
  const params = new URLSearchParams();
  if (filtros.contratista !== undefined) params.set("contratista", String(filtros.contratista));
  if (filtros.estado) params.set("estado", filtros.estado);
  const query = params.toString();
  return request<AutorizacionIngreso[]>(`/api/contratistas/autorizaciones-ingreso/${query ? `?${query}` : ""}`, {
    headers: authHeaders(token),
  });
}

export function crearAutorizacionIngreso(
  token: string,
  datos: NuevaAutorizacionIngreso
): Promise<AutorizacionIngreso> {
  return request<AutorizacionIngreso>("/api/contratistas/autorizaciones-ingreso/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarAutorizacionIngreso(
  token: string,
  id: number,
  cambios: Partial<NuevaAutorizacionIngreso>
): Promise<AutorizacionIngreso> {
  return request<AutorizacionIngreso>(`/api/contratistas/autorizaciones-ingreso/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function eliminarAutorizacionIngreso(token: string, id: number): Promise<void> {
  return request<void>(`/api/contratistas/autorizaciones-ingreso/${id}/`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export function descargarAutorizacionIngresoPdf(token: string, id: number): Promise<void> {
  return descargarArchivo(
    token,
    `/api/contratistas/autorizaciones-ingreso/${id}/pdf/`,
    `autorizacion-ingreso-${id}.pdf`
  );
}

// --- Capacitación previa a ingreso ---

export type ConfiguracionCapacitacion = {
  titulo_curso: string;
  video_url: string;
  puntaje_minimo_aprobacion: number;
  actualizada_en: string;
};

export type PreguntaCapacitacion = {
  id: number;
  texto: string;
  opciones: string[];
  orden: number;
};

export type EstadoCapacitacion = "en_curso" | "aprobado" | "no_aprobado";

export type RegistroCapacitacion = {
  id: number;
  contratista: number;
  contratista_nombre: string;
  trabajador: number | null;
  trabajador_nombre: string;
  nombres: string;
  correo: string;
  documento: string;
  calificacion: number | null;
  estado: EstadoCapacitacion;
  estado_display: string;
  iniciado_en: string;
  finalizado_en: string | null;
};

export type ResultadoCapacitacion = RegistroCapacitacion & {
  correctas: number;
  total: number;
};

export function obtenerConfiguracionCapacitacion(token: string): Promise<ConfiguracionCapacitacion> {
  return request<ConfiguracionCapacitacion>("/api/contratistas/capacitacion/configuracion/", {
    headers: authHeaders(token),
  });
}

export function actualizarConfiguracionCapacitacion(
  token: string,
  cambios: Partial<Pick<ConfiguracionCapacitacion, "titulo_curso" | "video_url" | "puntaje_minimo_aprobacion">>
): Promise<ConfiguracionCapacitacion> {
  return request<ConfiguracionCapacitacion>("/api/contratistas/capacitacion/configuracion/", {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
  });
}

export function listarPreguntasCapacitacion(token: string): Promise<PreguntaCapacitacion[]> {
  return request<PreguntaCapacitacion[]>("/api/contratistas/capacitacion/preguntas/", {
    headers: authHeaders(token),
  });
}

export function listarRegistrosCapacitacion(
  token: string,
  contratistaId?: number
): Promise<RegistroCapacitacion[]> {
  const query = contratistaId ? `?contratista=${contratistaId}` : "";
  return request<RegistroCapacitacion[]>(`/api/contratistas/capacitacion/registros/${query}`, {
    headers: authHeaders(token),
  });
}

export function iniciarCapacitacion(
  token: string,
  datos: { contratista?: number; nombres: string; correo?: string; documento?: string }
): Promise<RegistroCapacitacion> {
  return request<RegistroCapacitacion>("/api/contratistas/capacitacion/iniciar/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function calificarCapacitacion(
  token: string,
  id: number,
  respuestas: number[]
): Promise<ResultadoCapacitacion> {
  return request<ResultadoCapacitacion>(`/api/contratistas/capacitacion/${id}/calificar/`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ respuestas }),
  });
}

export function descargarCertificadoCapacitacion(token: string, id: number): Promise<void> {
  return descargarArchivo(token, `/api/contratistas/capacitacion/${id}/certificado/`, `certificado-capacitacion-${id}.pdf`);
}

export function exportarCapacitacionesAprobadasExcel(token: string, contratistaId?: number): Promise<void> {
  const query = contratistaId ? `?contratista=${contratistaId}` : "";
  return descargarArchivo(
    token,
    `/api/contratistas/capacitacion/exportar/${query}`,
    "capacitacion_aprobados.xlsx"
  );
}
