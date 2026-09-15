from django.db import migrations

CURSOS = {
    "induccion_sst": "Inducción SST",
    "riesgo_quimico": "Gestión de Riesgo Químico",
    "sam_jog_lototo": "SAM JOG LOTOTO",
    "pasos_seguros": "Pasos seguros",
    "comportamientos_condiciones": "Grupo de comportamientos y condiciones",
    "identificacion_peligros": "Identificación de peligros, valoración y control del riesgo",
    "epp": "Elementos de protección personal",
}

PERMISOS_TRABAJO = [
    "Trabajos de LOTOTO",
    "Trabajos en Altura > 1.8 m",
    "Espacio Confinado",
    "Excavaciones o Demolición",
    "Izaje (grúa, tecle, polipasto, montacargas, poleas)",
    "Subestaciones (sistemas eléctricos vivos)",
    "Trabajos en Caliente",
    "Sustancias Peligrosas a Granel",
    "Otros",
]


def sembrar(apps, schema_editor):
    """Convierte los catálogos que antes eran constantes fijas en el código
    (Trabajador.CURSOS, PERMISOS_TRABAJO) en filas editables desde el
    dashboard — mismas claves/nombres, para que los trabajadores/actividades
    ya guardados sigan encontrando su curso o permiso."""
    CursoSafetyAcademy = apps.get_model("contratistas", "CursoSafetyAcademy")
    PermisoTrabajo = apps.get_model("contratistas", "PermisoTrabajo")
    ConfiguracionAlertas = apps.get_model("contratistas", "ConfiguracionAlertas")

    for orden, (clave, etiqueta) in enumerate(CURSOS.items()):
        CursoSafetyAcademy.objects.get_or_create(clave=clave, defaults={"etiqueta": etiqueta, "orden": orden})

    for orden, nombre in enumerate(PERMISOS_TRABAJO):
        PermisoTrabajo.objects.get_or_create(nombre=nombre, defaults={"orden": orden})

    ConfiguracionAlertas.objects.get_or_create(pk=1, defaults={"dias_alerta_vencimiento": 15})


def deshacer(apps, schema_editor):
    CursoSafetyAcademy = apps.get_model("contratistas", "CursoSafetyAcademy")
    PermisoTrabajo = apps.get_model("contratistas", "PermisoTrabajo")
    CursoSafetyAcademy.objects.filter(clave__in=CURSOS.keys()).delete()
    PermisoTrabajo.objects.filter(nombre__in=PERMISOS_TRABAJO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("contratistas", "0007_configuracionalertas_cursosafetyacademy_and_more"),
    ]

    operations = [
        migrations.RunPython(sembrar, deshacer),
    ]
