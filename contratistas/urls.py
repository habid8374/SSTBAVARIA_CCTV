from django.urls import path

from . import views

app_name = "contratistas"

urlpatterns = [
    path("catalogos/", views.catalogos, name="catalogos"),
    path("empresas/", views.EmpresaContratistaListaDashboard.as_view(), name="empresas_lista"),
    path("empresas/<int:pk>/", views.EmpresaContratistaDetalle.as_view(), name="empresas_detalle"),
    path("trabajadores/", views.TrabajadorListaDashboard.as_view(), name="trabajadores_lista"),
    path("trabajadores/<int:pk>/", views.TrabajadorDetalle.as_view(), name="trabajadores_detalle"),
    path("radicaciones/", views.RadicacionListaDashboard.as_view(), name="radicaciones_lista"),
    path("radicaciones/<int:pk>/", views.RadicacionDetalle.as_view(), name="radicaciones_detalle"),
    path("radicaciones/<int:pk>/aprobar/", views.aprobar_radicacion, name="radicaciones_aprobar"),
    path("radicaciones/<int:pk>/rechazar/", views.rechazar_radicacion, name="radicaciones_rechazar"),
    path("declaraciones/", views.DeclaracionMetodoListaDashboard.as_view(), name="declaraciones_lista"),
    path("declaraciones/<int:pk>/", views.DeclaracionMetodoDetalle.as_view(), name="declaraciones_detalle"),
    path("declaraciones/<int:pk>/firmar/", views.firmar_declaracion, name="declaraciones_firmar"),
]
