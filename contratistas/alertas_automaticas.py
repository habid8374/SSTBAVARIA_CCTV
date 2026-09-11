"""Motor de alertas automáticas sobre una Declaración de Método.

Regla dura: esto NUNCA decide por sí solo. Solo genera advertencias
informativas — cada una con un motivo de rechazo sugerido — para que el
personal de SST/interventoría las tenga en cuenta al revisar. No cambia el
estado de la declaración, no bloquea aprobar/rechazar, y el texto sugerido
es solo un punto de partida que el revisor edita o descarta libremente.

Las reglas están basadas en los SOP "Safety to Sustain" (trabajos en
altura, excavaciones, sistemas anticaída) que compartió el cliente.

Fase A usa solo datos que el formulario ya capturaba (permisos, EPP,
riesgo, firmas, tarea SIF). Fase B suma los umbrales numéricos exactos de
las SOP a partir de dos campos opcionales por actividad —
altura_trabajo_metros y profundidad_excavacion_metros — que solo disparan
alertas cuando el contratista los diligencia; si quedan vacíos, esas
reglas simplemente no aplican (no se asume nada en su ausencia)."""

import re

from .models import nivel_riesgo

PERMISO_ALTURA = "Certificado de apoyo en alturas / protección contra caídas"
PERMISO_EXCAVACION = "Excavaciones o Demolición"
EPP_CONTRA_CAIDAS = "Otros: Equipo contra caídas (Arnés de seguridad, línea retráctil, doble gancho)"

# Palabras que por sí solas ya implican trabajo en altura sin ambigüedad
# razonable (a diferencia de "altura", "andamio" o "escalera" sueltas — ver
# abajo, se quitaron de esta lista porque en Excel reales del cliente
# aparecían en frases sin relación real con trabajo en altura: "acceso por
# escaleras" de oficina, "andamio movil" usado a la altura de los hombros,
# "nivelaran la altura y la luz" de un ajuste de instalación).
PALABRAS_CLAVE_ALTURA = ["techo", "cubierta", "plataforma elevad"]

# La palabra "altura" sola es demasiado ambigua (nivelar la altura de algo,
# la altura de los hombros, etc.) — solo cuenta como señal real de trabajo
# en altura cuando aparece en una de estas frases: "trabajo(s) en altura",
# "altura de <número>" (ej. "altura de 120 mt") o "<número> m/mt/metros de
# altura" (ej. "3 metros de altura").
_PATRON_ALTURA_CON_CONTEXTO = re.compile(
    r"trabajos?\s+en\s+altura"
    r"|altura\s+de\s+\d"
    r"|\d[\d.,]*\s*(?:m|mts?|metros)\s+de\s+altura"
)


def _texto_sugiere_trabajo_en_altura(texto):
    if any(palabra in texto for palabra in PALABRAS_CLAVE_ALTURA):
        return True
    return bool(_PATRON_ALTURA_CON_CONTEXTO.search(texto))


def _alerta(codigo, actividad, titulo, mensaje, motivo_sugerido, fuente):
    return {
        "codigo": codigo,
        "actividad_id": actividad.id,
        "actividad_orden": actividad.orden,
        "titulo": titulo,
        "mensaje": mensaje,
        "motivo_sugerido": motivo_sugerido,
        "fuente": fuente,
    }


def _deduplicar(alertas):
    """Una 'Secuencia de Actividades' del Excel real del cliente suele traer
    varias filas de riesgo (una por cada peligro de su matriz Kinney) — al
    importar, cada fila queda como una ActividadMetodo aparte pero
    comparte secuencia/técnicas/permisos con sus filas hermanas, así que
    una misma condición puede generar la misma alerta una vez por fila en
    vez de una vez por tarea real. Se conserva solo la primera aparición
    de cada (código, mensaje)."""
    vistos = set()
    resultado = []
    for alerta in alertas:
        clave = (alerta["codigo"], alerta["mensaje"])
        if clave in vistos:
            continue
        vistos.add(clave)
        resultado.append(alerta)
    return resultado


