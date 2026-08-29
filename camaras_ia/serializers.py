from rest_framework import serializers

from .models import Camara, ReglaAlerta, ZonaRestringida


class EventoEntradaSerializer(serializers.Serializer):
    """Payload que envía el equipo local en cada evento de movimiento.

    `punto_x`/`punto_y` deben estar en el mismo sistema de coordenadas del
    encuadre de referencia usado al dibujar el `poligono` de la zona — eso
    lo define el equipo local, agnóstico a marca/modelo de cámara.
    """

    camara = serializers.PrimaryKeyRelatedField(queryset=Camara.objects.filter(activa=True))
    punto_x = serializers.FloatField()
    punto_y = serializers.FloatField()
    snapshot = serializers.ImageField(required=False, allow_null=True)


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
