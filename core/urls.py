from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("perfil/", views.perfil, name="perfil"),
    path("resumen/", views.resumen, name="resumen"),
    path("usuarios/", views.UsuarioListaCrear.as_view(), name="usuarios_lista"),
    path("usuarios/<int:pk>/", views.UsuarioDetalle.as_view(), name="usuarios_detalle"),
    path("push/vapid-public-key/", views.push_vapid_public_key, name="push_vapid_public_key"),
    path("push/suscribir/", views.push_suscribir, name="push_suscribir"),
    path("push/desuscribir/", views.push_desuscribir, name="push_desuscribir"),
]
