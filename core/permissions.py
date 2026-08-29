from rest_framework.permissions import BasePermission

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
