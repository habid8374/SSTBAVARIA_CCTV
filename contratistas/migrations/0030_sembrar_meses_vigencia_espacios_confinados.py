from django.db import migrations


def sembrar(apps, schema_editor):
    """El cliente confirmó que espacios confinados vence cada 36 meses —
    se siembra acá para que la sugerencia de fecha de vencimiento en el
    formulario ya venga configurada; el resto de certificaciones queda sin
    período conocido (meses_vigencia=None) hasta que se confirme cada una."""
    CertificacionEspecial = apps.get_model("contratistas", "CertificacionEspecial")
    CertificacionEspecial.objects.filter(clave="espacios_confinados").update(meses_vigencia=36)


def deshacer(apps, schema_editor):
    CertificacionEspecial = apps.get_model("contratistas", "CertificacionEspecial")
    CertificacionEspecial.objects.filter(clave="espacios_confinados").update(meses_vigencia=None)


class Migration(migrations.Migration):

    dependencies = [
        ("contratistas", "0029_certificacionespecial_meses_vigencia_and_more"),
    ]

    operations = [
        migrations.RunPython(sembrar, deshacer),
    ]
