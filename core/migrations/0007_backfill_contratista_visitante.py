from django.db import migrations


def backfill_contratista_visitante(apps, schema_editor):
    """Corrige perfiles con rol Visitante/Auditor que se crearon o editaron
    sin pasar por el serializer del API (ej. desde Django admin) y por eso
    se quedaron sin empresa pseudo-contratista asignada — lo que les
    bloqueaba iniciar la capacitación con 'Hace falta indicar la empresa
    contratista'."""
    PerfilUsuario = apps.get_model("core", "PerfilUsuario")
    EmpresaContratista = apps.get_model("contratistas", "EmpresaContratista")
    Empresa = apps.get_model("core", "Empresa")

    perfiles = PerfilUsuario.objects.filter(rol="visitante", contratista__isnull=True)
    if not perfiles.exists():
        return

    empresa_visitantes = EmpresaContratista.objects.filter(es_visitantes=True).first()
    if empresa_visitantes is None:
        empresa = Empresa.objects.first() or Empresa.objects.create(nombre="Empresa")
        empresa_visitantes = EmpresaContratista.objects.create(
            empresa=empresa,
            nombre="Visitas y Auditorías Externas",
            es_visitantes=True,
            capacitacion_habilitada_manual=True,
        )
    perfiles.update(contratista=empresa_visitantes)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_alter_perfilusuario_contratista_and_more"),
        ("contratistas", "0034_empresacontratista_es_visitantes"),
    ]

    operations = [
        migrations.RunPython(backfill_contratista_visitante, migrations.RunPython.noop),
    ]
