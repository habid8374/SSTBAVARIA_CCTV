from django.urls import path

from . import views

app_name = "camaras_ia"

urlpatterns = [
    # Equipo local (autenticado por API key)
    path("eventos/", views.recibir_evento_camara, name="recibir_evento_camara"),
    path("reglas-activas/", views.obtener_reglas_activas, name="obtener_reglas_activas"),
    # Dashboard (autenticado por usuario/token)
    path("dashboard/indicadores/", views.indicadores_dashboard, name="indicadores_dashboard"),
    path("dashboard/eventos-por-zona/", views.eventos_por_zona, name="eventos_por_zona"),
    path("dashboard/eventos/", views.EventoListaDashboard.as_view(), name="eventos_lista"),
    path("dashboard/eventos/<int:pk>/", views.EventoDetalleDashboard.as_view(), name="eventos_detalle"),
    path("dashboard/camaras/", views.CamaraListaDashboard.as_view(), name="camaras_lista"),
    path(
        "dashboard/camaras/<int:pk>/snapshot-referencia/",
        views.subir_snapshot_referencia,
        name="subir_snapshot_referencia",
    ),
    path("dashboard/zonas/", views.ZonaListaCrear.as_view(), name="zonas_lista"),
    path("dashboard/zonas/<int:pk>/", views.ZonaDetalle.as_view(), name="zonas_detalle"),
    path("dashboard/reglas/", views.ReglaListaCrear.as_view(), name="reglas_lista"),
    path("dashboard/reglas/<int:pk>/", views.ReglaDetalle.as_view(), name="reglas_detalle"),
]
