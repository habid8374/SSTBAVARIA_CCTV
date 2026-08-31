from rest_framework import serializers

from core.models import Empresa
from core.validators import validar_tamano_archivo

from .models import Camara, EventoDetectado, ReglaAlerta, ZonaRestringida


class EventoEntradaSerializer(serializers.Serializer):
    """Payload que envía el equipo local en cada evento de movimiento.

    `punto_x`/`punto_y` deben estar en el mismo sistema de coordenadas del
    encuadre de referencia usado al dibujar el `poligono` de la zona — eso
    lo define el equipo local, agnóstico a marca/modelo de cámara.
    """

    camara = serializers.PrimaryKeyRelatedField(queryset=Camara.objects.filter(activa=True))
    punto_x = serializers.FloatField()
    punto_y = serializers.FloatField()
    snapshot = serializers.ImageField(required=False, allow_null=True, validators=[validar_tamano_archivo])


class SnapshotReferenciaSerializer(serializers.Serializer):
    """Validación del archivo subido para el encuadre de referencia de una
    cámara (mismos límites de tamaño/tipo que el ImageField del modelo, pero
    esto se guarda con .save() directo en vez de por un ModelSerializer, así
    que hay que declarar los validadores acá también)."""

    snapshot_referencia = serializers.ImageField(validators=[validar_tamano_archivo])


class ReglaAlertaActivaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReglaAlerta
        fields = [
            "id",
            "nombre",
            "hora_inicio",
            "hora_fin",
            "dias_semana",
            "canal_notificacion",
            "destinatario",
        ]


class ZonaActivaSerializer(serializers.ModelSerializer):
    reglas = serializers.SerializerMethodField()

    class Meta:
        model = ZonaRestringida
        fields = ["id", "nombre", "poligono", "reglas"]

    def get_reglas(self, zona):
        reglas_activas = zona.reglas.filter(activa=True)
        return ReglaAlertaActivaSerializer(reglas_activas, many=True).data


class CamaraActivaSerializer(serializers.ModelSerializer):
    zonas = serializers.SerializerMethodField()

    class Meta:
        model = Camara
        fields = ["id", "nombre", "ip", "puerto_onvif", "usuario_onvif", "password_onvif", "zonas"]

    def get_zonas(self, camara):
        zonas_activas = camara.zonas.filter(activa=True).prefetch_related("reglas")
        return ZonaActivaSerializer(zonas_activas, many=True).data


# --- Serializers del dashboard (autenticación por usuario, no API key) ---


class ReglaAlertaSerializer(serializers.ModelSerializer):
    zona_nombre = serializers.CharField(source="zona.nombre", read_only=True)

    class Meta:
        model = ReglaAlerta
        fields = [
            "id",
            "zona",
            "zona_nombre",
            "nombre",
            "hora_inicio",
            "hora_fin",
            "dias_semana",
            "canal_notificacion",
            "destinatario",
            "activa",
        ]


class ZonaDashboardSerializer(serializers.ModelSerializer):
    camara_nombre = serializers.CharField(source="camara.nombre", read_only=True)
    reglas = ReglaAlertaSerializer(many=True, read_only=True)

    class Meta:
        model = ZonaRestringida
        fields = ["id", "camara", "camara_nombre", "nombre", "poligono", "activa", "reglas"]


class EventoDashboardSerializer(serializers.ModelSerializer):
    """Lectura para la bandeja de Alertas; solo `estado` es editable (marcar
    revisado) — el resto del evento lo escribe recibir_evento_camara."""

    camara_nombre = serializers.CharField(source="camara.nombre", read_only=True)
    zona_nombre = serializers.CharField(source="zona.nombre", read_only=True, default=None)

    class Meta:
        model = EventoDetectado
        fields = [
            "id",
            "camara",
            "camara_nombre",
            "zona",
            "zona_nombre",
            "timestamp",
            "snapshot",
            "punto_x",
            "punto_y",
            "disparo_alerta",
            "estado",
        ]
        read_only_fields = [
            "id",
            "camara",
            "camara_nombre",
            "zona",
            "zona_nombre",
            "timestamp",
            "snapshot",
            "punto_x",
            "punto_y",
            "disparo_alerta",
        ]


class UltimoEventoSerializer(serializers.ModelSerializer):
    zona_nombre = serializers.CharField(source="zona.nombre", read_only=True, default=None)

    class Meta:
        model = EventoDetectado
        fields = ["id", "zona", "zona_nombre", "timestamp", "snapshot", "punto_x", "punto_y", "disparo_alerta"]


class CamaraDashboardSerializer(serializers.ModelSerializer):
    zonas = ZonaDashboardSerializer(many=True, read_only=True)
    ultimo_evento = serializers.SerializerMethodField()

    class Meta:
        model = Camara
        fields = [
            "id",
            "nombre",
            "ip",
            "puerto_onvif",
            "usuario_onvif",
            "password_onvif",
            "ubicacion",
            "activa",
            "snapshot_referencia",
            "zonas",
            "ultimo_evento",
        ]

    def get_ultimo_evento(self, camara):
        evento = camara.eventos.order_by("-timestamp").first()
        if not evento:
            return None
        return UltimoEventoSerializer(evento, context=self.context).data


class CamaraCrearSerializer(serializers.ModelSerializer):
    """Alta de una cámara desde el dashboard. La empresa se asigna sola —
    este panel todavía no tiene gestión de empresas propia; si hace falta
    una distinta, se ajusta desde el admin de Django (app core)."""

    class Meta:
        model = Camara
        fields = [
            "id",
            "nombre",
            "ip",
            "puerto_onvif",
            "usuario_onvif",
            "password_onvif",
            "ubicacion",
            "activa",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        empresa = Empresa.objects.first()
        if empresa is None:
            empresa = Empresa.objects.create(nombre="Empresa")
        return Camara.objects.create(empresa=empresa, **validated_data)
