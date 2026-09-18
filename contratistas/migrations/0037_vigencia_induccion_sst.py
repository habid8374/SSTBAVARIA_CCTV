import calendar

from django.db import migrations

MESES_VIGENCIA_INDUCCION_SST = 6


def _sumar_meses(fecha, meses):
    """Copia de contratistas.models._sumar_meses — las migraciones no
    importan del código de la app porque este puede cambiar más adelante,
    así que se repite acá la misma lógica (fecha + N meses calendario)."""
    mes_total = fecha.month - 1 + meses
    anio = fecha.year + mes_total // 12
    mes = mes_total % 12 + 1
    ultimo_dia_mes = calendar.monthrange(anio, mes)[1]
    return fecha.replace(year=anio, month=mes, day=min(fecha.day, ultimo_dia_mes))


def sembrar_vigencia(apps, schema_editor):
    """La inducción SST vence a los 6 meses — hasta ahora CursoSafetyAcademy
    ('induccion_sst') no tenía meses_vigencia configurado, así que ni el
    curso del trabajador ni (antes de este cambio) el registro de
    capacitación en sí quedaban con fecha de vencimiento. Se deja
    configurable (no hardcodeado) por si el cliente cambia el período más
    adelante — solo se siembra si todavía está vacío, para no pisar un
    valor que ya se haya editado a mano."""
    CursoSafetyAcademy = apps.get_model("contratistas", "CursoSafetyAcademy")
    CursoSafetyAcademy.objects.filter(clave="induccion_sst", meses_vigencia__isnull=True).update(
        meses_vigencia=MESES_VIGENCIA_INDUCCION_SST
    )

    RegistroCapacitacion = apps.get_model("contratistas", "RegistroCapacitacion")
    for registro in RegistroCapacitacion.objects.filter(
        estado="aprobado", fecha_vencimiento__isnull=True, finalizado_en__isnull=False
    ):
        base = registro.finalizado_en.date() if hasattr(registro.finalizado_en, "date") else registro.finalizado_en
        registro.fecha_vencimiento = _sumar_meses(base, MESES_VIGENCIA_INDUCCION_SST)
        registro.save(update_fields=["fecha_vencimiento"])


class Migration(migrations.Migration):

    dependencies = [
        ("contratistas", "0036_registrocapacitacion_fecha_vencimiento"),
    ]

    operations = [
        migrations.RunPython(sembrar_vigencia, migrations.RunPython.noop),
    ]
