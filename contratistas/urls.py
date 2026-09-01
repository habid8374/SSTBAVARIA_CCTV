from django.urls import path

from . import views

app_name = "contratistas"

urlpatterns = [
    path("catalogos/", views.catalogos, name="catalogos"),
    path("indicadores/", views.indicadores, name="indicadores"),
    path("indicadores/dashboard/", views.indicadores_dashboard, name="indicadores_dashboard"),
    path("funcionarios/", views.FuncionarioListaDashboard.as_view(), name="funcionarios_lista"),
    path("funcionarios/<int:pk>/", views.FuncionarioDetalle.as_view(), name="funcionarios_detalle"),
    path("cursos/", views.CursoSafetyAcademyListaDashboard.as_view(), name="cursos_lista"),
    path("cursos/<int:pk>/", views.CursoSafetyAcademyDetalle.as_view(), name="cursos_detalle"),
    path("permisos-trabajo/", views.PermisoTrabajoListaDashboard.as_view(), name="permisos_lista"),
    path("permisos-trabajo/<int:pk>/", views.PermisoTrabajoDetalle.as_view(), name="permisos_detalle"),
    path("equipos-epp/", views.EquipoProteccionPersonalListaDashboard.as_view(), name="equipos_epp_lista"),
    path("equipos-epp/<int:pk>/", views.EquipoProteccionPersonalDetalle.as_view(), name="equipos_epp_detalle"),
    path("configuracion-alertas/", views.ConfiguracionAlertasDetalle.as_view(), name="configuracion_alertas"),
    path("auditoria/", views.RegistroAuditoriaLista.as_view(), name="auditoria_lista"),
    path("notificaciones-internas/", views.NotificacionInternaLista.as_view(), name="notificaciones_internas_lista"),
    path(
        "notificaciones-internas/<int:pk>/marcar-leida/",
        views.marcar_notificacion_leida,
        name="notificaciones_internas_marcar_leida",
    ),
    path(
        "notificaciones-internas/marcar-todas-leidas/",
        views.marcar_todas_notificaciones_leidas,
        name="notificaciones_internas_marcar_todas_leidas",
    ),
    path("empresas/", views.EmpresaContratistaListaDashboard.as_view(), name="empresas_lista"),
    path("empresas/<int:pk>/", views.EmpresaContratistaDetalle.as_view(), name="empresas_detalle"),
    path("trabajadores/", views.TrabajadorListaDashboard.as_view(), name="trabajadores_lista"),
    path("trabajadores/<int:pk>/", views.TrabajadorDetalle.as_view(), name="trabajadores_detalle"),
    path("radicaciones/", views.RadicacionListaDashboard.as_view(), name="radicaciones_lista"),
    path("radicaciones/exportar/", views.radicaciones_exportar, name="radicaciones_exportar"),
    path("radicaciones/<int:pk>/", views.RadicacionDetalle.as_view(), name="radicaciones_detalle"),
    path("radicaciones/<int:pk>/aprobar/", views.aprobar_radicacion, name="radicaciones_aprobar"),
    path("radicaciones/<int:pk>/rechazar/", views.rechazar_radicacion, name="radicaciones_rechazar"),
    path("declaraciones/", views.DeclaracionMetodoListaDashboard.as_view(), name="declaraciones_lista"),
    path(
        "declaraciones/importar-excel/",
        views.declaracion_importar_excel,
        name="declaraciones_importar_excel",
    ),
    path("declaraciones/<int:pk>/", views.DeclaracionMetodoDetalle.as_view(), name="declaraciones_detalle"),
    path("declaraciones/<int:pk>/firmar/", views.firmar_declaracion, name="declaraciones_firmar"),
    path("declaraciones/<int:pk>/pdf/", views.declaracion_pdf, name="declaraciones_pdf"),
    path("declaraciones/<int:pk>/excel/", views.declaracion_excel, name="declaraciones_excel"),
    path("declaraciones/<int:pk>/alertas/", views.declaracion_alertas, name="declaraciones_alertas"),
    path(
        "declaraciones/<int:pk>/archivo-origen/",
        views.declaracion_subir_archivo_origen,
        name="declaraciones_archivo_origen",
    ),
    path(
        "declaraciones/<int:pk>/notas-alertas/",
        views.notas_alertas_declaracion,
        name="declaraciones_notas_alertas",
    ),
    path(
        "autorizaciones-ingreso/",
        views.AutorizacionIngresoListaDashboard.as_view(),
        name="autorizaciones_ingreso_lista",
    ),
    path(
        "autorizaciones-ingreso/<int:pk>/",
        views.AutorizacionIngresoDetalle.as_view(),
        name="autorizaciones_ingreso_detalle",
    ),
    path(
        "autorizaciones-ingreso/<int:pk>/pdf/",
        views.autorizacion_ingreso_pdf,
        name="autorizaciones_ingreso_pdf",
    ),
]
