"""Motor de alertas automáticas sobre una Declaración de Método.

Regla dura: esto NUNCA decide por sí solo. Solo genera advertencias
informativas — cada una con un motivo de rechazo sugerido — para que el
personal de SST/interventoría las tenga en cuenta al revisar. No cambia el
estado de la declaración, no bloquea aprobar/rechazar, y el texto sugerido
es solo un punto de partida que el revisor edita o descarta libremente.

Las reglas están basadas en los SOP "Safety to Sustain" (trabajos en
altura, excavaciones, sistemas anticaída) que compartió el cliente, y usan
únicamente datos que el formulario ya captura hoy — sin campos nuevos."""

from .models import nivel_riesgo

PERMISO_ALTURA = "Trabajos en Altura > 1.8 m"
PERMISO_EXCAVACION = "Excavaciones o Demolición"
EPP_CONTRA_CAIDAS = "Otros: Equipo contra caídas (Arnés de seguridad, línea retráctil, doble gancho)"
ROL_SEGURIDAD_PLANTA = "seguridad_planta"

PALABRAS_CLAVE_ALTURA = ["altura", "techo", "cubierta", "andamio", "plataforma elevad", "escalera"]


def _firmas_seguridad_planta_vigentes(declaracion):
    return [
        f
        for f in declaracion.firmas.all()
        if f.rol == ROL_SEGURIDAD_PLANTA and not f.documento_modificado_despues_de_firmar
    ]


def generar_alertas(declaracion):
    """Devuelve una lista de alertas (dict) para las actividades de la
    declaración dada. Es de solo lectura — no modifica nada."""
    alertas = []
    firmas_seguridad_vigentes = _firmas_seguridad_planta_vigentes(declaracion)

    for actividad in declaracion.actividades.all():
        permisos = actividad.permisos_requeridos or []
        epp = actividad.epp_requerido or []
        etiqueta = actividad.secuencia[:80] if actividad.secuencia else f"actividad #{actividad.orden + 1}"

        if PERMISO_ALTURA in permisos and EPP_CONTRA_CAIDAS not in epp:
            alertas.append(
                {
                    "codigo": "altura_sin_epp_caida",
                    "actividad_id": actividad.id,
                    "actividad_orden": actividad.orden,
                    "titulo": "Trabajo en altura sin EPP contra caídas marcado",
                    "mensaje": (
                        f'La actividad «{etiqueta}» exige el permiso "{PERMISO_ALTURA}" '
                        "pero no tiene marcado el EPP contra caídas."
                    ),
                    "motivo_sugerido": (
                        "Falta marcar el equipo de protección contra caídas (arnés, línea "
                        "retráctil, doble gancho) en una actividad que requiere trabajo en "
                        "altura mayor a 1.8 m."
                    ),
                    "fuente": "SOP.MAZ.SAFE.1.9 Trabajos en Alturas / Requisitos Sistemas Anticaída",
                }
            )

        if PERMISO_EXCAVACION in permisos and len((actividad.medidas_mitigacion or "").strip()) < 20:
            alertas.append(
                {
                    "codigo": "excavacion_sin_medidas",
                    "actividad_id": actividad.id,
                    "actividad_orden": actividad.orden,
                    "titulo": "Excavación sin medidas de mitigación detalladas",
                    "mensaje": (
                        f'La actividad «{etiqueta}» exige el permiso "{PERMISO_EXCAVACION}" '
                        "pero las medidas de mitigación están vacías o son muy breves."
                    ),
                    "motivo_sugerido": (
                        "Las medidas de mitigación para la excavación no detallan aspectos "
                        "exigidos por el SOP de excavaciones (salida de emergencia, "
                        "señalización del perímetro, distancia de acopio de material, retén "
                        "exterior)."
                    ),
                    "fuente": "SOP.MAZ.SAFE.1.9.12 Requisitos de Seguridad Excavaciones",
                }
            )

        nivel_con, _ = nivel_riesgo(actividad.riesgo_con)
        if nivel_con in ("alto", "muy_alto"):
            alertas.append(
                {
                    "codigo": "riesgo_alto_con_mitigacion",
                    "actividad_id": actividad.id,
                    "actividad_orden": actividad.orden,
                    "titulo": "Riesgo sigue alto después de mitigar",
                    "mensaje": (
                        f"La actividad «{etiqueta}» tiene un riesgo de {actividad.riesgo_con} "
                        "incluso con las medidas de mitigación aplicadas."
                    ),
                    "motivo_sugerido": (
                        "El riesgo con mitigación aplicada sigue en banda alta — revisar si "
                        "las medidas descritas son suficientes o si falta información."
                    ),
                    "fuente": "Método Kinney (evaluación de riesgo)",
                }
            )

        if actividad.tarea_sif and not firmas_seguridad_vigentes:
            alertas.append(
                {
                    "codigo": "sif_sin_firma_seguridad",
                    "actividad_id": actividad.id,
                    "actividad_orden": actividad.orden,
                    "titulo": "Tarea SIF sin firma de Seguridad de Planta",
                    "mensaje": (
                        f"La actividad «{etiqueta}» está marcada como tarea SIF (potencial de "
                        "lesión seria o fatal) pero la declaración no tiene una firma vigente "
                        "de Seguridad de Planta (Site)."
                    ),
                    "motivo_sugerido": (
                        "Falta la firma de Seguridad de Planta (Site) exigida para una tarea "
                        "con potencial de lesión seria o fatal."
                    ),
                    "fuente": "Buenas prácticas internas — tareas SIF",
                }
            )

        texto = " ".join(
            [actividad.secuencia or "", actividad.tecnicas_herramientas or "", actividad.descripcion_riesgo or ""]
        ).lower()
        if PERMISO_ALTURA not in permisos and any(palabra in texto for palabra in PALABRAS_CLAVE_ALTURA):
            alertas.append(
                {
                    "codigo": "texto_sugiere_altura_sin_permiso",
                    "actividad_id": actividad.id,
                    "actividad_orden": actividad.orden,
                    "titulo": "El texto sugiere trabajo en altura sin el permiso marcado",
                    "mensaje": (
                        f"La actividad «{etiqueta}» menciona palabras relacionadas con trabajo "
                        f'en altura, pero no tiene marcado el permiso "{PERMISO_ALTURA}".'
                    ),
                    "motivo_sugerido": (
                        "Verificar si la actividad realmente implica trabajo en altura y, de "
                        "ser así, marcar el permiso correspondiente."
                    ),
                    "fuente": "Heurística de texto — confirmar manualmente antes de usar como motivo de rechazo",
                }
            )

    return alertas
