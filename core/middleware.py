import re

from django.http import JsonResponse
from rest_framework.authtoken.models import Token

from .models import PerfilUsuario

# Rutas exactas que el rol Visitante/Auditor puede llegar a tocar — login y
# perfil (para que el dashboard cargue), y el flujo de tomar la inducción.
# Todo lo demás queda cortado más abajo, sin importar qué permission_classes
# tenga declarada la vista (la mayoría del resto del dashboard solo exige
# "¿está logueado?", no revisa el rol).
_RUTAS_EXACTAS_VISITANTE = {
    "/api/auth/login/",
    "/api/auth/logout/",
    "/api/auth/perfil/",
    "/api/contratistas/capacitacion/configuracion/",
    "/api/contratistas/capacitacion/preguntas/",
    "/api/contratistas/capacitacion/iniciar/",
}
# .../capacitacion/<pk>/calificar/ y .../capacitacion/<pk>/certificado/
_PATRON_RUTA_VISITANTE = re.compile(r"^/api/contratistas/capacitacion/\d+/(calificar|certificado)/$")


class RestringirVisitanteMiddleware:
    """El rol Visitante/Auditor (visitas externas y auditorías a planta,
    ver PerfilUsuario.Rol.VISITANTE) solo puede llegar a las rutas de
    Capacitación de arriba — se corta acá, antes de que cada vista decida
    su propio permission_classes, para no depender de que cada vista nueva
    recuerde excluir este rol.

    El token se resuelve a mano (no con request.user) porque en este punto
    del pipeline todavía no corrió TokenAuthentication de DRF — eso solo
    pasa dentro del dispatch de cada vista, después de este middleware."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        encabezado = request.headers.get("Authorization", "")
        if encabezado.startswith("Token "):
            token = (
                Token.objects.filter(key=encabezado[len("Token "):].strip())
                .select_related("user__perfil")
                .first()
            )
            perfil = getattr(token.user, "perfil", None) if token else None
            if perfil and perfil.rol == PerfilUsuario.Rol.VISITANTE:
                permitido = request.path in _RUTAS_EXACTAS_VISITANTE or _PATRON_RUTA_VISITANTE.match(
                    request.path
                )
                if not permitido:
                    return JsonResponse(
                        {"detail": "Este usuario solo tiene acceso al módulo de Capacitación."},
                        status=403,
                    )
        return self.get_response(request)


class PermitirIframeAdminMiddleware:
    """Permite insertar /admin/ (Django admin) en un <iframe> — pero solo
    desde los orígenes del propio dashboard (ver settings.CORS_ALLOWED_ORIGINS),
    no desde cualquier sitio. Existe para que el link "Admin de Django" del
    sidebar (solo Administrador) se pueda abrir embebido dentro de la PWA en
    vez de siempre disparar el navegador del celular (una PWA instalada saca
    al navegador normal cualquier link a un origen distinto al suyo).

    X-Frame-Options no soporta listar orígenes puntuales (solo DENY,
    SAMEORIGIN, o el ya retirado ALLOW-FROM) — por eso se marca la
    respuesta como exenta de XFrameOptionsMiddleware (que si no, pondría
    X-Frame-Options: DENY encima y bloquearía incluso al propio dashboard) y
    en su lugar se manda Content-Security-Policy: frame-ancestors, que sí
    soporta una lista y además tiene prioridad sobre X-Frame-Options en los
    navegadores modernos.

    El resto del sitio (todo lo que no sea /admin/) sigue con
    X-Frame-Options: DENY normal — la protección contra clickjacking no se
    toca fuera del admin. Debe ir DESPUÉS de XFrameOptionsMiddleware en
    settings.MIDDLEWARE (la fase de respuesta corre en orden inverso a la
    lista, así que "después" en la lista es "antes" en la respuesta — el
    exempt tiene que quedar puesto antes de que XFrameOptionsMiddleware lo
    revise)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/admin/"):
            from django.conf import settings

            origenes = " ".join(settings.CORS_ALLOWED_ORIGINS)
            response.xframe_options_exempt = True
            response["Content-Security-Policy"] = f"frame-ancestors 'self' {origenes};"
        return response
