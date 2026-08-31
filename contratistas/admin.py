from django.contrib import admin

from .models import (
    ActividadMetodo,
    ConfiguracionAlertas,
    CursoSafetyAcademy,
    DeclaracionMetodo,
    EmpresaContratista,
    FirmaMetodo,
    Funcionario,
    PermisoTrabajo,
    RadicacionSeguridadSocial,
    Trabajador,
)


class TrabajadorInline(admin.TabularInline):
    model = Trabajador
    extra = 0
    show_change_link = True


@admin.register(EmpresaContratista)
class EmpresaContratistaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nit", "empresa", "responsable_sst_nombre", "activa")
    list_filter = ("empresa", "activa")
    search_fields = ("nombre", "nit")
    inlines = [TrabajadorInline]


class RadicacionSeguridadSocialInline(admin.TabularInline):
    model = RadicacionSeguridadSocial
    extra = 0
    show_change_link = True


@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ("apellidos", "nombres", "documento", "contratista", "tipo_vinculacion", "activo")
    list_filter = ("contratista", "tipo_vinculacion", "activo")
    search_fields = ("nombres", "apellidos", "documento")
    inlines = [RadicacionSeguridadSocialInline]


@admin.register(RadicacionSeguridadSocial)
class RadicacionSeguridadSocialAdmin(admin.ModelAdmin):
    list_display = ("trabajador", "anio", "mes", "numero_planilla", "estado", "radicada_en")
    list_filter = ("estado", "anio", "mes")
    search_fields = ("trabajador__nombres", "trabajador__apellidos", "numero_planilla")
    readonly_fields = ("radicada_en",)


class ActividadMetodoInline(admin.StackedInline):
    model = ActividadMetodo
    extra = 0
    show_change_link = True


class FirmaMetodoInline(admin.TabularInline):
    model = FirmaMetodo
    extra = 0


@admin.register(DeclaracionMetodo)
class DeclaracionMetodoAdmin(admin.ModelAdmin):
    list_display = ("descripcion_trabajo", "contratista", "fecha_elaboracion", "estado")
    list_filter = ("estado", "contratista")
    search_fields = ("descripcion_trabajo", "numero_pedido")
    inlines = [ActividadMetodoInline, FirmaMetodoInline]


@admin.register(ActividadMetodo)
class ActividadMetodoAdmin(admin.ModelAdmin):
    list_display = ("declaracion", "orden", "secuencia", "riesgo_sin", "riesgo_con", "tarea_sif")
    list_filter = ("tarea_sif",)


@admin.register(FirmaMetodo)
class FirmaMetodoAdmin(admin.ModelAdmin):
    list_display = ("declaracion", "rol", "nombre_firmante", "firmante_usuario", "firmado_en")
    list_filter = ("rol",)
    readonly_fields = ("firmado_en", "hash_documento")


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cargo", "rol_firma", "correo", "activo")
    list_filter = ("rol_firma", "activo")
    search_fields = ("nombre", "cargo", "correo")


@admin.register(CursoSafetyAcademy)
class CursoSafetyAcademyAdmin(admin.ModelAdmin):
    list_display = ("etiqueta", "clave", "activo", "orden")
    list_editable = ("activo", "orden")


@admin.register(PermisoTrabajo)
class PermisoTrabajoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "orden")
    list_editable = ("activo", "orden")


@admin.register(ConfiguracionAlertas)
class ConfiguracionAlertasAdmin(admin.ModelAdmin):
    list_display = ("dias_alerta_vencimiento", "actualizada_en")
