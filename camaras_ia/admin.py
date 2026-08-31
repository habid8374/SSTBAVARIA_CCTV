from django.contrib import admin

from .models import Camara, ConfiguracionNotificaciones, EquipoLocal, EventoDetectado, ReglaAlerta, ZonaRestringida


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
    list_display = ("nombre", "camara", "activa")
    list_filter = ("camara__empresa", "activa")
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
    list_display = ("camara", "zona", "timestamp", "disparo_alerta", "estado")
    list_filter = ("estado", "disparo_alerta", "camara")
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp",)
