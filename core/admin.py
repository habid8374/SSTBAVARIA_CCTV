from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Empresa, PerfilUsuario

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

    @admin.display(description="rol")
    def rol(self, obj):
        return obj.perfil.get_rol_display() if hasattr(obj, "perfil") else "—"


admin.site.unregister(Usuario)
admin.site.register(Usuario, UsuarioAdmin)
