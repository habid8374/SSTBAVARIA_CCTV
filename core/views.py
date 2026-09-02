from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from camaras_ia.models import Camara, EventoDetectado

from .models import SuscripcionPush
from .permissions import EsAdministrador
from .serializers import SuscripcionPushSerializer, UsuarioCrearSerializer, UsuarioSerializer
from .throttling import LoginRateThrottle

Usuario = get_user_model()


def _serializar_usuario(user):
    perfil = getattr(user, "perfil", None)
    return {
        "id": user.pk,
        "username": user.username,
        "nombre": user.get_full_name() or user.username,
        "email": user.email,
        "is_staff": user.is_staff,
        "rol": perfil.rol if perfil else None,
        "contratista_id": perfil.contratista_id if perfil else None,
        "contratista_nombre": perfil.contratista.nombre if perfil and perfil.contratista else None,
    }


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login(request):
    """Login del dashboard: usuario/contraseña de Django -> token de API."""
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return Response(
            {"detail": "Usuario o contraseña incorrectos."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "usuario": _serializar_usuario(user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    request.user.auth_token.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def perfil(request):
    return Response(_serializar_usuario(request.user))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resumen(request):
    """Conteos simples para la pantalla inicial del dashboard — prueba de
    que el frontend y el backend ya se están hablando de verdad."""
    hoy = timezone.localdate()
    return Response(
        {
            "camaras_activas": Camara.objects.filter(activa=True).count(),
            "eventos_nuevos": EventoDetectado.objects.filter(
                estado=EventoDetectado.Estado.NUEVO
            ).count(),
            "alertas_hoy": EventoDetectado.objects.filter(
                disparo_alerta=True, timestamp__date=hoy
            ).count(),
        }
    )


class UsuarioListaCrear(generics.ListCreateAPIView):
    """Listado y alta de usuarios del dashboard. Solo Administradores."""

    queryset = Usuario.objects.select_related("perfil").order_by("username")
    permission_classes = [EsAdministrador]

    def get_serializer_class(self):
        return UsuarioCrearSerializer if self.request.method == "POST" else UsuarioSerializer


class UsuarioDetalle(generics.RetrieveUpdateDestroyAPIView):
    """Edición (rol, datos, activo) y baja de un usuario. Solo Administradores."""

    queryset = Usuario.objects.select_related("perfil").all()
    serializer_class = UsuarioSerializer
    permission_classes = [EsAdministrador]

    def perform_update(self, serializer):
        desactivando_propia_cuenta = (
            serializer.instance == self.request.user
            and serializer.validated_data.get("is_active") is False
        )
        if desactivando_propia_cuenta:
            raise PermissionDenied("No puedes desactivar tu propia cuenta.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance == self.request.user:
            raise PermissionDenied("No puedes eliminar tu propia cuenta.")
        instance.delete()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def push_vapid_public_key(request):
    """La llave pública VAPID que el navegador necesita para suscribirse
    (PushManager.subscribe({applicationServerKey})). Vacía si el servidor
    todavía no tiene el par de llaves configurado."""
    from django.conf import settings

    return Response({"clave_publica": settings.VAPID_PUBLIC_KEY})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def push_suscribir(request):
    """Guarda (o actualiza, si el navegador reusó el mismo endpoint) la
    suscripción de este dispositivo para el usuario logueado."""
    entrada = SuscripcionPushSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    datos = entrada.validated_data
    SuscripcionPush.objects.update_or_create(
        endpoint=datos["endpoint"],
        defaults={
            "usuario": request.user,
            "p256dh": datos["keys"]["p256dh"],
            "auth": datos["keys"]["auth"],
        },
    )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def push_desuscribir(request):
    """Borra la suscripción de este dispositivo — ej. al desactivar las
    notificaciones desde la campanita. Solo la propia, nunca la de otro
    usuario, aunque alguien mande un endpoint ajeno a mano."""
    endpoint = request.data.get("endpoint", "")
    SuscripcionPush.objects.filter(usuario=request.user, endpoint=endpoint).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
