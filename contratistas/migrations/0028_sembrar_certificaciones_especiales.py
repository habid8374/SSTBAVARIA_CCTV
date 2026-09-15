from django.db import migrations

CERTIFICACIONES = {
    "espacios_confinados": "Espacios confinados",
    "conduccion_vehiculos": "Conducción de vehículos / montacargas",
    "manlift": "Operación de manlift",
    "grua": "Operación de grúa",
    "soldador": "Soldador",
    "rescatista": "Rescatista",
    "licencia_sst": "Licencia en Seguridad y Salud en el Trabajo",
}


def sembrar(apps, schema_editor):
    """Claves tomadas del formato real de control de ingresos del cliente
    ("TABLA INGRESOS") — certificaciones de trabajo especializado que solo
    aplican a quien realiza esa actividad puntual (distinto de los cursos
    Safety Academy, que aplican a todo trabajador)."""
    CertificacionEspecial = apps.get_model("contratistas", "CertificacionEspecial")
    for orden, (clave, etiqueta) in enumerate(CERTIFICACIONES.items()):
        CertificacionEspecial.objects.get_or_create(clave=clave, defaults={"etiqueta": etiqueta, "orden": orden})


def deshacer(apps, schema_editor):
    CertificacionEspecial = apps.get_model("contratistas", "CertificacionEspecial")
    CertificacionEspecial.objects.filter(clave__in=CERTIFICACIONES.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("contratistas", "0027_certificacionespecial_and_more"),
    ]

    operations = [
        migrations.RunPython(sembrar, deshacer),
    ]
