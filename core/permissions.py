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
