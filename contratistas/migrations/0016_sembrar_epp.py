from django.db import migrations

EQUIPOS_EPP = [
    "Casco de seguridad",
    "Gafas de seguridad",
    "Chaleco de seguridad",
    "Guantes tipo: Nitrilo, Carnaza, Anticorte, dieléctricos",
    "Calzado de seguridad",
    "Traje impermeable",
    "Careta o protección facial",
    "Protección respiratoria",
    "Protección auditiva",
    "Peto, mangas de carnaza",
    "Otros: Equipo contra caídas (Arnés de seguridad, línea retráctil, doble gancho)",
]


def sembrar(apps, schema_editor):
    """Catálogo de EPP tomado tal cual del formato real de Declaración de
    Método del cliente (hoja "Firmas,Permisos, EPP") — mismo patrón que la
    siembra de PERMISOS_TRABAJO en 0008_sembrar_cursos_y_permisos."""
    EquipoProteccionPersonal = apps.get_model("contratistas", "EquipoProteccionPersonal")
    for orden, nombre in enumerate(EQUIPOS_EPP):
        EquipoProteccionPersonal.objects.get_or_create(nombre=nombre, defaults={"orden": orden})


def deshacer(apps, schema_editor):
    EquipoProteccionPersonal = apps.get_model("contratistas", "EquipoProteccionPersonal")
    EquipoProteccionPersonal.objects.filter(nombre__in=EQUIPOS_EPP).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("contratistas", "0015_equipoproteccionpersonal_and_more"),
    ]

    operations = [
        migrations.RunPython(sembrar, deshacer),
    ]
