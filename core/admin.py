from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Empresa, PerfilUsuario, RegistroInicioSesion, SuscripcionPush

Usuario = get_user_model()


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nit", "contacto_nombre", "contacto_telefono", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre", "nit")


class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False


class UsuarioAdmin(DjangoUserAdmin):
    inlines = [PerfilUsuarioInline]
    list_display = DjangoUserAdmin.list_display + ("rol",)

    def get_inline_instances(self, request, obj=None):
        # En "Agregar usuario" el usuario todavía no existe -> el inline no
        # tiene a qué PerfilUsuario apuntar. La señal crear_perfil_usuario ya
        # crea uno automáticamente en cuanto se guarda el User; si además se
        # muestra el inline acá, Django intenta insertar un segundo
        # PerfilUsuario para el mismo usuario_id y revienta con
        # UniqueViolation. Se oculta en "agregar" y se deja para "editar",
        # donde el perfil ya existe de verdad.
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    @admin.display(description="rol")
    def rol(self, obj):
        return obj.perfil.get_rol_display() if hasattr(obj, "perfil") else "—"


admin.site.unregister(Usuario)
admin.site.register(Usuario, UsuarioAdmin)


@admin.register(SuscripcionPush)
class SuscripcionPushAdmin(admin.ModelAdmin):
    list_display = ("usuario", "endpoint", "creada_en")
    list_filter = ("usuario",)
    readonly_fields = ("endpoint", "p256dh", "auth", "creada_en")


@admin.register(RegistroInicioSesion)
class RegistroInicioSesionAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "username_intentado", "ip", "exitoso")
    list_filter = ("exitoso",)
    search_fields = ("username_intentado", "ip")
    readonly_fields = ("usuario", "username_intentado", "ip", "user_agent", "exitoso", "fecha")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
