from datetime import timedelta

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import EsAdministradorParaEliminar

from .models import (
    DIAS_ALERTA_VENCIMIENTO,
    DeclaracionMetodo,
    EmpresaContratista,
    FirmaMetodo,
    RadicacionSeguridadSocial,
    Trabajador,
    calcular_hash_declaracion,
    nivel_riesgo,
)
from .notificaciones import notificar_decision_declaracion, notificar_decision_radicacion
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def indicadores(request):
    """Conteo de radicaciones de seguridad social vencidas o por vencer —
    para el banner de aviso en la vista de Contratistas. Nada se marca solo
    en la base; se calcula al vuelo contra la fecha de hoy."""
    hoy = timezone.localdate()
    limite_por_vencer = hoy + timedelta(days=DIAS_ALERTA_VENCIMIENTO)
    radicaciones = RadicacionSeguridadSocial.objects.exclude(estado=RadicacionSeguridadSocial.Estado.RECHAZADA)
    return Response(
        {
            "radicaciones_vencidas": radicaciones.filter(fecha_vencimiento__lt=hoy).count(),
            "radicaciones_por_vencer": radicaciones.filter(
                fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=limite_por_vencer
            ).count(),
        }
    )


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


def _filtrar_radicaciones(qs, params):
    """Filtros compartidos entre el listado y la exportación a Excel, para
    que "exportar lo que estoy viendo" sea literal."""
    trabajador_id = params.get("trabajador")
    if trabajador_id:
        qs = qs.filter(trabajador_id=trabajador_id)
    contratista_id = params.get("contratista")
    if contratista_id:
        qs = qs.filter(trabajador__contratista_id=contratista_id)
    estado = params.get("estado")
    if estado:
        qs = qs.filter(estado=estado)
    vencida = params.get("vencida")
    if vencida is not None:
        hoy = timezone.localdate()
        if vencida.lower() in ("1", "true"):
            qs = qs.filter(fecha_vencimiento__lt=hoy)
        else:
            qs = qs.filter(models.Q(fecha_vencimiento__gte=hoy) | models.Q(fecha_vencimiento__isnull=True))
    return qs


class RadicacionListaDashboard(generics.ListCreateAPIView):
    serializer_class = RadicacionSeguridadSocialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = RadicacionSeguridadSocial.objects.select_related("trabajador__contratista").order_by("-radicada_en")
        return _filtrar_radicaciones(qs, self.request.query_params)


class RadicacionDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = RadicacionSeguridadSocial.objects.select_related("trabajador__contratista")
    serializer_class = RadicacionSeguridadSocialSerializer
    permission_classes = [EsAdministradorParaEliminar]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def radicaciones_exportar(request):
    """Descarga en Excel las radicaciones que calcen con los mismos filtros
    del listado (?trabajador=&contratista=&estado=&vencida=) — "exportar lo
    que estoy viendo"."""
    from django.http import HttpResponse
    from openpyxl import Workbook

    qs = RadicacionSeguridadSocial.objects.select_related("trabajador__contratista").order_by("-radicada_en")
    qs = _filtrar_radicaciones(qs, request.query_params)

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Radicaciones"
    hoja.append(
        [
            "Contratista",
            "Trabajador",
            "Documento",
            "Mes",
            "Año",
            "N° planilla",
            "Fecha vencimiento",
            "Vencida",
            "Días para vencer",
            "Interventor",
            "Estado",
            "Observaciones",
            "Radicada en",
        ]
    )
    for radicacion in qs:
        hoja.append(
            [
                radicacion.trabajador.contratista.nombre,
                f"{radicacion.trabajador.apellidos} {radicacion.trabajador.nombres}",
                radicacion.trabajador.documento,
                radicacion.mes,
                radicacion.anio,
                radicacion.numero_planilla,
                radicacion.fecha_vencimiento.isoformat() if radicacion.fecha_vencimiento else "",
                "Sí" if radicacion.vencida else "No",
                radicacion.dias_para_vencer if radicacion.dias_para_vencer is not None else "",
                radicacion.interventor,
                radicacion.get_estado_display(),
                radicacion.observaciones,
                timezone.localtime(radicacion.radicada_en).strftime("%Y-%m-%d %H:%M"),
            ]
        )

    respuesta = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    respuesta["Content-Disposition"] = 'attachment; filename="radicaciones_seguridad_social.xlsx"'
    libro.save(respuesta)
    return respuesta


