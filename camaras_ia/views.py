from datetime import timedelta

from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import EsAdministrador, EsAdministradorOSoloLectura

from .models import Camara, EquipoLocal, EventoDetectado, ReglaAlerta, ZonaRestringida
from .serializers import (
    CamaraActivaSerializer,
    CamaraDashboardSerializer,
    EventoDashboardSerializer,
    EventoEntradaSerializer,
    ReglaAlertaSerializer,
    ZonaDashboardSerializer,
)
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
        punto_x=punto[0],
        punto_y=punto[1],
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


# --- Endpoints del dashboard (usuario autenticado por token, no equipo local) ---


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def indicadores_dashboard(request):
    """KPIs para el Tablero: cámaras activas/total, alertas hoy y una
    disponibilidad simple (cámaras activas / total) — no es monitoreo de
    conectividad real, solo una proporción sobre lo que ya tenemos."""
    total = Camara.objects.count()
    activas = Camara.objects.filter(activa=True).count()
    hoy = timezone.localdate()
    alertas_hoy = EventoDetectado.objects.filter(disparo_alerta=True, timestamp__date=hoy).count()
    disponibilidad = round(activas / total * 100) if total else 0
    return Response(
        {
            "camaras_activas": activas,
            "camaras_total": total,
            "alertas_hoy": alertas_hoy,
            "disponibilidad": disponibilidad,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def eventos_por_zona(request):
    """Conteo de eventos de los últimos 7 días agrupados por zona, para el
    gráfico del Tablero."""
    desde = timezone.now() - timedelta(days=7)
    datos = (
        EventoDetectado.objects.filter(timestamp__gte=desde, zona__isnull=False)
        .values("zona__nombre", "zona__camara__nombre")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )
    return Response(
        [
            {"zona": d["zona__nombre"], "camara": d["zona__camara__nombre"], "total": d["total"]}
            for d in datos
        ]
    )


class EventoListaDashboard(generics.ListAPIView):
    """Bandeja de Alertas: lista de eventos, más recientes primero, con
    filtros opcionales ?estado=&disparo_alerta=&camara=."""

    serializer_class = EventoDashboardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = EventoDetectado.objects.select_related("camara", "zona").order_by("-timestamp")
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        disparo_alerta = self.request.query_params.get("disparo_alerta")
        if disparo_alerta is not None:
            qs = qs.filter(disparo_alerta=disparo_alerta.lower() in ("1", "true"))
        camara_id = self.request.query_params.get("camara")
        if camara_id:
            qs = qs.filter(camara_id=camara_id)
        return qs[:200]


class EventoDetalleDashboard(generics.RetrieveUpdateAPIView):
    """Marcar un evento como revisado (o de vuelta a nuevo)."""

    queryset = EventoDetectado.objects.select_related("camara", "zona")
    serializer_class = EventoDashboardSerializer
    permission_classes = [IsAuthenticated]


class CamaraListaDashboard(generics.ListAPIView):
    """Cámaras con sus zonas y el último evento — usado por el Tablero y la
    vista de Cámaras IA con overlays."""

    queryset = Camara.objects.prefetch_related("zonas__reglas", "eventos").order_by("nombre")
    serializer_class = CamaraDashboardSerializer
    permission_classes = [IsAuthenticated]


@api_view(["POST"])
@permission_classes([EsAdministrador])
def subir_snapshot_referencia(request, pk):
    """Sube/reemplaza el encuadre de referencia de una cámara, sobre el que
    se dibujan las zonas restringidas en el editor visual."""
    camara = get_object_or_404(Camara, pk=pk)
    archivo = request.FILES.get("snapshot_referencia")
    if not archivo:
        return Response({"detail": "Falta el archivo snapshot_referencia."}, status=status.HTTP_400_BAD_REQUEST)
    camara.snapshot_referencia = archivo
    camara.save(update_fields=["snapshot_referencia"])
    return Response(CamaraDashboardSerializer(camara, context={"request": request}).data)


class ZonaListaCrear(generics.ListCreateAPIView):
    queryset = ZonaRestringida.objects.select_related("camara").prefetch_related("reglas")
    serializer_class = ZonaDashboardSerializer
    permission_classes = [EsAdministradorOSoloLectura]


class ZonaDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = ZonaRestringida.objects.select_related("camara").prefetch_related("reglas")
    serializer_class = ZonaDashboardSerializer
    permission_classes = [EsAdministradorOSoloLectura]


class ReglaListaCrear(generics.ListCreateAPIView):
    serializer_class = ReglaAlertaSerializer
    permission_classes = [EsAdministradorOSoloLectura]

    def get_queryset(self):
        qs = ReglaAlerta.objects.select_related("zona")
        zona_id = self.request.query_params.get("zona")
        if zona_id:
            qs = qs.filter(zona_id=zona_id)
        return qs


class ReglaDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = ReglaAlerta.objects.select_related("zona")
    serializer_class = ReglaAlertaSerializer
    permission_classes = [EsAdministradorOSoloLectura]
