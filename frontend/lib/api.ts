const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
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
