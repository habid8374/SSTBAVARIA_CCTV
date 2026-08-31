"""Helpers para capturar y registrar la traza de auditoría de los modelos
críticos de cumplimiento. Ver RegistroAuditoria en models.py."""

from datetime import date, datetime

from django.db.models.fields.files import FieldFile

from .models import RegistroAuditoria


def _valor_serializable(valor):
    if isinstance(valor, FieldFile):
        return valor.name or ""
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def capturar_snapshot(instancia):
    """Diccionario campo -> valor de los campos concretos del modelo, listo
    para comparar o guardar en un JSONField. Para FK usa el id (campo.attname)
    en vez del objeto relacionado, para no disparar una consulta extra por
    cada campo."""
    return {
        campo.name: _valor_serializable(getattr(instancia, campo.attname))
        for campo in instancia._meta.concrete_fields
    }


def registrar_auditoria(usuario, instancia, accion, snapshot_anterior=None):
    """Crea un RegistroAuditoria. Para "actualizado", compara snapshot_anterior
    contra el estado actual y solo registra los campos que cambiaron — si no
    cambió nada, no crea registro."""
    cambios = {}
    if accion == RegistroAuditoria.Accion.ACTUALIZADO:
        if snapshot_anterior is None:
            return
        snapshot_actual = capturar_snapshot(instancia)
        for campo, valor_anterior in snapshot_anterior.items():
            valor_actual = snapshot_actual.get(campo)
            if valor_actual != valor_anterior:
                cambios[campo] = {"antes": valor_anterior, "despues": valor_actual}
        if not cambios:
            return

    RegistroAuditoria.objects.create(
        modelo=type(instancia).__name__,
        objeto_id=instancia.pk,
        objeto_str=str(instancia)[:300],
        accion=accion,
        usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
        cambios=cambios,
    )
