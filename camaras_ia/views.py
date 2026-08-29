from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Camara, EquipoLocal, EventoDetectado
from .serializers import CamaraActivaSerializer, EventoEntradaSerializer
from .services import disparar_alerta, evaluar_zona_horario


def _equipo_desde_api_key(request):
    """Resuelve el EquipoLocal autenticado por el header X-API-Key, o None."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    return EquipoLocal.objects.filter(api_key=api_key, activo=True).first()


@api_view(["POST"])
def recibir_evento_camara(request):
    """Recibe un evento de movimiento del equipo local: cámara, punto
    detectado y snapshot. Cruza el punto contra las zonas restringidas de la
    cámara y las reglas de horario vigentes; si hay una regla activa ahora
    mismo, marca el evento como disparo de alerta y llama a disparar_alerta.
    """
    equipo = _equipo_desde_api_key(request)
    if equipo is None:
        return Response(
            {"detail": "API key inválida o inactiva."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = EventoEntradaSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    camara = serializer.validated_data["camara"]

    if camara.empresa_id != equipo.empresa_id:
        return Response(
            {"detail": "La cámara no pertenece a la empresa de este equipo."},
            status=status.HTTP_403_FORBIDDEN,
        )

    punto = (serializer.validated_data["punto_x"], serializer.validated_data["punto_y"])
    zona, regla = evaluar_zona_horario(camara, punto)

    evento = EventoDetectado.objects.create(
        camara=camara,
        zona=zona,
        snapshot=serializer.validated_data.get("snapshot"),
        disparo_alerta=regla is not None,
    )

    if regla is not None:
        disparar_alerta(evento, regla)

    equipo.ultima_conexion = timezone.now()
    equipo.save(update_fields=["ultima_conexion"])

    return Response(
        {
            "id": evento.pk,
            "zona": zona.nombre if zona else None,
            "disparo_alerta": evento.disparo_alerta,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def obtener_reglas_activas(request):
    """El equipo local consulta esto periódicamente para sincronizar qué
    cámaras/zonas/horarios debe vigilar, sin tocar el equipo físicamente.
    Solo devuelve cámaras, zonas y reglas activas de la empresa del equipo.
    """
    equipo = _equipo_desde_api_key(request)
    if equipo is None:
        return Response(
            {"detail": "API key inválida o inactiva."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    camaras_activas = Camara.objects.filter(empresa=equipo.empresa, activa=True).prefetch_related(
        "zonas__reglas"
    )

    equipo.ultima_conexion = timezone.now()
    equipo.save(update_fields=["ultima_conexion"])

    return Response(
        {
            "equipo": equipo.nombre,
            "camaras": CamaraActivaSerializer(camaras_activas, many=True).data,
        }
    )
