from django.db import migrations

# Reemplazo completo del catálogo de Permisos de trabajo con las 18
# políticas ZBS Safety vigentes que envió el cliente. Cada nombre resume el
# título real del SOP/VPO correspondiente.
PERMISOS_TRABAJO_NUEVOS = [
    "Permiso de trabajo en espacios confinados",  # SOP.MAZ.SAFE.1.6
    "Permiso LOTO / bloqueo y etiquetado de energías",  # VPO SAFE 1.1
    "Permiso de trabajo en procesos de alto riesgo",  # VPO.SAFE.1.2
    "Permiso de trabajo — gestión operacional",  # VPO SAFE 2.2
    "Permiso de seguridad vial y conducción",  # SAFE 1.8
    "Permiso de trabajo en alturas / protección contra caídas",  # SAFE 1.9
    "Permiso de manejo de sustancias peligrosas",  # VPO.SAFE.1.5
    "Permiso de trabajo eléctrico",  # VPO.SAFE.3.1.07.05
    "Reporte de incidentes",  # SOP.SAFE.MAZ.1.1.1
    "Seguridad en circulación",  # VPO.SAFE.1.3
    "Salud ocupacional",  # VPO.SAFE.2.4
    "Gestión de contratistas y proveedores",  # SOP MAZ.SAFE.2.5
    "Respuesta a emergencias",  # SOP.MAZ.SAFE.2.6
    "Cultura de seguridad",  # SOP MAZ SAFE 3.1
    "Gestión de SIF (lesiones/fatalidades graves)",  # VPO.SAFE.3.2
    "Prevención de la violencia",  # SOP MAZ 1.7
    "Monitoreo de seguridad y coaching",  # VPO.SAFE.2.1
    "Manejo de materiales y ergonomía",  # VPO.SAFE.1.4
    # No vino un SOP específico de excavaciones entre los 18 que mandó el
    # cliente, pero se retiene este ítem (existía antes) porque
    # alertas_automaticas.py tiene 4 reglas automáticas (excavacion_sin_medidas,
    # excavacion_sobre_1_2m_salida_emergencia, excavacion_sobre_1_3m_reten_exterior,
    # excavacion_sobre_5m_requiere_andamio) que dependen de este nombre exacto —
    # quitarlo sin reemplazo las apaga en silencio. Pendiente de confirmar con
    # el cliente si hay una política de reemplazo o si de verdad se elimina.
    "Excavaciones o Demolición",
]


def reemplazar(apps, schema_editor):
    PermisoTrabajo = apps.get_model("contratistas", "PermisoTrabajo")
    PermisoTrabajo.objects.all().delete()
    for orden, nombre in enumerate(PERMISOS_TRABAJO_NUEVOS):
        PermisoTrabajo.objects.get_or_create(nombre=nombre, defaults={"orden": orden})


def deshacer(apps, schema_editor):
    """No hay forma de restaurar exactamente lo que había antes de esta
    migración (se borró) — deshacer solo quita las nuevas."""
    PermisoTrabajo = apps.get_model("contratistas", "PermisoTrabajo")
    PermisoTrabajo.objects.filter(nombre__in=PERMISOS_TRABAJO_NUEVOS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("contratistas", "0021_seed_capacitacion_fdt"),
    ]

    operations = [
        migrations.RunPython(reemplazar, deshacer),
    ]
