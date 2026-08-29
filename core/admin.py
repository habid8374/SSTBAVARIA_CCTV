from django.contrib import admin

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nit", "contacto_nombre", "contacto_telefono", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre", "nit")
