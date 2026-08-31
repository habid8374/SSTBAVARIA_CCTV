from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import EsAdministradorParaEliminar

from .models import DeclaracionMetodo, EmpresaContratista, FirmaMetodo, RadicacionSeguridadSocial, Trabajador
from .serializers import (
    CatalogosSerializer,
    DecisionRadicacionSerializer,
    DeclaracionMetodoSerializer,
    EmpresaContratistaCrearSerializer,
    EmpresaContratistaSerializer,
    FirmaMetodoSerializer,
    RadicacionSeguridadSocialSerializer,
    TrabajadorSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def catalogos(request):
    """Listas fijas (cursos, permisos de trabajo, roles de firma) para armar
    los formularios del frontend sin duplicarlas ahí."""
    return Response(CatalogosSerializer(instance={}).data)


# --- Empresas contratistas ---


class EmpresaContratistaListaDashboard(generics.ListCreateAPIView):
    queryset = EmpresaContratista.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return EmpresaContratistaCrearSerializer if self.request.method == "POST" else EmpresaContratistaSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contratista = serializer.save()
        return Response(
            EmpresaContratistaSerializer(contratista, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class EmpresaContratistaDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = EmpresaContratista.objects.all()
    serializer_class = EmpresaContratistaSerializer
    permission_classes = [EsAdministradorParaEliminar]


# --- Trabajadores ---


class TrabajadorListaDashboard(generics.ListCreateAPIView):
    serializer_class = TrabajadorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Trabajador.objects.select_related("contratista").prefetch_related("radicaciones")
        contratista_id = self.request.query_params.get("contratista")
        if contratista_id:
            qs = qs.filter(contratista_id=contratista_id)
        return qs


class TrabajadorDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = Trabajador.objects.select_related("contratista")
    serializer_class = TrabajadorSerializer
    permission_classes = [EsAdministradorParaEliminar]


# --- Radicaciones de seguridad social ---


class RadicacionListaDashboard(generics.ListCreateAPIView):
    serializer_class = RadicacionSeguridadSocialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = RadicacionSeguridadSocial.objects.select_related("trabajador__contratista").order_by("-radicada_en")
        trabajador_id = self.request.query_params.get("trabajador")
        if trabajador_id:
            qs = qs.filter(trabajador_id=trabajador_id)
        contratista_id = self.request.query_params.get("contratista")
        if contratista_id:
            qs = qs.filter(trabajador__contratista_id=contratista_id)
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class RadicacionDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = RadicacionSeguridadSocial.objects.select_related("trabajador__contratista")
    serializer_class = RadicacionSeguridadSocialSerializer
    permission_classes = [EsAdministradorParaEliminar]


def _decidir_radicacion(request, pk, nuevo_estado):
    radicacion = get_object_or_404(RadicacionSeguridadSocial, pk=pk)
    entrada = DecisionRadicacionSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    radicacion.estado = nuevo_estado
    radicacion.observaciones = entrada.validated_data.get("observaciones") or radicacion.observaciones
    radicacion.revisada_en = timezone.now()
    radicacion.save(update_fields=["estado", "observaciones", "revisada_en"])
    return Response(RadicacionSeguridadSocialSerializer(radicacion).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def aprobar_radicacion(request, pk):
    return _decidir_radicacion(request, pk, RadicacionSeguridadSocial.Estado.APROBADA)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rechazar_radicacion(request, pk):
    return _decidir_radicacion(request, pk, RadicacionSeguridadSocial.Estado.RECHAZADA)


# --- Declaraciones de método ---


class DeclaracionMetodoListaDashboard(generics.ListCreateAPIView):
    serializer_class = DeclaracionMetodoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DeclaracionMetodo.objects.select_related("contratista").prefetch_related("actividades", "firmas")
        contratista_id = self.request.query_params.get("contratista")
        if contratista_id:
            qs = qs.filter(contratista_id=contratista_id)
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class DeclaracionMetodoDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = DeclaracionMetodo.objects.select_related("contratista").prefetch_related("actividades", "firmas")
    serializer_class = DeclaracionMetodoSerializer
    permission_classes = [EsAdministradorParaEliminar]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def firmar_declaracion(request, pk):
    """Agrega (o reemplaza, si ya existía) la firma de un rol para esta declaración."""
    declaracion = get_object_or_404(DeclaracionMetodo, pk=pk)
    entrada = FirmaMetodoSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    firma, _ = FirmaMetodo.objects.update_or_create(
        declaracion=declaracion,
        rol=entrada.validated_data["rol"],
        defaults={"nombre_firmante": entrada.validated_data["nombre_firmante"]},
    )
    return Response(FirmaMetodoSerializer(firma).data, status=status.HTTP_201_CREATED)
