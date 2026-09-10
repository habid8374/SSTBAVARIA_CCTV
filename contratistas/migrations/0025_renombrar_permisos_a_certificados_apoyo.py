from django.db import migrations

# El personal de SST del cliente aclaró que en su formato real solo existe UN
# permiso de trabajo general (ahora ActividadMetodo.requiere_permiso_trabajo,
# ver migración 0024) — los demás ítems de este catálogo son certificados de
# apoyo específicos por tipo de riesgo, no "permisos" en sí. Se renombran los
# 8 ítems que todavía decían "Permiso..." para que quede claro. Nombre
# anterior -> nuevo.
RENOMBRES = {
    "Permiso de trabajo en espacios confinados": "Certificado de apoyo en espacios confinados",
    "Permiso LOTO / bloqueo y etiquetado de energías": "Certificado de apoyo LOTO / bloqueo y etiquetado de energías",
    "Permiso de trabajo en procesos de alto riesgo": "Certificado de apoyo en procesos de alto riesgo",
    "Permiso de trabajo — gestión operacional": "Certificado de apoyo — gestión operacional",
    "Permiso de seguridad vial y conducción": "Certificado de apoyo en seguridad vial y conducción",
    "Permiso de trabajo en alturas / protección contra caídas": "Certificado de apoyo en alturas / protección contra caídas",
    "Permiso de manejo de sustancias peligrosas": "Certificado de apoyo en manejo de sustancias peligrosas",
    "Permiso de trabajo eléctrico": "Certificado de apoyo en trabajo eléctrico",
}


def renombrar(apps, schema_editor):
    PermisoTrabajo = apps.get_model("contratistas", "PermisoTrabajo")
    ActividadMetodo = apps.get_model("contratistas", "ActividadMetodo")

    for anterior, nuevo in RENOMBRES.items():
        PermisoTrabajo.objects.filter(nombre=anterior).update(nombre=nuevo)

    # El nombre viejo también queda guardado tal cual dentro del JSON de cada
    # actividad ya creada — renombrar solo el catálogo los dejaría huérfanos
    # (ya no calzarían con ningún ítem activo).
    for actividad in ActividadMetodo.objects.exclude(permisos_requeridos=[]):
        actuales = actividad.permisos_requeridos or []
        actualizados = [RENOMBRES.get(nombre, nombre) for nombre in actuales]
        if actualizados != actuales:
            actividad.permisos_requeridos = actualizados
            actividad.save(update_fields=["permisos_requeridos"])


def deshacer(apps, schema_editor):
    PermisoTrabajo = apps.get_model("contratistas", "PermisoTrabajo")
    ActividadMetodo = apps.get_model("contratistas", "ActividadMetodo")
    inversos = {nuevo: anterior for anterior, nuevo in RENOMBRES.items()}

    for nuevo, anterior in inversos.items():
        PermisoTrabajo.objects.filter(nombre=nuevo).update(nombre=anterior)

    for actividad in ActividadMetodo.objects.exclude(permisos_requeridos=[]):
        actuales = actividad.permisos_requeridos or []
        actualizados = [inversos.get(nombre, nombre) for nombre in actuales]
        if actualizados != actuales:
            actividad.permisos_requeridos = actualizados
            actividad.save(update_fields=["permisos_requeridos"])


class Migration(migrations.Migration):

    dependencies = [
        ("contratistas", "0024_actividadmetodo_requiere_permiso_trabajo_and_more"),
    ]

    operations = [
        migrations.RunPython(renombrar, deshacer),
    ]