def _decidir_radicacion(request, pk, nuevo_estado):
    radicacion = get_object_or_404(RadicacionSeguridadSocial, pk=pk)
    entrada = DecisionRadicacionSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    observaciones = entrada.validated_data.get("observaciones", "").strip()

    if nuevo_estado == RadicacionSeguridadSocial.Estado.RECHAZADA and not observaciones:
        raise ValidationError({"observaciones": "Hay que indicar el motivo del rechazo."})

    radicacion.estado = nuevo_estado
    radicacion.observaciones = observaciones or radicacion.observaciones
    radicacion.revisada_en = timezone.now()
    radicacion.save(update_fields=["estado", "observaciones", "revisada_en"])
    notificar_decision_radicacion(radicacion)
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

    def perform_update(self, serializer):
        estado_anterior = serializer.instance.estado
        declaracion = serializer.save()
        if declaracion.estado != estado_anterior and declaracion.estado in (
            DeclaracionMetodo.Estado.APROBADA,
            DeclaracionMetodo.Estado.RECHAZADA,
        ):
            notificar_decision_declaracion(declaracion)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def firmar_declaracion(request, pk):
    """Agrega (o reemplaza, si ya existía) la firma electrónica de un rol
    para esta declaración. La cuenta que firma es siempre request.user — el
    cliente nunca puede suplantar a otra persona — y queda registrada la
    huella del documento en ese momento, para poder detectar cambios
    posteriores (ver FirmaMetodo.documento_modificado_despues_de_firmar)."""
    declaracion = get_object_or_404(
        DeclaracionMetodo.objects.prefetch_related("actividades"), pk=pk
    )
    entrada = FirmaMetodoSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    firma, _ = FirmaMetodo.objects.update_or_create(
        declaracion=declaracion,
        rol=entrada.validated_data["rol"],
        defaults={
            "nombre_firmante": entrada.validated_data["nombre_firmante"],
            "firmante_usuario": request.user,
            "hash_documento": calcular_hash_declaracion(declaracion),
        },
    )
    return Response(FirmaMetodoSerializer(firma).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def declaracion_pdf(request, pk):
    """Documento imprimible/archivable de la declaración de método completa
    — datos generales, actividades con su evaluación Kinney antes/después
    de mitigar, y las firmas registradas."""
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa

    declaracion = get_object_or_404(
        DeclaracionMetodo.objects.select_related("contratista").prefetch_related("actividades", "firmas"), pk=pk
    )

    actividades = []
    for actividad in declaracion.actividades.all():
        _, nivel_sin = nivel_riesgo(actividad.riesgo_sin)
        _, nivel_con = nivel_riesgo(actividad.riesgo_con)
        actividades.append(
            {
                "secuencia": actividad.secuencia,
                "tecnicas_herramientas": actividad.tecnicas_herramientas,
                "descripcion_riesgo": actividad.descripcion_riesgo,
                "probabilidad_sin": actividad.probabilidad_sin,
                "frecuencia_sin": actividad.frecuencia_sin,
                "impacto_sin": actividad.impacto_sin,
                "riesgo_sin": actividad.riesgo_sin,
                "nivel_sin": nivel_sin,
                "medidas_mitigacion": actividad.medidas_mitigacion,
                "probabilidad_con": actividad.probabilidad_con,
                "frecuencia_con": actividad.frecuencia_con,
                "impacto_con": actividad.impacto_con,
                "riesgo_con": actividad.riesgo_con,
                "nivel_con": nivel_con,
                "permisos_requeridos": actividad.permisos_requeridos,
                "tarea_sif": actividad.tarea_sif,
            }
        )

    html = render_to_string(
        "contratistas/declaracion_pdf.html", {"declaracion": declaracion, "actividades": actividades}
    )
    respuesta = HttpResponse(content_type="application/pdf")
    respuesta["Content-Disposition"] = f'inline; filename="declaracion-metodo-{declaracion.pk}.pdf"'
    resultado = pisa.CreatePDF(html, dest=respuesta)
    if resultado.err:
        return Response({"detail": "No se pudo generar el PDF."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return respuesta
