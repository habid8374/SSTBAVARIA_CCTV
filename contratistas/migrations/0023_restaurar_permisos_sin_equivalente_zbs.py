from django.db import migrations

# La migración 0022 reemplazó el catálogo de Permisos de trabajo con las 18
# políticas ZBS Safety del cliente (+ "Excavaciones o Demolición", retenido
# aparte). De los 9 ítems originales, 3 no tienen un equivalente claro entre
# esas 18 políticas nuevas: "Izaje", "Trabajos en Caliente" y "Otros". Son
# tipos de permiso reales que el formato de Excel del cliente sigue usando
# tal cual (columnas fijas de su plantilla) — quitarlos sin reemplazo hace
# que el importador de Excel los marque como "no reconocidos" en cada
# declaración real que los use, y que un contratista no tenga forma de
# marcarlos a mano en el catálogo tampoco. Se restauran con su nombre
# original hasta que el cliente confirme si hay una política ZBS específica
# que los reemplace.
PERMISOS_RESTAURADOS = [
    "Izaje (grúa, tecle, polipasto, montacargas, poleas)",
    "Trabajos en Caliente",
    "Otros",
]


def restaurar(apps, schema_editor):
    PermisoTrabajo = apps.get_model("contratistas", "PermisoTrabajo")
    orden_inicial = PermisoTrabajo.objects.count()
    for indice, nombre in enumerate(PERMISOS_RESTAURADOS):
        PermisoTrabajo.objects.get_or_create(nombre=nombre, defaults={"orden": orden_inicial + indice})


def deshacer(apps, schema_editor):
    PermisoTrabajo = apps.get_model("contratistas", "PermisoTrabajo")
    PermisoTrabajo.objects.filter(nombre__in=PERMISOS_RESTAURADOS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("contratistas", "0022_reemplazar_permisos_trabajo_zbs"),
    ]

    operations = [
        migrations.RunPython(restaurar, deshacer),
    ]
