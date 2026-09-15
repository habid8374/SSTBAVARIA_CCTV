"""Sincroniza la configuración local de zonas/reglas (almacenamiento_local)
hacia la nube — la nube pasa a ser un espejo de solo lectura, ver
camaras_ia/views.py:sincronizar_zonas_equipo_local. Nada de esto decide
alertas ni cruza zona+horario — es puramente "avisar a la nube qué hay
configurado acá" para que el dashboard lo pueda mostrar.
"""

import logging

logger = logging.getLogger("equipo_local.sincronizacion_config")

_CAMPOS_ZONA = ("nombre", "tipo", "poligono", "centro_x", "centro_y", "radio_metros", "activa")
_CAMPOS_REGLA = ("nombre", "hora_inicio", "hora_fin", "dias_semana", "canal_notificacion", "destinatario", "activa")


def sincronizar_configuracion_local(almacenamiento, cliente_api):
    """Empuja hacia la nube las zonas y reglas locales que cambiaron desde
    el último sincronizado, y las que se eliminaron localmente. Primero
    zonas (una regla necesita el cloud_id de su zona), después reglas.
    Cualquier error de red no rompe el ciclo de sincronización de main.py
    — se reintenta en el próximo ciclo."""
    try:
        _sincronizar_zonas(almacenamiento, cliente_api)
        _sincronizar_reglas(almacenamiento, cliente_api)
    except Exception:
        logger.exception("No se pudo sincronizar la configuración local con la nube.")


def _sincronizar_zonas(almacenamiento, cliente_api):
    eliminar = [z["cloud_id"] for z in almacenamiento.zonas_pendientes_de_eliminar()]
    pendientes = almacenamiento.zonas_pendientes_de_sincronizar()
    if not pendientes and not eliminar:
        return

    payload = []
    for zona in pendientes:
        entrada = {campo: zona[campo] for campo in _CAMPOS_ZONA}
        entrada["cliente_id"] = str(zona["id"])
        entrada["cloud_id"] = zona["cloud_id"]
        entrada["camara"] = zona["camara_id"]
        payload.append(entrada)

    respuesta = cliente_api.sincronizar_zonas(payload, eliminar=eliminar)

    for asignado in respuesta.get("ids", []):
        almacenamiento.marcar_zona_sincronizada(int(asignado["cliente_id"]), asignado["cloud_id"])
    # confirmar_eliminacion_zona espera el id LOCAL, no el cloud_id — se
    # vuelve a consultar la lista de pendientes para tener ambos.
    for zona in almacenamiento.zonas_pendientes_de_eliminar():
        if zona["cloud_id"] in eliminar:
            almacenamiento.confirmar_eliminacion_zona(zona["id"])
    for error in respuesta.get("errores", []):
        logger.warning("No se pudo sincronizar la zona local %s: %s", error.get("cliente_id"), error.get("detail"))


def _sincronizar_reglas(almacenamiento, cliente_api):
    eliminar = [r["cloud_id"] for r in almacenamiento.reglas_pendientes_de_eliminar()]
    pendientes = almacenamiento.reglas_pendientes_de_sincronizar()
    if not pendientes and not eliminar:
        return

    payload = []
    for regla in pendientes:
        zona = almacenamiento.obtener_zona(regla["zona_id"])
        if zona is None or zona["cloud_id"] is None:
            # La zona todavía no se sincronizó (falló su push, o es muy
            # reciente) — se reintenta en el próximo ciclo, junto con la zona.
            continue
        entrada = {campo: regla[campo] for campo in _CAMPOS_REGLA}
        entrada["cliente_id"] = str(regla["id"])
        entrada["cloud_id"] = regla["cloud_id"]
        entrada["zona"] = zona["cloud_id"]
        payload.append(entrada)

    if not payload and not eliminar:
        return

    respuesta = cliente_api.sincronizar_reglas(payload, eliminar=eliminar)

    for asignado in respuesta.get("ids", []):
        almacenamiento.marcar_regla_sincronizada(int(asignado["cliente_id"]), asignado["cloud_id"])
    for regla in almacenamiento.reglas_pendientes_de_eliminar():
        if regla["cloud_id"] in eliminar:
            almacenamiento.confirmar_eliminacion_regla(regla["id"])
    for error in respuesta.get("errores", []):
        logger.warning("No se pudo sincronizar la regla local %s: %s", error.get("cliente_id"), error.get("detail"))


def importar_configuracion_desde_cloud(almacenamiento, camara_id, zonas_cloud):
    """Migración de arranque: si el equipo local todavía no tiene ninguna
    zona configurada para `camara_id`, importa las que ya existían en el
    dashboard (zonas_cloud, tal como las devuelve obtener_reglas_activas)
    para no perder la configuración previa. No hace nada si ya hay algo
    configurado localmente — la próxima edición local es la que manda."""
    if almacenamiento.tiene_zonas(camara_id):
        return
    for zona in zonas_cloud:
        zona_id = almacenamiento.importar_zona_desde_cloud(
            camara_id,
            cloud_id=zona["id"],
            nombre=zona["nombre"],
            tipo=zona.get("tipo", "poligono"),
            poligono=zona.get("poligono"),
            centro_x=zona.get("centro_x"),
            centro_y=zona.get("centro_y"),
            radio_metros=zona.get("radio_metros"),
            activa=True,
        )
        for regla in zona.get("reglas", []):
            almacenamiento.importar_regla_desde_cloud(
                zona_id,
                cloud_id=regla["id"],
                hora_inicio=regla["hora_inicio"],
                hora_fin=regla["hora_fin"],
                dias_semana=regla.get("dias_semana", []),
                canal_notificacion=regla.get("canal_notificacion", "whatsapp"),
                destinatario=regla.get("destinatario", ""),
                nombre=regla.get("nombre", ""),
                activa=True,
            )
