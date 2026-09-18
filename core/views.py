from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from camaras_ia.models import Camara, EventoDetectado

from .models import RegistroInicioSesion, SuscripcionPush
from .permissions import EsAdministrador, EsSuperusuario
from .serializers import (
    RegistroInicioSesionSerializer,
    SuscripcionPushSerializer,
    UsuarioCrearSerializer,
    UsuarioSerializer,
)
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
        "es_superusuario": user.is_superuser,
        "rol": perfil.rol if perfil else None,
        "contratista_id": perfil.contratista_id if perfil else None,
        "contratista_nombre": perfil.contratista.nombre if perfil and perfil.contratista else None,
    }


def _ip_cliente(request):
    """La IP real del navegador — Railway (y cualquier proxy) pone el
    REMOTE_ADDR del request en la IP del proxy, no la del cliente. La IP de
    verdad viaja en X-Forwarded-For, pero ese header lo puede mandar
    cualquiera (no solo un proxy real): tomar el primer valor de la lista
    (como se hacía antes) es tomar justo el que el cliente puede falsificar.
    El único salto de confianza es el que antepone el proxy de Railway, que
    es el ÚLTIMO de la lista — misma asunción de un solo proxy que
    REST_FRAMEWORK.NUM_PROXIES en settings.py."""
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR")
    if reenviada:
        return reenviada.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR")


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login(request):
    """Login del dashboard: usuario/contraseña de Django -> token de API.
    Cada intento (exitoso o fallido) queda en RegistroInicioSesion, con IP
    y navegador, para la auditoría de Sistema → Auditoría."""
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
    ip = _ip_cliente(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]

    if user is None or not user.is_active:
        RegistroInicioSesion.objects.create(
            username_intentado=username[:150], ip=ip, user_agent=user_agent, exitoso=False
        )
        return Response(
            {"detail": "Usuario o contraseña incorrectos."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    RegistroInicioSesion.objects.create(
        usuario=user, username_intentado=username[:150], ip=ip, user_agent=user_agent, exitoso=True
    )
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


def _correo_bienvenida_visitante(usuario, password, enlace_login, logo_url):
    """HTML del correo de bienvenida para la cuenta compartida de
    Visitante/Auditor — ver camaras_ia.notificaciones.plantilla_correo_marca
    para el diseño (identidad de marca GuardIA) compartido con el correo de
    bienvenida del portal de contratistas."""
    from camaras_ia.notificaciones import plantilla_correo_marca

    intro_html = """
            <p style="margin:0 0 16px; font-size:14px; line-height:1.6; color:#3a3a3a;">
              Es un gusto darle la bienvenida a nuestra plataforma de videovigilancia con inteligencia
              artificial y cumplimiento en seguridad y salud en el trabajo. A continuación encontrará las
              credenciales de acceso para completar la capacitación de seguridad previa a su visita o
              auditoría en planta.
            </p>"""
    nota_html = (
        "Este acceso es compartido con otras visitas y auditorías, y está habilitado únicamente para "
        "tomar el curso de Capacitación — sin visibilidad sobre ningún otro módulo del sistema. Por su "
        "seguridad, le solicitamos no reenviar este correo ni compartir la contraseña fuera de este "
        "propósito."
    )
    return plantilla_correo_marca(
        preheader="Su acceso a GuardIA ya está listo — credenciales de ingreso adjuntas.",
        eyebrow="Invitación de acceso",
        titulo="Bienvenido(a) a GuardIA",
        intro_html=intro_html,
        usuario=usuario,
        password=password,
        cta_url=enlace_login,
        cta_label="Ingresar a la plataforma",
        logo_url=logo_url,
        nota_html=nota_html,
    )


@api_view(["POST"])
@permission_classes([EsAdministrador])
def enviar_acceso_visitantes(request):
    """Genera una contraseña nueva para la cuenta compartida del rol
    Visitante/Auditor (ver PerfilUsuario.Rol.VISITANTE) y la manda por
    correo, vía Brevo, a los destinatarios indicados junto con el link del
    dashboard. Cada envío rota la contraseña — así no hace falta un botón
    aparte de "regenerar": para invalidar copias viejas (correos
    reenviados, guardados de más), basta con volver a mandar el acceso.

    La contraseña solo se guarda en la cuenta si al menos un correo se
    mandó con éxito — si Brevo no está configurado o todos los envíos
    fallan, la cuenta se queda con la contraseña que ya tenía, en vez de
    quedar con una nueva que nadie recibió."""
    import secrets

    from django.core.exceptions import ValidationError as DjangoValidationError
    from django.core.validators import validate_email

    from camaras_ia.notificaciones import ErrorEnvioCorreo, enviar_correo_brevo
    from contratistas.portal_usuarios import URL_PORTAL

    from .models import PerfilUsuario

    correos_crudos = request.data.get("correos", [])
    if not isinstance(correos_crudos, list):
        return Response({"detail": "correos debe ser una lista de direcciones."}, status=status.HTTP_400_BAD_REQUEST)

    correos = []
    for correo in correos_crudos:
        correo = (correo or "").strip()
        if not correo:
            continue
        try:
            validate_email(correo)
        except DjangoValidationError:
            return Response({"detail": f"«{correo}» no es un correo válido."}, status=status.HTTP_400_BAD_REQUEST)
        correos.append(correo)
    if not correos:
        return Response({"detail": "Hace falta al menos un correo."}, status=status.HTTP_400_BAD_REQUEST)

    visitante = (
        Usuario.objects.filter(perfil__rol=PerfilUsuario.Rol.VISITANTE, is_active=True).order_by("id").first()
    )
    if visitante is None:
        return Response(
            {"detail": "Todavía no existe la cuenta de Visitante/Auditor activa — créala primero desde Usuarios."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    password_nueva = secrets.token_urlsafe(9)
    # Se usa el dominio propio fijo (igual que el correo de bienvenida de
    # contratistas, ver contratistas/portal_usuarios.URL_PORTAL) en vez de
    # settings.FRONTEND_URL, que en producción cae al dominio de Vercel.
    enlace_login = f"{URL_PORTAL}/login"
    logo_url = f"{URL_PORTAL}/logo-guardia.png"
    asunto = "Bienvenido(a) a GuardIA — acceso a la capacitación de seguridad"
    contenido_html = _correo_bienvenida_visitante(
        usuario=visitante.username, password=password_nueva, enlace_login=enlace_login, logo_url=logo_url
    )

    errores = []
    enviados = 0
    for correo in correos:
        try:
            enviar_correo_brevo(correo, asunto, contenido_html)
            enviados += 1
        except ErrorEnvioCorreo as err:
            errores.append({"correo": correo, "detail": str(err)})

    if enviados:
        visitante.set_password(password_nueva)
        visitante.save(update_fields=["password"])

    return Response({"enviados": enviados, "errores": errores, "password_rotada": enviados > 0})


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


def _filtrar_inicios_sesion(qs, params):
    usuario_id = params.get("usuario")
    if usuario_id:
        qs = qs.filter(usuario_id=usuario_id)
    exitoso = params.get("exitoso")
    if exitoso is not None:
        qs = qs.filter(exitoso=exitoso.lower() in ("1", "true"))
    desde = params.get("desde")
    if desde:
        qs = qs.filter(fecha__date__gte=desde)
    hasta = params.get("hasta")
    if hasta:
        qs = qs.filter(fecha__date__lte=hasta)
    return qs


class RegistroInicioSesionLista(generics.ListAPIView):
    """Solo lectura — quién se conectó (o intentó) al dashboard, cuándo y
    desde qué IP, incluidos los intentos fallidos. Filtrable por
    ?usuario=&exitoso=&desde=&hasta= (fechas YYYY-MM-DD). Solo el
    superusuario real (ver EsSuperusuario) — ni siquiera otro Administrador."""

    serializer_class = RegistroInicioSesionSerializer
    permission_classes = [EsSuperusuario]

    def get_queryset(self):
        qs = RegistroInicioSesion.objects.select_related("usuario")
        qs = _filtrar_inicios_sesion(qs, self.request.query_params)
        return qs[:500]


@api_view(["GET"])
@permission_classes([EsSuperusuario])
def inicios_sesion_exportar(request):
    """Descarga en Excel los inicios de sesión que calcen con los mismos
    filtros del listado — "exportar lo que estoy viendo"."""
    from django.http import HttpResponse
    from openpyxl import Workbook

    qs = RegistroInicioSesion.objects.select_related("usuario").order_by("-fecha")
    qs = _filtrar_inicios_sesion(qs, request.query_params)

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Inicios de sesión"
    hoja.append(["Fecha", "Usuario", "Resultado", "IP", "Navegador/Dispositivo"])
    for registro in qs:
        hoja.append(
            [
                timezone.localtime(registro.fecha).strftime("%Y-%m-%d %H:%M:%S"),
                registro.usuario.username if registro.usuario else registro.username_intentado,
                "Exitoso" if registro.exitoso else "Fallido",
                registro.ip or "",
                registro.user_agent,
            ]
        )

    respuesta = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    respuesta["Content-Disposition"] = 'attachment; filename="inicios_de_sesion.xlsx"'
    libro.save(respuesta)
    return respuesta
