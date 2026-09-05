import io
import time
import zipfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.models import Empresa
from core.permissions import EsAdministrador, EsAdministradorOSoloLectura

from .models import Camara, ConfiguracionNotificaciones, EquipoLocal, EventoDetectado, ReglaAlerta, ZonaRestringida
from .serializers import (
    CamaraActivaSerializer,
    CamaraCalibracionSerializer,
    CamaraCrearSerializer,
    CamaraDashboardSerializer,
    ConfiguracionNotificacionesSerializer,
    EquipoLocalSerializer,
    EventoDashboardSerializer,
    EventoEntradaSerializer,
    ReglaAlertaSerializer,
    SnapshotReferenciaSerializer,
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
@permission_classes([AllowAny])  # se autentica con su propia API key, no con el login de usuario
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
@permission_classes([AllowAny])  # se autentica con su propia API key, no con el login de usuario
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
            # context con el request: sin esto, snapshot_referencia vendría
            # como ruta relativa (/media/...) — el equipo local corre en otra
            # máquina y necesita la URL absoluta para poder descargarla.
            "camaras": CamaraActivaSerializer(camaras_activas, many=True, context={"request": request}).data,
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
    """Bandeja de Alertas / Envíos de Notificaciones: lista de eventos, más
    recientes primero, con filtros opcionales
    ?estado=&disparo_alerta=&camara=&canal_notificacion=."""

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
        canal_notificacion = self.request.query_params.get("canal_notificacion")
        if canal_notificacion:
            qs = qs.filter(canal_notificacion=canal_notificacion)
        return qs[:200]


class EventoDetalleDashboard(generics.RetrieveUpdateAPIView):
    """Marcar un evento como revisado (o de vuelta a nuevo)."""

    queryset = EventoDetectado.objects.select_related("camara", "zona")
    serializer_class = EventoDashboardSerializer
    permission_classes = [IsAuthenticated]


class CamaraListaDashboard(generics.ListCreateAPIView):
    """Cámaras con sus zonas y el último evento — usado por el Tablero y la
    vista de Cámaras IA con overlays. Alta de cámaras nuevas, solo
    Administrador."""

    queryset = Camara.objects.prefetch_related("zonas__reglas", "eventos").order_by("nombre")
    permission_classes = [EsAdministradorOSoloLectura]

    def get_serializer_class(self):
        return CamaraCrearSerializer if self.request.method == "POST" else CamaraDashboardSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        camara = serializer.save()
        return Response(
            CamaraDashboardSerializer(camara, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class CamaraDetalleDashboard(generics.RetrieveUpdateDestroyAPIView):
    """Editar datos/credenciales ONVIF, activar/desactivar o eliminar una
    cámara. Solo Administrador puede escribir."""

    queryset = Camara.objects.prefetch_related("zonas__reglas", "eventos")
    serializer_class = CamaraDashboardSerializer
    permission_classes = [EsAdministradorOSoloLectura]


@api_view(["POST"])
@permission_classes([EsAdministrador])
def subir_snapshot_referencia(request, pk):
    """Sube/reemplaza el encuadre de referencia de una cámara, sobre el que
    se dibujan las zonas restringidas en el editor visual."""
    camara = get_object_or_404(Camara, pk=pk)
    entrada = SnapshotReferenciaSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    camara.snapshot_referencia = entrada.validated_data["snapshot_referencia"]
    camara.save(update_fields=["snapshot_referencia"])
    return Response(CamaraDashboardSerializer(camara, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([EsAdministrador])
def calibrar_camara(request, pk):
    """Guarda la calibración de una cámara: dos puntos marcados sobre el
    snapshot de referencia y la distancia real (en metros) entre ellos —
    con eso, Camara.px_por_metro queda disponible para las zonas tipo
    "punto y radio" (ver services.punto_en_zona)."""
    camara = get_object_or_404(Camara, pk=pk)
    entrada = CamaraCalibracionSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    (x1, y1), (x2, y2) = entrada.validated_data["punto1"], entrada.validated_data["punto2"]
    camara.calibracion_punto1_x = x1
    camara.calibracion_punto1_y = y1
    camara.calibracion_punto2_x = x2
    camara.calibracion_punto2_y = y2
    camara.calibracion_distancia_metros = entrada.validated_data["distancia_metros"]
    camara.save(
        update_fields=[
            "calibracion_punto1_x",
            "calibracion_punto1_y",
            "calibracion_punto2_x",
            "calibracion_punto2_y",
            "calibracion_distancia_metros",
        ]
    )
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


# --- Sección Sistema: credenciales Brevo + gestión de equipos locales ---


class ConfiguracionNotificacionesDetalle(generics.RetrieveUpdateAPIView):
    """Fila única — el administrador digita acá la API key de Brevo en vez
    de depender de una variable de entorno en Railway."""

    serializer_class = ConfiguracionNotificacionesSerializer
    permission_classes = [EsAdministradorOSoloLectura]

    def get_object(self):
        return ConfiguracionNotificaciones.obtener()


class EquipoLocalListaCrear(generics.ListCreateAPIView):
    """Alta y listado de equipos locales (mini-PC en sitio) desde el
    dashboard — antes solo existía por el admin de Django."""

    queryset = EquipoLocal.objects.order_by("nombre")
    serializer_class = EquipoLocalSerializer
    permission_classes = [EsAdministradorOSoloLectura]

    def perform_create(self, serializer):
        empresa = Empresa.objects.first()
        if empresa is None:
            empresa = Empresa.objects.create(nombre="Empresa")
        serializer.save(empresa=empresa)


class EquipoLocalDetalle(generics.RetrieveUpdateDestroyAPIView):
    """Activar/desactivar o eliminar un equipo local."""

    queryset = EquipoLocal.objects.all()
    serializer_class = EquipoLocalSerializer
    permission_classes = [EsAdministradorOSoloLectura]


_EQUIPO_LOCAL_EXCLUIR_DEL_ZIP = {"venv", "__pycache__", "grabaciones", "tests", ".pytest_cache"}


def _env_real_para_equipo(request, equipo):
    """Arma el contenido de un .env ya completo (URL del backend + api_key
    de este equipo en particular) — la persona que instala en el PC de la
    planta no tiene que editar ni pegar nada a mano."""
    api_base_url = request.build_absolute_uri("/").rstrip("/")
    return (
        "# Generado automáticamente para este equipo — ya viene completo,\n"
        "# no hace falta editar nada. No lo compartas: trae una API key.\n"
        "\n"
        f"API_BASE_URL={api_base_url}\n"
        f"API_KEY={equipo.api_key}\n"
    )


@api_view(["GET"])
@permission_classes([EsAdministradorOSoloLectura])
def descargar_equipo_local_zip(request):
    """Empaqueta la carpeta equipo_local/ (el programa que corre en el PC
    de la planta) en un .zip listo para copiar a ese PC, con el .env ya
    completo (URL del backend + api_key) del equipo indicado en
    ?equipo_id= — así quien lo instala no necesita acceso al repositorio de
    código ni editar nada a mano, solo el dashboard. Se arma al vuelo desde
    el mismo checkout que corre este backend en Railway; excluye lo que no
    hace falta llevar (entornos virtuales, cachés, grabaciones, tests)."""
    equipo_id = request.query_params.get("equipo_id")
    if not equipo_id:
        return Response({"detail": "Falta el parámetro equipo_id."}, status=status.HTTP_400_BAD_REQUEST)
    equipo = get_object_or_404(EquipoLocal, pk=equipo_id)

    carpeta = Path(settings.BASE_DIR) / "equipo_local"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_archivo:
        for ruta in sorted(carpeta.rglob("*")):
            if not ruta.is_file():
                continue
            partes = ruta.relative_to(carpeta.parent).parts
            if any(parte in _EQUIPO_LOCAL_EXCLUIR_DEL_ZIP or parte.endswith(".pyc") for parte in partes):
                continue
            if ruta.name == ".env.example":
                continue  # se reemplaza por el .env real de abajo
            arcname = str(ruta.relative_to(carpeta.parent))
            info = zipfile.ZipInfo(arcname, date_time=time.localtime(ruta.stat().st_mtime)[:6])
            # Conserva el bit ejecutable (necesario para instalar.sh en Linux/Mac).
            info.external_attr = (ruta.stat().st_mode & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zip_archivo.writestr(info, ruta.read_bytes())

        zip_archivo.writestr("equipo_local/.env", _env_real_para_equipo(request, equipo))

    respuesta = HttpResponse(buffer.getvalue(), content_type="application/zip")
    respuesta["Content-Disposition"] = 'attachment; filename="equipo_local.zip"'
    return respuesta
