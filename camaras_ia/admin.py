from django.contrib import admin

from .models import (
    Camara,
    ConfiguracionIA,
    ConfiguracionNotificaciones,
    EquipoLocal,
    EventoDetectado,
    InstruccionSeguridad,
    ReglaAlerta,
    TipoEventoIA,
    ZonaRestringida,
)


class ReglaAlertaInline(admin.TabularInline):
    model = ReglaAlerta
    extra = 0


class ZonaRestringidaInline(admin.TabularInline):
    model = ZonaRestringida
    extra = 0
    show_change_link = True


@admin.register(Camara)
class CamaraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ip", "empresa", "ubicacion", "activa")
    list_filter = ("empresa", "activa")
    search_fields = ("nombre", "ip", "ubicacion")
    inlines = [ZonaRestringidaInline]


@admin.register(ConfiguracionNotificaciones)
class ConfiguracionNotificacionesAdmin(admin.ModelAdmin):
    list_display = ("__str__", "brevo_remitente_email", "actualizada_en")


@admin.register(EquipoLocal)
class EquipoLocalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "api_key", "activo", "ultima_conexion")
    list_filter = ("empresa", "activo")
    search_fields = ("nombre",)
    readonly_fields = ("api_key",)


@admin.register(ZonaRestringida)
class ZonaRestringidaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "camara", "tipo", "activa")
    list_filter = ("camara__empresa", "tipo", "activa")
    search_fields = ("nombre",)
    inlines = [ReglaAlertaInline]


@admin.register(ReglaAlerta)
class ReglaAlertaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "zona",
        "hora_inicio",
        "hora_fin",
        "canal_notificacion",
        "destinatario",
        "activa",
    )
    list_filter = ("canal_notificacion", "activa")
    search_fields = ("nombre", "destinatario")


@admin.register(EventoDetectado)
class EventoDetectadoAdmin(admin.ModelAdmin):
    list_display = ("camara", "zona", "timestamp", "disparo_alerta", "estado", "ia_analizado_en")
    list_filter = ("estado", "disparo_alerta", "camara")
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp", "ia_analizado_en")
    filter_horizontal = ("tipos_ia",)


@admin.register(ConfiguracionIA)
class ConfiguracionIAAdmin(admin.ModelAdmin):
    list_display = ("__str__", "modelo", "actualizada_en")


@admin.register(TipoEventoIA)
class TipoEventoIAAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "severidad", "activo", "creado_en")
    list_filter = ("empresa", "severidad", "activo")
    search_fields = ("nombre", "descripcion")


@admin.register(InstruccionSeguridad)
class InstruccionSeguridadAdmin(admin.ModelAdmin):
    list_display = ("__str__", "camara", "estado", "zona", "creada_en")
    list_filter = ("empresa", "estado")
    search_fields = ("texto", "notas")
