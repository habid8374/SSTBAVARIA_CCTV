from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import PerfilUsuario


class EsAdministrador(BasePermission):
    """Solo usuarios con rol Administrador (o superusuario de Django)."""

    message = "Se requiere rol de administrador."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        perfil = getattr(user, "perfil", None)
        return bool(perfil and perfil.rol == PerfilUsuario.Rol.ADMINISTRADOR)


class EsSuperusuario(BasePermission):
    """Solo el superusuario real de Django (`is_superuser`) — a diferencia
    de EsAdministrador, el rol Administrador de PerfilUsuario NO alcanza acá.
    Para lo más sensible del sistema (auditoría de quién se conectó desde
    qué IP y trazabilidad de aprobaciones/rechazos): ni siquiera otro
    Administrador debería poder verlo, solo el dueño de la cuenta."""

    message = "Solo el superusuario puede ver esto."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


class EsAdministradorOSoloLectura(BasePermission):
    """Cualquier usuario autenticado puede leer (GET); escribir requiere rol
    Administrador — para configuración (zonas, reglas) que un Operador puede
    consultar pero no modificar."""

    message = "Se requiere rol de administrador para modificar esto."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return EsAdministrador().has_permission(request, view)


class EsAdministradorParaEliminar(BasePermission):
    """Cualquier usuario autenticado puede crear/leer/editar; eliminar (acción
    destructiva e irreversible) requiere rol Administrador — para datos
    operativos (contratistas, trabajadores, declaraciones) que un Operador
    llena en el día a día pero no debería poder borrar."""

    message = "Se requiere rol de administrador para eliminar esto."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method != "DELETE":
            return True
        return EsAdministrador().has_permission(request, view)


class EsPersonalInterno(BasePermission):
    """Solo Administrador u Operador — nunca Contratista. Para secciones que
    no le competen al portal de contratistas: cámaras, sistema, usuarios,
    padrón de funcionarios firmantes, indicadores comparativos entre
    empresas y auditoría."""

    message = "Esta sección es solo para el personal de SST/interventoría."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        perfil = getattr(user, "perfil", None)
        return bool(perfil and perfil.es_interno)


class EsPersonalInternoOSoloLectura(BasePermission):
    """Cualquier usuario autenticado puede leer (GET); crear/editar requiere
    ser personal interno (Administrador u Operador) — para datos que un
    usuario del portal de contratistas puede consultar sobre su propia
    empresa (queryset ya filtrado en la vista) pero no modificar."""

    message = "Esta acción es solo para el personal de SST/interventoría."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return EsPersonalInterno().has_permission(request, view)
