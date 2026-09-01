from datetime import timedelta

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import PerfilUsuario
from core.permissions import (
    EsAdministrador,
    EsAdministradorOSoloLectura,
    EsAdministradorParaEliminar,
    EsPersonalInterno,
    EsPersonalInternoOSoloLectura,
)

from .auditoria import capturar_snapshot, registrar_auditoria
from .models import (
    ActividadMetodo,
    AutorizacionIngreso,
    ConfiguracionAlertas,
    ConfiguracionCapacitacion,
    CursoSafetyAcademy,
    DeclaracionMetodo,
    EmpresaContratista,
    EquipoProteccionPersonal,
    FirmaMetodo,
    Funcionario,
    NotificacionInterna,
    PermisoTrabajo,
    PreguntaCapacitacion,
    RadicacionSeguridadSocial,
    RegistroAuditoria,
    RegistroCapacitacion,
    Trabajador,
    calcular_hash_declaracion,
    nivel_riesgo,
)
from .notificaciones import (
    notificar_decision_declaracion,
    notificar_decision_radicacion,
    notificar_declaracion_pendiente,
    notificar_radicacion_pendiente,
)
from .serializers import (
    AutorizacionIngresoSerializer,
    CalificarCapacitacionSerializer,
    CatalogosSerializer,
    ConfiguracionAlertasSerializer,
    ConfiguracionCapacitacionSerializer,
    CursoSafetyAcademySerializer,
    DecisionRadicacionSerializer,
    DeclaracionMetodoSerializer,
    EmpresaContratistaCrearSerializer,
    EmpresaContratistaSerializer,
    EquipoProteccionPersonalSerializer,
    FirmaMetodoSerializer,
    FuncionarioSerializer,
    NotaAlertaSerializer,
    NotificacionInternaSerializer,
    PermisoTrabajoSerializer,
    PreguntaCapacitacionPublicaSerializer,
    RadicacionSeguridadSocialSerializer,
    RegistroAuditoriaSerializer,
    RegistroCapacitacionIniciarSerializer,
    RegistroCapacitacionSerializer,
    TrabajadorSerializer,
)


class AuditoriaMixin:
    """Registra en RegistroAuditoria cada creación/edición/eliminación hecha
    a través de esta vista genérica — ver contratistas/auditoria.py. Solo se
    aplica a los modelos críticos de cumplimiento (contratistas,
    trabajadores, radicaciones, declaraciones de método, funcionarios)."""

    def perform_create(self, serializer):
        instancia = serializer.save()
        registrar_auditoria(self.request.user, instancia, RegistroAuditoria.Accion.CREADO)

    def perform_update(self, serializer):
        snapshot_anterior = capturar_snapshot(serializer.instance)
        instancia = serializer.save()
        registrar_auditoria(self.request.user, instancia, RegistroAuditoria.Accion.ACTUALIZADO, snapshot_anterior)

    def perform_destroy(self, instance):
        registrar_auditoria(self.request.user, instance, RegistroAuditoria.Accion.ELIMINADO)
        instance.delete()


