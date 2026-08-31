const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

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

export type Rol = "administrador" | "operador";

export type Usuario = {
  id: number;
  username: string;
  nombre: string;
  email: string;
  is_staff: boolean;
  rol: Rol | null;
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
  date_joined: string;
};

export type NuevoUsuario = {
  username: string;
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  rol: Rol;
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
  cambios: Partial<Pick<UsuarioGestionado, "rol" | "is_active" | "first_name" | "last_name" | "email">>
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
  filtros: { estado?: EstadoEvento; disparo_alerta?: boolean; camara?: number } = {}
): Promise<EventoDashboard[]> {
  const params = new URLSearchParams();
  if (filtros.estado) params.set("estado", filtros.estado);
  if (filtros.disparo_alerta !== undefined) params.set("disparo_alerta", String(filtros.disparo_alerta));
  if (filtros.camara !== undefined) params.set("camara", String(filtros.camara));
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

// --- Contratistas: empresas, trabajadores, seguridad social, declaración de método ---

export type Opcion = { clave: string; etiqueta: string };

export type Catalogos = {
  cursos_safety_academy: Opcion[];
  permisos_trabajo: string[];
  roles_firma: Opcion[];
};

export function obtenerCatalogosContratistas(token: string): Promise<Catalogos> {
  return request<Catalogos>("/api/contratistas/catalogos/", { headers: authHeaders(token) });
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
  creada_en: string;
  trabajadores_count: number;
};

export type NuevaEmpresaContratista = Omit<
  EmpresaContratista,
  "id" | "creada_en" | "trabajadores_count"
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
  activo: boolean;
  creado_en: string;
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
  activo?: boolean;
};

export function listarTrabajadores(token: string, contratistaId?: number): Promise<Trabajador[]> {
  const query = contratistaId ? `?contratista=${contratistaId}` : "";
  return request<Trabajador[]>(`/api/contratistas/trabajadores/${query}`, { headers: authHeaders(token) });
}

export function crearTrabajador(token: string, datos: NuevoTrabajador): Promise<Trabajador> {
  return request<Trabajador>("/api/contratistas/trabajadores/", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}

export function actualizarTrabajador(
  token: string,
  id: number,
  cambios: Partial<NuevoTrabajador>
): Promise<Trabajador> {
  return request<Trabajador>(`/api/contratistas/trabajadores/${id}/`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(cambios),
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

export function listarRadicaciones(
  token: string,
  filtros: { trabajador?: number; contratista?: number; estado?: EstadoRadicacion } = {}
): Promise<RadicacionSeguridadSocial[]> {
  const params = new URLSearchParams();
  if (filtros.trabajador !== undefined) params.set("trabajador", String(filtros.trabajador));
  if (filtros.contratista !== undefined) params.set("contratista", String(filtros.contratista));
  if (filtros.estado) params.set("estado", filtros.estado);
  const query = params.toString();
  return request<RadicacionSeguridadSocial[]>(`/api/contratistas/radicaciones/${query ? `?${query}` : ""}`, {
    headers: authHeaders(token),
  });
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
  tarea_sif: boolean;
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
  firmado_en: string;
};

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
  datos: { rol: RolFirma; nombre_firmante: string }
): Promise<FirmaMetodo> {
  return request<FirmaMetodo>(`/api/contratistas/declaraciones/${id}/firmar/`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(datos),
  });
}
