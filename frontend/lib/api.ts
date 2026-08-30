const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
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
      detail = body.detail ?? detail;
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