def _contratista_de(request):
    """El id de la EmpresaContratista del usuario autenticado, si su rol es
    Contratista (portal externo) — o None para personal interno, que ve y
    filtra sin restricción."""
    perfil = getattr(request.user, "perfil", None)
    if perfil and perfil.rol == PerfilUsuario.Rol.CONTRATISTA:
        return perfil.contratista_id
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def catalogos(request):
    """Listas fijas (cursos, permisos de trabajo, roles de firma) para armar
    los formularios del frontend sin duplicarlas ahí."""
    return Response(CatalogosSerializer(instance={}).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def indicadores(request):
    """Conteo de radicaciones de seguridad social y de certificaciones de
    trabajadores (examen médico ocupacional, trabajo en alturas) vencidas o
    por vencer — para el banner de aviso en la vista de Contratistas. Nada
    se marca solo en la base; se calcula al vuelo contra la fecha de hoy."""
    hoy = timezone.localdate()
    dias_alerta = ConfiguracionAlertas.obtener().dias_alerta_vencimiento
    limite_por_vencer = hoy + timedelta(days=dias_alerta)
    radicaciones = RadicacionSeguridadSocial.objects.exclude(estado=RadicacionSeguridadSocial.Estado.RECHAZADA)
    trabajadores = Trabajador.objects.filter(activo=True)
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        radicaciones = radicaciones.filter(trabajador__contratista_id=contratista_id)
        trabajadores = trabajadores.filter(contratista_id=contratista_id)
    return Response(
        {
            "radicaciones_vencidas": radicaciones.filter(fecha_vencimiento__lt=hoy).count(),
            "radicaciones_por_vencer": radicaciones.filter(
                fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=limite_por_vencer
            ).count(),
            "examenes_medicos_vencidos": trabajadores.filter(fecha_vencimiento_examen_medico__lt=hoy).count(),
            "examenes_medicos_por_vencer": trabajadores.filter(
                fecha_vencimiento_examen_medico__gte=hoy, fecha_vencimiento_examen_medico__lte=limite_por_vencer
            ).count(),
            "certificaciones_alturas_vencidas": trabajadores.filter(
                fecha_vencimiento_certificacion_alturas__lt=hoy
            ).count(),
            "certificaciones_alturas_por_vencer": trabajadores.filter(
                fecha_vencimiento_certificacion_alturas__gte=hoy,
                fecha_vencimiento_certificacion_alturas__lte=limite_por_vencer,
            ).count(),
        }
    )


MESES_ABREVIADOS = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


def _ultimos_meses(hoy, cantidad=6):
    """[(año, mes), ...] de los últimos `cantidad` meses, terminando en el mes actual."""
    meses = []
    year, month = hoy.year, hoy.month
    for _ in range(cantidad):
        meses.append((year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(meses))


@api_view(["GET"])
@permission_classes([EsPersonalInterno])
def indicadores_dashboard(request):
    """Panel de indicadores tipo Power BI para Contratistas y Declaración de
    Método: cumplimiento por contratista, estado de declaraciones, riesgo
    Kinney promedio, tiempos de aprobación y tendencia mensual. Todo se
    calcula al vuelo — no hay tablas de resumen materializadas que puedan
    desincronizarse del dato real."""
    hoy = timezone.localdate()

    radicaciones = RadicacionSeguridadSocial.objects.all()
    radicaciones_por_estado = {
        clave: radicaciones.filter(estado=clave).count() for clave, _ in RadicacionSeguridadSocial.Estado.choices
    }

    declaraciones = DeclaracionMetodo.objects.all()
    declaraciones_por_estado = {
        clave: declaraciones.filter(estado=clave).count() for clave, _ in DeclaracionMetodo.Estado.choices
    }

    actividades = list(ActividadMetodo.objects.select_related("declaracion__contratista"))
    riesgos_sin = [a.riesgo_sin for a in actividades]
    riesgos_con = [a.riesgo_con for a in actividades]
    top_riesgos = sorted(actividades, key=lambda a: a.riesgo_sin, reverse=True)[:5]
    top_riesgos_datos = [
        {
            "declaracion_id": a.declaracion_id,
            "contratista": a.declaracion.contratista.nombre,
            "secuencia": a.secuencia[:80],
            "riesgo_sin": a.riesgo_sin,
            "nivel_sin": nivel_riesgo(a.riesgo_sin)[1],
            "riesgo_con": a.riesgo_con,
        }
        for a in top_riesgos
    ]

    aprobadas = declaraciones.filter(estado=DeclaracionMetodo.Estado.APROBADA)
    tiempos_dias = [(d.actualizada_en - d.creada_en).total_seconds() / 86400 for d in aprobadas]

    contratistas_activos = list(EmpresaContratista.objects.filter(activa=True).prefetch_related("trabajadores"))
    por_contratista = []
    for c in contratistas_activos:
        por_contratista.append(
            {
                "contratista": c.nombre,
                "trabajadores": c.trabajadores.count(),
                "radicaciones_pendientes": radicaciones.filter(
                    trabajador__contratista=c, estado=RadicacionSeguridadSocial.Estado.PENDIENTE
                ).count(),
                "declaraciones_pendientes": declaraciones.filter(contratista=c)
                .exclude(estado__in=[DeclaracionMetodo.Estado.APROBADA, DeclaracionMetodo.Estado.RECHAZADA])
                .count(),
            }
        )
    por_contratista.sort(key=lambda x: x["trabajadores"], reverse=True)

    tendencia_mensual = []
    for year, month in _ultimos_meses(hoy):
        tendencia_mensual.append(
            {
                "mes": f"{MESES_ABREVIADOS[month]} {year}",
                "declaraciones": declaraciones.filter(creada_en__year=year, creada_en__month=month).count(),
                "radicaciones": radicaciones.filter(radicada_en__year=year, radicada_en__month=month).count(),
            }
        )

    claves_obligatorias = list(
        CursoSafetyAcademy.objects.filter(activo=True, obligatorio=True).values_list("clave", flat=True)
    )
    trabajadores_activos = list(Trabajador.objects.filter(activo=True).only("cursos_safety_academy"))
    trabajadores_con_cursos_pendientes = sum(
        1
        for t in trabajadores_activos
        if any(not (t.cursos_safety_academy or {}).get(clave) for clave in claves_obligatorias)
    )

    return Response(
        {
            "contratistas_activos": len(contratistas_activos),
            "trabajadores_activos": len(trabajadores_activos),
            "trabajadores_con_cursos_pendientes": trabajadores_con_cursos_pendientes,
            "radicaciones_por_estado": radicaciones_por_estado,
            "declaraciones_por_estado": declaraciones_por_estado,
            "riesgo_promedio_sin": round(sum(riesgos_sin) / len(riesgos_sin), 1) if riesgos_sin else 0,
            "riesgo_promedio_con": round(sum(riesgos_con) / len(riesgos_con), 1) if riesgos_con else 0,
            "top_riesgos": top_riesgos_datos,
            "tiempo_promedio_aprobacion_dias": (
                round(sum(tiempos_dias) / len(tiempos_dias), 1) if tiempos_dias else None
            ),
            "por_contratista": por_contratista[:8],
            "tendencia_mensual": tendencia_mensual,
        }
    )


# --- Funcionarios firmantes ---


class FuncionarioListaDashboard(AuditoriaMixin, generics.ListCreateAPIView):
    serializer_class = FuncionarioSerializer
    permission_classes = [EsPersonalInterno]

    def get_queryset(self):
        qs = Funcionario.objects.all()
        rol_firma = self.request.query_params.get("rol_firma")
        if rol_firma:
            qs = qs.filter(rol_firma=rol_firma)
        solo_activos = self.request.query_params.get("activo")
        if solo_activos is not None:
            qs = qs.filter(activo=solo_activos.lower() in ("1", "true"))
        return qs


class FuncionarioDetalle(AuditoriaMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Funcionario.objects.all()
    serializer_class = FuncionarioSerializer
    permission_classes = [EsPersonalInterno, EsAdministradorParaEliminar]


# --- Motor de reglas (cursos, permisos de trabajo, días de alerta) ---


class CursoSafetyAcademyListaDashboard(generics.ListCreateAPIView):
    queryset = CursoSafetyAcademy.objects.all()
    serializer_class = CursoSafetyAcademySerializer
    permission_classes = [EsPersonalInterno]


class CursoSafetyAcademyDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = CursoSafetyAcademy.objects.all()
    serializer_class = CursoSafetyAcademySerializer
    permission_classes = [EsPersonalInterno, EsAdministradorParaEliminar]


class PermisoTrabajoListaDashboard(generics.ListCreateAPIView):
    queryset = PermisoTrabajo.objects.all()
    serializer_class = PermisoTrabajoSerializer
    permission_classes = [EsPersonalInterno]


class PermisoTrabajoDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = PermisoTrabajo.objects.all()
    serializer_class = PermisoTrabajoSerializer
    permission_classes = [EsPersonalInterno, EsAdministradorParaEliminar]


class EquipoProteccionPersonalListaDashboard(generics.ListCreateAPIView):
    queryset = EquipoProteccionPersonal.objects.all()
    serializer_class = EquipoProteccionPersonalSerializer
    permission_classes = [EsPersonalInterno]


class EquipoProteccionPersonalDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = EquipoProteccionPersonal.objects.all()
    serializer_class = EquipoProteccionPersonalSerializer
    permission_classes = [EsPersonalInterno, EsAdministradorParaEliminar]


class ConfiguracionAlertasDetalle(generics.RetrieveUpdateAPIView):
    """Fila única — a cuántos días de vencer se considera "por vencer" una
    planilla, editable por un Administrador en vez de fijo en el código."""

    serializer_class = ConfiguracionAlertasSerializer
    permission_classes = [EsPersonalInterno, EsAdministradorOSoloLectura]

    def get_object(self):
        return ConfiguracionAlertas.obtener()


# --- Empresas contratistas ---


class EmpresaContratistaListaDashboard(generics.ListCreateAPIView):
    queryset = EmpresaContratista.objects.all()
    permission_classes = [EsPersonalInternoOSoloLectura]

    def get_queryset(self):
        qs = EmpresaContratista.objects.all()
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(pk=contratista_id)
        return qs

    def get_serializer_class(self):
        return EmpresaContratistaCrearSerializer if self.request.method == "POST" else EmpresaContratistaSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contratista = serializer.save()
        registrar_auditoria(request.user, contratista, RegistroAuditoria.Accion.CREADO)
        return Response(
            EmpresaContratistaSerializer(contratista, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class EmpresaContratistaDetalle(AuditoriaMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EmpresaContratistaSerializer
    permission_classes = [EsPersonalInternoOSoloLectura, EsAdministradorParaEliminar]

    def get_queryset(self):
        qs = EmpresaContratista.objects.all()
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(pk=contratista_id)
        return qs


# --- Trabajadores ---


class TrabajadorListaDashboard(AuditoriaMixin, generics.ListCreateAPIView):
    serializer_class = TrabajadorSerializer
    permission_classes = [EsPersonalInternoOSoloLectura]

    def get_queryset(self):
        qs = Trabajador.objects.select_related("contratista").prefetch_related("radicaciones")
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(contratista_id=contratista_id)
        else:
            filtro = self.request.query_params.get("contratista")
            if filtro:
                qs = qs.filter(contratista_id=filtro)
        return qs


class TrabajadorDetalle(AuditoriaMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TrabajadorSerializer
    permission_classes = [EsPersonalInternoOSoloLectura, EsAdministradorParaEliminar]

    def get_queryset(self):
        qs = Trabajador.objects.select_related("contratista")
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(contratista_id=contratista_id)
        return qs


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
    permission_classes = [EsPersonalInternoOSoloLectura]

    def get_queryset(self):
        qs = RadicacionSeguridadSocial.objects.select_related("trabajador__contratista").order_by("-radicada_en")
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(trabajador__contratista_id=contratista_id)
        return _filtrar_radicaciones(qs, self.request.query_params)

    def perform_create(self, serializer):
        radicacion = serializer.save()
        registrar_auditoria(self.request.user, radicacion, RegistroAuditoria.Accion.CREADO)
        if radicacion.estado == RadicacionSeguridadSocial.Estado.PENDIENTE:
            notificar_radicacion_pendiente(radicacion)


class RadicacionDetalle(AuditoriaMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RadicacionSeguridadSocialSerializer
    permission_classes = [EsPersonalInternoOSoloLectura, EsAdministradorParaEliminar]

    def get_queryset(self):
        qs = RadicacionSeguridadSocial.objects.select_related("trabajador__contratista")
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(trabajador__contratista_id=contratista_id)
        return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def radicaciones_exportar(request):
    """Descarga en Excel las radicaciones que calcen con los mismos filtros
    del listado (?trabajador=&contratista=&estado=&vencida=) — "exportar lo
    que estoy viendo"."""
    from django.http import HttpResponse
    from openpyxl import Workbook

    qs = RadicacionSeguridadSocial.objects.select_related("trabajador__contratista").order_by("-radicada_en")
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(trabajador__contratista_id=contratista_id)
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
    snapshot_anterior = capturar_snapshot(radicacion)
    entrada = DecisionRadicacionSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    observaciones = entrada.validated_data.get("observaciones", "").strip()

    if nuevo_estado == RadicacionSeguridadSocial.Estado.RECHAZADA and not observaciones:
        raise ValidationError({"observaciones": "Hay que indicar el motivo del rechazo."})

    radicacion.estado = nuevo_estado
    radicacion.observaciones = observaciones or radicacion.observaciones
    radicacion.revisada_en = timezone.now()
    radicacion.save(update_fields=["estado", "observaciones", "revisada_en"])
    registrar_auditoria(request.user, radicacion, RegistroAuditoria.Accion.ACTUALIZADO, snapshot_anterior)
    notificar_decision_radicacion(radicacion)
    return Response(RadicacionSeguridadSocialSerializer(radicacion).data)


@api_view(["POST"])
@permission_classes([EsPersonalInterno])
def aprobar_radicacion(request, pk):
    return _decidir_radicacion(request, pk, RadicacionSeguridadSocial.Estado.APROBADA)


@api_view(["POST"])
@permission_classes([EsPersonalInterno])
def rechazar_radicacion(request, pk):
    return _decidir_radicacion(request, pk, RadicacionSeguridadSocial.Estado.RECHAZADA)


# --- Declaraciones de método ---


class DeclaracionMetodoListaDashboard(AuditoriaMixin, generics.ListCreateAPIView):
    serializer_class = DeclaracionMetodoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DeclaracionMetodo.objects.select_related("contratista").prefetch_related("actividades", "firmas")
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(contratista_id=contratista_id)
        else:
            filtro = self.request.query_params.get("contratista")
            if filtro:
                qs = qs.filter(contratista_id=filtro)
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def perform_create(self, serializer):
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            estado = serializer.validated_data.get("estado")
            if estado in (DeclaracionMetodo.Estado.APROBADA, DeclaracionMetodo.Estado.RECHAZADA):
                raise PermissionDenied("Solo el personal de SST/interventoría puede aprobar o rechazar.")
            serializer.validated_data["contratista_id"] = contratista_id
            serializer.validated_data.pop("contratista", None)
        instancia = serializer.save()
        registrar_auditoria(self.request.user, instancia, RegistroAuditoria.Accion.CREADO)
        if instancia.estado == DeclaracionMetodo.Estado.ENVIADA:
            notificar_declaracion_pendiente(instancia)


class DeclaracionMetodoDetalle(AuditoriaMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DeclaracionMetodoSerializer
    permission_classes = [EsAdministradorParaEliminar]

    def get_queryset(self):
        qs = DeclaracionMetodo.objects.select_related("contratista").prefetch_related("actividades", "firmas")
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(contratista_id=contratista_id)
        return qs

    def perform_update(self, serializer):
        estado_anterior = serializer.instance.estado
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            nuevo_estado = serializer.validated_data.get("estado", estado_anterior)
            if nuevo_estado != estado_anterior and nuevo_estado in (
                DeclaracionMetodo.Estado.APROBADA,
                DeclaracionMetodo.Estado.RECHAZADA,
            ):
                raise PermissionDenied("Solo el personal de SST/interventoría puede aprobar o rechazar.")
        snapshot_anterior = capturar_snapshot(serializer.instance)
        declaracion = serializer.save()
        registrar_auditoria(self.request.user, declaracion, RegistroAuditoria.Accion.ACTUALIZADO, snapshot_anterior)
        if declaracion.estado == estado_anterior:
            return
        if declaracion.estado in (DeclaracionMetodo.Estado.APROBADA, DeclaracionMetodo.Estado.RECHAZADA):
            notificar_decision_declaracion(declaracion)
        elif declaracion.estado == DeclaracionMetodo.Estado.ENVIADA:
            notificar_declaracion_pendiente(
                declaracion, es_subsanacion=estado_anterior == DeclaracionMetodo.Estado.RECHAZADA
            )


# --- Autorización de ingreso (inclusiones/exclusiones) ---


class AutorizacionIngresoListaDashboard(AuditoriaMixin, generics.ListCreateAPIView):
    serializer_class = AutorizacionIngresoSerializer
    permission_classes = [EsPersonalInternoOSoloLectura]

    def get_queryset(self):
        qs = AutorizacionIngreso.objects.select_related("contratista").prefetch_related("trabajadores__trabajador")
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(contratista_id=contratista_id)
        else:
            filtro = self.request.query_params.get("contratista")
            if filtro:
                qs = qs.filter(contratista_id=filtro)
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class AutorizacionIngresoDetalle(AuditoriaMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AutorizacionIngresoSerializer
    permission_classes = [EsPersonalInternoOSoloLectura, EsAdministradorParaEliminar]

    def get_queryset(self):
        qs = AutorizacionIngreso.objects.select_related("contratista").prefetch_related("trabajadores__trabajador")
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(contratista_id=contratista_id)
        return qs


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def firmar_declaracion(request, pk):
    """Agrega (o reemplaza, si ya existía) la firma electrónica de un rol
    para esta declaración. La cuenta que firma es siempre request.user — el
    cliente nunca puede suplantar a otra persona — y queda registrada la
    huella del documento en ese momento, para poder detectar cambios
    posteriores (ver FirmaMetodo.documento_modificado_despues_de_firmar)."""
    qs = DeclaracionMetodo.objects.prefetch_related("actividades")
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(contratista_id=contratista_id)
    declaracion = get_object_or_404(qs, pk=pk)
    entrada = FirmaMetodoSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    if contratista_id is not None and entrada.validated_data["rol"] != FirmaMetodo.Rol.SUPERVISOR_CONTRATISTA:
        raise PermissionDenied("El portal del contratista solo puede firmar como Supervisor de Seguridad del Contratista.")
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


class RegistroAuditoriaLista(generics.ListAPIView):
    """Solo lectura — la traza de auditoría nunca se edita ni se borra desde
    acá. Filtrable por ?modelo= para revisar solo, por ejemplo, los cambios
    de Trabajador."""

    serializer_class = RegistroAuditoriaSerializer
    permission_classes = [EsAdministrador]

    def get_queryset(self):
        qs = RegistroAuditoria.objects.select_related("usuario")
        modelo = self.request.query_params.get("modelo")
        if modelo:
            qs = qs.filter(modelo=modelo)
        objeto_id = self.request.query_params.get("objeto_id")
        if objeto_id:
            qs = qs.filter(objeto_id=objeto_id)
        return qs[:500]


class NotificacionInternaLista(generics.ListAPIView):
    """Bandeja compartida del personal de SST/interventoría: declaraciones y
    radicaciones nuevas o corregidas y reenviadas, esperando revisión. Solo
    lectura desde acá — se marcan leídas con los endpoints de abajo."""

    serializer_class = NotificacionInternaSerializer
    permission_classes = [EsPersonalInterno]

    def get_queryset(self):
        qs = NotificacionInterna.objects.all()
        solo_no_leidas = self.request.query_params.get("leida")
        if solo_no_leidas is not None:
            qs = qs.filter(leida=solo_no_leidas.lower() in ("1", "true"))
        return qs[:200]


@api_view(["POST"])
@permission_classes([EsPersonalInterno])
def marcar_notificacion_leida(request, pk):
    notificacion = get_object_or_404(NotificacionInterna, pk=pk)
    notificacion.leida = True
    notificacion.save(update_fields=["leida"])
    return Response(NotificacionInternaSerializer(notificacion).data)


@api_view(["POST"])
@permission_classes([EsPersonalInterno])
def marcar_todas_notificaciones_leidas(request):
    NotificacionInterna.objects.filter(leida=False).update(leida=True)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def declaracion_pdf(request, pk):
    """Documento imprimible/archivable de la declaración de método completa
    — datos generales, actividades con su evaluación Kinney antes/después
    de mitigar, y las firmas registradas."""
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa

    qs = DeclaracionMetodo.objects.select_related("contratista").prefetch_related("actividades", "firmas")
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(contratista_id=contratista_id)
    declaracion = get_object_or_404(qs, pk=pk)

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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def declaracion_excel(request, pk):
    """Descarga la declaración de método en Excel. Si se creó importando un
    Excel, descarga ese mismo archivo original (mismo formato con el que lo
    diligenció el contratista) con una hoja "Decisión SST" agregada al
    final con el estado y las observaciones de la revisión — así el
    archivo que se sube y el que se descarga quedan en el mismo formato.
    Si no tiene un Excel original adjunto (se llenó a mano), genera el
    libro de 5 hojas propio — ver contratistas/exportar_declaracion_excel.py."""
    from django.http import HttpResponse

    from .exportar_declaracion_excel import generar_excel_declaracion, generar_excel_desde_original

    qs = DeclaracionMetodo.objects.select_related("contratista").prefetch_related("actividades", "firmas")
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(contratista_id=contratista_id)
    declaracion = get_object_or_404(qs, pk=pk)

    libro = generar_excel_desde_original(declaracion) or generar_excel_declaracion(declaracion)
    respuesta = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    respuesta["Content-Disposition"] = f'attachment; filename="declaracion-metodo-{declaracion.pk}.xlsx"'
    libro.save(respuesta)
    return respuesta


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def declaracion_importar_excel(request):
    """Lee un Excel de Declaración de Método en el formato real del cliente
    (mismas 5 hojas del export) y devuelve los datos ya parseados para
    precargar el formulario — no crea ni guarda nada. Quien sube el
    archivo sigue revisando y guardando desde el formulario normal, igual
    que si lo hubiera escrito a mano."""
    from django.core.exceptions import ValidationError as DjangoValidationError

    from core.validators import validar_tamano_archivo

    from .importar_declaracion_excel import ErrorImportacionExcel, parsear_excel_declaracion

    archivo = request.FILES.get("archivo")
    if not archivo:
        return Response({"detail": "Hace falta adjuntar un archivo."}, status=status.HTTP_400_BAD_REQUEST)
    if not archivo.name.lower().endswith(".xlsx"):
        return Response({"detail": "El archivo debe ser un .xlsx."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validar_tamano_archivo(archivo)
    except DjangoValidationError as exc:
        return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)

    try:
        resultado = parsear_excel_declaracion(archivo)
    except ErrorImportacionExcel as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(resultado)


@api_view(["GET"])
@permission_classes([EsPersonalInterno])
def declaracion_alertas(request, pk):
    """Alertas automáticas de la declaración — solo para quien la revisa.
    No decide nada por sí solo: son advertencias informativas con un motivo
    de rechazo sugerido, para que el revisor las tenga en cuenta al aprobar
    o rechazar. Ver contratistas/alertas_automaticas.py."""
    from .alertas_automaticas import generar_alertas

    qs = DeclaracionMetodo.objects.prefetch_related("actividades", "firmas")
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(contratista_id=contratista_id)
    declaracion = get_object_or_404(qs, pk=pk)

    return Response(generar_alertas(declaracion))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def declaracion_subir_archivo_origen(request, pk):
    """Guarda el Excel original que se subió para importar esta declaración
    (o cualquier otro Excel de referencia), para que quien la revisa pueda
    abrirlo y compararlo contra lo que quedó cargado en el formulario."""
    from django.core.exceptions import ValidationError as DjangoValidationError

    from core.validators import validar_tamano_archivo

    qs = DeclaracionMetodo.objects.all()
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(contratista_id=contratista_id)
    declaracion = get_object_or_404(qs, pk=pk)

    archivo = request.FILES.get("archivo")
    if not archivo:
        return Response({"detail": "Hace falta adjuntar un archivo."}, status=status.HTTP_400_BAD_REQUEST)
    if not archivo.name.lower().endswith(".xlsx"):
        return Response({"detail": "El archivo debe ser un .xlsx."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validar_tamano_archivo(archivo)
    except DjangoValidationError as exc:
        return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)

    declaracion.archivo_origen_excel = archivo
    declaracion.save(update_fields=["archivo_origen_excel"])
    return Response(DeclaracionMetodoSerializer(declaracion, context={"request": request}).data)


@api_view(["GET", "POST"])
@permission_classes([EsPersonalInterno])
def notas_alertas_declaracion(request, pk):
    """Notas que deja el personal de SST/interventoría sobre una alerta
    automática puntual — identificada por su código más el orden de la
    actividad que la disparó (ver contratistas.models.NotaAlerta) — para
    dejar registrado por qué se actuó o no sobre ella. No reemplaza el
    campo Observaciones general ni cambia el estado de la declaración; solo
    para quien revisa, igual que el panel de alertas."""
    declaracion = get_object_or_404(DeclaracionMetodo, pk=pk)

    if request.method == "GET":
        notas = declaracion.notas_alertas.order_by("creada_en")
        return Response(NotaAlertaSerializer(notas, many=True).data)

    entrada = NotaAlertaSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    nota = entrada.save(
        declaracion=declaracion,
        autor=request.user,
        autor_nombre=request.user.get_full_name() or request.user.username,
    )
    return Response(NotaAlertaSerializer(nota).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def autorizacion_ingreso_pdf(request, pk):
    """Documento imprimible con el mismo formato del "AUTORIZACION DE INGRESO
    PERSONAL CONTRATISTA — INCLUSIONES/EXCLUSIONES" real de la planta:
    encabezado con código de documento, datos generales, tabla de
    inclusiones, tabla de exclusiones con motivo, y las líneas de firma en
    blanco de la empresa contratista y del interventor."""
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa

    qs = AutorizacionIngreso.objects.select_related("contratista", "declaracion").prefetch_related(
        "trabajadores__trabajador"
    )
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(contratista_id=contratista_id)
    autorizacion = get_object_or_404(qs, pk=pk)
    lineas = list(autorizacion.trabajadores.all())
    incluidos = [linea for linea in lineas if linea.incluido]
    excluidos = [linea for linea in lineas if not linea.incluido]

    html = render_to_string(
        "contratistas/autorizacion_ingreso_pdf.html",
        {"autorizacion": autorizacion, "incluidos": incluidos, "excluidos": excluidos},
    )
    respuesta = HttpResponse(content_type="application/pdf")
    respuesta["Content-Disposition"] = f'inline; filename="autorizacion-ingreso-{autorizacion.pk}.pdf"'
    resultado = pisa.CreatePDF(html, dest=respuesta)
    if resultado.err:
        return Response({"detail": "No se pudo generar el PDF."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return respuesta


# --- Capacitación previa a ingreso ---
# Reimplementación del "FDT Evalúa visitantes" (Google Apps Script) que
# usaba el cliente: registro del participante, video de inducción,
# evaluación de 10 preguntas calificada en el servidor (nunca se manda la
# respuesta correcta al navegador) y certificado si aprueba. Solo queda
# habilitada por empresa contratista cuando ya tiene una Declaración de
# Método aprobada, o cuando un Administrador la habilita manualmente — ver
# EmpresaContratista.capacitacion_habilitada.


class ConfiguracionCapacitacionDetalle(generics.RetrieveUpdateAPIView):
    """Fila única — título, video y puntaje mínimo de la inducción,
    editables por un Administrador en vez de fijos en el código. La lectura
    queda abierta a cualquier autenticado (incluido el portal de
    contratistas): son justo quienes hacen el curso y necesitan el video."""

    serializer_class = ConfiguracionCapacitacionSerializer
    permission_classes = [EsAdministradorOSoloLectura]

    def get_object(self):
        return ConfiguracionCapacitacion.obtener()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preguntas_capacitacion(request):
    """Preguntas activas de la evaluación, sin la respuesta correcta."""
    preguntas = PreguntaCapacitacion.objects.filter(activa=True)
    return Response(PreguntaCapacitacionPublicaSerializer(preguntas, many=True).data)


class RegistroCapacitacionLista(generics.ListAPIView):
    """Reporte de quién ha hecho la inducción, con qué resultado — personal
    interno ve todas las empresas; el portal de contratistas solo la suya."""

    serializer_class = RegistroCapacitacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = RegistroCapacitacion.objects.select_related("contratista", "trabajador")
        contratista_id = _contratista_de(self.request)
        if contratista_id is not None:
            qs = qs.filter(contratista_id=contratista_id)
        else:
            filtro = self.request.query_params.get("contratista")
            if filtro:
                qs = qs.filter(contratista_id=filtro)
        return qs


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def iniciar_capacitacion(request):
    """Arranca un intento: valida que la empresa tenga la capacitación
    habilitada y crea el registro en curso. Si el documento coincide con un
    trabajador ya radicado en la misma empresa, queda vinculado desde ya."""
    contratista_id = _contratista_de(request)
    if contratista_id is None:
        contratista_id = request.data.get("contratista")
        if not contratista_id:
            return Response(
                {"detail": "Hace falta indicar la empresa contratista."}, status=status.HTTP_400_BAD_REQUEST
            )

    empresa = get_object_or_404(EmpresaContratista, pk=contratista_id)
    if not empresa.capacitacion_habilitada:
        return Response(
            {"detail": "La capacitación todavía no está habilitada para esta empresa."},
            status=status.HTTP_403_FORBIDDEN,
        )

    entrada = RegistroCapacitacionIniciarSerializer(data={**request.data, "contratista": empresa.pk})
    entrada.is_valid(raise_exception=True)

    documento = (entrada.validated_data.get("documento") or "").strip()
    trabajador = None
    if documento:
        trabajador = Trabajador.objects.filter(contratista=empresa, documento=documento).first()

    registro = entrada.save(trabajador=trabajador, creado_por=request.user)
    return Response(RegistroCapacitacionSerializer(registro).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def calificar_capacitacion(request, pk):
    """Califica la evaluación en el servidor y, si aprueba y quedó vinculada
    a un trabajador, marca 'induccion_sst' como completada en su ficha."""
    qs = RegistroCapacitacion.objects.select_related("trabajador")
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(contratista_id=contratista_id)
    registro = get_object_or_404(qs, pk=pk)

    if registro.estado != RegistroCapacitacion.Estado.EN_CURSO:
        return Response({"detail": "Esta evaluación ya fue calificada."}, status=status.HTTP_400_BAD_REQUEST)

    entrada = CalificarCapacitacionSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    respuestas = entrada.validated_data["respuestas"]

    preguntas = list(PreguntaCapacitacion.objects.filter(activa=True))
    correctas = sum(
        1
        for pregunta, respuesta in zip(preguntas, respuestas)
        if respuesta == pregunta.respuesta_correcta
    )
    total = len(preguntas)
    calificacion = round((correctas / total) * 100) if total else 0
    minimo = ConfiguracionCapacitacion.obtener().puntaje_minimo_aprobacion
    aprobado = calificacion >= minimo

    registro.respuestas = respuestas
    registro.calificacion = calificacion
    registro.estado = RegistroCapacitacion.Estado.APROBADO if aprobado else RegistroCapacitacion.Estado.NO_APROBADO
    registro.finalizado_en = timezone.now()
    registro.save(update_fields=["respuestas", "calificacion", "estado", "finalizado_en"])

    if aprobado and registro.trabajador:
        trabajador = registro.trabajador
        cursos = dict(trabajador.cursos_safety_academy or {})
        cursos["induccion_sst"] = timezone.localdate().isoformat()
        trabajador.cursos_safety_academy = cursos
        trabajador.save(update_fields=["cursos_safety_academy"])

    datos = RegistroCapacitacionSerializer(registro).data
    datos["correctas"] = correctas
    datos["total"] = total
    return Response(datos)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def capacitacion_certificado_pdf(request, pk):
    """Certificado imprimible de un registro de capacitación aprobado —
    mismo documento que ya se ve en pantalla al aprobar, disponible para
    volver a descargar después desde el reporte."""
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa

    qs = RegistroCapacitacion.objects.select_related("contratista")
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(contratista_id=contratista_id)
    registro = get_object_or_404(qs, pk=pk)

    if registro.estado != RegistroCapacitacion.Estado.APROBADO:
        return Response(
            {"detail": "Solo se puede descargar el certificado de una capacitación aprobada."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    titulo_curso = ConfiguracionCapacitacion.obtener().titulo_curso
    html = render_to_string(
        "contratistas/capacitacion_certificado_pdf.html", {"registro": registro, "titulo_curso": titulo_curso}
    )
    respuesta = HttpResponse(content_type="application/pdf")
    respuesta["Content-Disposition"] = f'inline; filename="certificado-capacitacion-{registro.pk}.pdf"'
    resultado = pisa.CreatePDF(html, dest=respuesta)
    if resultado.err:
        return Response({"detail": "No se pudo generar el certificado."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return respuesta


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def capacitacion_exportar_aprobados(request):
    """Descarga en Excel a todos los que aprobaron la inducción — filtro
    opcional ?contratista= para personal interno (el portal de contratistas
    siempre queda scopeado a la suya)."""
    from django.http import HttpResponse
    from openpyxl import Workbook

    qs = RegistroCapacitacion.objects.select_related("contratista", "trabajador").filter(
        estado=RegistroCapacitacion.Estado.APROBADO
    )
    contratista_id = _contratista_de(request)
    if contratista_id is not None:
        qs = qs.filter(contratista_id=contratista_id)
    else:
        filtro = request.query_params.get("contratista")
        if filtro:
            qs = qs.filter(contratista_id=filtro)
    qs = qs.order_by("-finalizado_en")

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Aprobados"
    hoja.append(
        ["Empresa", "Nombre", "Correo", "Documento", "Trabajador vinculado", "Calificación", "Fecha de aprobación"]
    )
    for registro in qs:
        hoja.append(
            [
                registro.contratista.nombre,
                registro.nombres,
                registro.correo,
                registro.documento,
                str(registro.trabajador) if registro.trabajador else "",
                registro.calificacion,
                timezone.localtime(registro.finalizado_en).strftime("%Y-%m-%d %H:%M") if registro.finalizado_en else "",
            ]
        )

    respuesta = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    respuesta["Content-Disposition"] = 'attachment; filename="capacitacion_aprobados.xlsx"'
    libro.save(respuesta)
    return respuesta