def generar_alertas(declaracion):
    """Devuelve una lista de alertas (dict) para las actividades de la
    declaración dada. Es de solo lectura — no modifica nada."""
    alertas = []

    for actividad in declaracion.actividades.all():
        permisos = actividad.permisos_requeridos or []
        epp = actividad.epp_requerido or []
        etiqueta = actividad.secuencia[:80] if actividad.secuencia else f"actividad #{actividad.orden + 1}"
        altura = actividad.altura_trabajo_metros
        profundidad = actividad.profundidad_excavacion_metros

        if PERMISO_ALTURA in permisos and EPP_CONTRA_CAIDAS not in epp:
            alertas.append(
                _alerta(
                    "altura_sin_epp_caida",
                    actividad,
                    "Trabajo en altura sin EPP contra caídas marcado",
                    f'La actividad «{etiqueta}» exige el permiso "{PERMISO_ALTURA}" '
                    "pero no tiene marcado el EPP contra caídas.",
                    "Falta marcar el equipo de protección contra caídas (arnés, línea "
                    "retráctil, doble gancho) en una actividad que requiere trabajo en "
                    "altura mayor a 1.8 m.",
                    "SOP.MAZ.SAFE.1.9 Trabajos en Alturas / Requisitos Sistemas Anticaída",
                )
            )

        if PERMISO_EXCAVACION in permisos and len((actividad.medidas_mitigacion or "").strip()) < 20:
            alertas.append(
                _alerta(
                    "excavacion_sin_medidas",
                    actividad,
                    "Excavación sin medidas de mitigación detalladas",
                    f'La actividad «{etiqueta}» exige el permiso "{PERMISO_EXCAVACION}" '
                    "pero las medidas de mitigación están vacías o son muy breves.",
                    "Las medidas de mitigación para la excavación no detallan aspectos "
                    "exigidos por el SOP de excavaciones (salida de emergencia, "
                    "señalización del perímetro, distancia de acopio de material, retén "
                    "exterior).",
                    "SOP.MAZ.SAFE.1.9.12 Requisitos de Seguridad Excavaciones",
                )
            )

        nivel_con, _ = nivel_riesgo(actividad.riesgo_con)
        if nivel_con in ("alto", "muy_alto"):
            alertas.append(
                _alerta(
                    "riesgo_alto_con_mitigacion",
                    actividad,
                    "Riesgo sigue alto después de mitigar",
                    f"La actividad «{etiqueta}» tiene un riesgo de {actividad.riesgo_con} "
                    "incluso con las medidas de mitigación aplicadas.",
                    "El riesgo con mitigación aplicada sigue en banda alta — revisar si "
                    "las medidas descritas son suficientes o si falta información.",
                    "Método Kinney (evaluación de riesgo)",
                )
            )

        texto = " ".join(
            [actividad.secuencia or "", actividad.tecnicas_herramientas or "", actividad.descripcion_riesgo or ""]
        ).lower()
        if PERMISO_ALTURA not in permisos and _texto_sugiere_trabajo_en_altura(texto):
            alertas.append(
                _alerta(
                    "texto_sugiere_altura_sin_permiso",
                    actividad,
                    "El texto sugiere trabajo en altura sin el permiso marcado",
                    f"La actividad «{etiqueta}» menciona palabras relacionadas con trabajo "
                    f'en altura, pero no tiene marcado el permiso "{PERMISO_ALTURA}".',
                    "Verificar si la actividad realmente implica trabajo en altura y, de "
                    "ser así, marcar el permiso correspondiente.",
                    "Heurística de texto — confirmar manualmente antes de usar como motivo de rechazo",
                )
            )

        if altura is not None and altura > 1.8 and PERMISO_ALTURA not in permisos:
            alertas.append(
                _alerta(
                    "altura_sobre_1_8m_sin_permiso",
                    actividad,
                    "Altura declarada supera 1.8 m sin el permiso marcado",
                    f"La actividad «{etiqueta}» declara una altura de trabajo de {altura} m "
                    f'(mayor a 1.8 m) pero no tiene marcado el permiso "{PERMISO_ALTURA}".',
                    "El SOP de trabajos en altura exige permiso de trabajo a partir de 1.8 m "
                    "— falta marcarlo dado el valor de altura declarado.",
                    "SOP.MAZ.SAFE.1.9 Trabajos en Alturas — Definiciones",
                )
            )

        if altura is not None and altura > 4:
            alertas.append(
                _alerta(
                    "altura_sobre_4m_requiere_zbs",
                    actividad,
                    "Altura mayor a 4 m — exige aprobación ZBS",
                    f"La actividad «{etiqueta}» declara una altura de trabajo de {altura} m "
                    "(mayor a 4 m).",
                    "Trabajo en techo/pipe rack por encima de 4 m exige revisión y "
                    "aprobación previa de Zone Safety (ZBS) del plan de seguridad y la "
                    "declaración de método, además de redes de seguridad certificadas o "
                    "plataformas/andamios certificados — confirmar que ese proceso ya se hizo.",
                    "SOP.MAZ.SAFE.1.9 Trabajos en Alturas §8.2.4-8.5.2 / SOP Redes de Seguridad",
                )
            )

        if profundidad is not None and profundidad > 1.2:
            alertas.append(
                _alerta(
                    "excavacion_sobre_1_2m_salida_emergencia",
                    actividad,
                    "Excavación mayor a 1.2 m — exige salida de emergencia",
                    f"La actividad «{etiqueta}» declara una profundidad de excavación de "
                    f"{profundidad} m (mayor a 1.2 m).",
                    "El SOP de excavaciones exige una salida de emergencia (rampa o "
                    "escalera) a máximo 7 m de cualquier trabajador dentro de la "
                    "excavación — confirmar que está contemplada.",
                    "SOP.MAZ.SAFE.1.9.12 Requisitos de Seguridad Excavaciones",
                )
            )

        if profundidad is not None and profundidad > 1.3:
            alertas.append(
                _alerta(
                    "excavacion_sobre_1_3m_reten_exterior",
                    actividad,
                    "Excavación mayor a 1.3 m — exige retén exterior",
                    f"La actividad «{etiqueta}» declara una profundidad de excavación de "
                    f"{profundidad} m (mayor a 1.3 m).",
                    "El SOP de excavaciones exige un retén (vigía) exterior dedicado "
                    "mientras haya trabajadores dentro de la excavación — confirmar que "
                    "está asignado.",
                    "SOP.MAZ.SAFE.1.9.12 Requisitos de Seguridad Excavaciones",
                )
            )

        if profundidad is not None and profundidad > 5:
            alertas.append(
                _alerta(
                    "excavacion_sobre_5m_requiere_andamio",
                    actividad,
                    "Excavación mayor a 5 m — exige andamiaje",
                    f"La actividad «{etiqueta}» declara una profundidad de excavación de "
                    f"{profundidad} m (mayor a 5 m).",
                    "El SOP de excavaciones exige andamiaje para excavaciones de más de "
                    "5 m de profundidad — confirmar que está contemplado en la "
                    "declaración.",
                    "SOP.MAZ.SAFE.1.9 Trabajos en Alturas §8.6 (excavaciones)",
                )
            )

    return _deduplicar(alertas)
