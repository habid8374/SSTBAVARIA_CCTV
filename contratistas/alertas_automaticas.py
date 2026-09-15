"""Motor de alertas automáticas sobre una Declaración de Método.

Regla dura: esto NUNCA decide por sí solo. Solo genera advertencias
informativas — cada una con un motivo de rechazo sugerido — para que el
personal de SST/interventoría las tenga en cuenta al revisar. No cambia el
estado de la declaración, no bloquea aprobar/rechazar, y el texto sugerido
es solo un punto de partida que el revisor edita o descarta libremente.

Las reglas están basadas en los SOP "Safety to Sustain" (trabajos en
altura, excavaciones, sistemas anticaída, ergonomía, seguridad vial,
procesos de alto riesgo) que compartió el cliente, más las categorías de
peligro del Anexo A de la GTC 45 (guía técnica colombiana de
identificación de peligros y valoración de riesgos) — ver
CATEGORIAS_PELIGRO_TEXTO más abajo para el detalle de cada una. Cada
categoría y cada regla numérica incluyen un campo
"medida_control_sugerida" con una medida de control concreta extraída del
SOP correspondiente (no genérica) que el frontend muestra junto a la
alerta — es solo un punto de partida, el revisor la edita o descarta
libremente igual que el resto de la alerta.

Fase A usa solo datos que el formulario ya capturaba (permisos, EPP,
riesgo, firmas, tarea SIF). Fase B suma los umbrales numéricos exactos de
las SOP a partir de dos campos opcionales por actividad —
altura_trabajo_metros y profundidad_excavacion_metros — que solo disparan
alertas cuando el contratista los diligencia; si quedan vacíos, esas
reglas simplemente no aplican (no se asume nada en su ausencia)."""

import re
import unicodedata

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


def _sin_acentos(texto):
    """minúsculas sin acentos — para que las palabras clave de abajo no
    necesiten repetirse con y sin tilde (ej. "electrocucion" atrapa tanto
    "electrocución" como "electrocucion")."""
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


# Catálogo de categorías de peligro que se detectan por texto libre contra
# el catálogo de permisos ZBS — basado en las categorías de peligro del
# Anexo A de la GTC 45 (guía técnica colombiana de identificación de
# peligros y valoración de riesgos) que el cliente pidió cruzar contra las
# declaraciones. Cada entrada funciona igual que la heurística de "trabajo
# en altura" ya existente: si el texto de la actividad menciona palabras de
# esa categoría pero el permiso correspondiente no está marcado, se sugiere
# revisar — nunca decide por sí sola (ver docstring del módulo).
CATEGORIAS_PELIGRO_TEXTO = [
    {
        "codigo": "altura",
        "descripcion_corta": "trabajo en altura",
        "permiso": PERMISO_ALTURA,
        "palabras_clave": PALABRAS_CLAVE_ALTURA,
        "patron_contexto": _PATRON_ALTURA_CON_CONTEXTO,
        "fuente": "SOP.MAZ.SAFE.1.9 Trabajos en Alturas — heurística de texto, confirmar manualmente",
        "medida_control_sugerida": (
            "Arnés de cuerpo completo con doble cabo de vida conectado a un punto de anclaje "
            "certificado; sistema 100% amarrado. Inspección del sistema anticaída componente "
            "por componente antes de cada uso, con precinto seriado de inspección vigente."
        ),
    },
    {
        "codigo": "electrico",
        "descripcion_corta": "riesgo eléctrico",
        "permiso": "Certificado de apoyo en trabajo eléctrico",
        "palabras_clave": [
            "electrocucion", "choque electrico", "contacto electrico", "riesgo electrico",
            "sistema electrico vivo", "subestacion electrica", "alta tension", "energia electrica",
        ],
        "fuente": "GTC 45 — Anexo A, peligro físico: Eléctrico (alta y baja tensión, estática)",
        "medida_control_sugerida": (
            "Desenergizar, bloquear y etiquetar (LOTO) antes de intervenir; verificar ausencia "
            "de tensión con equipo de medición calibrado. Si no es posible desenergizar, permiso "
            "de trabajo eléctrico específico y EPP dieléctrico según el nivel de tensión."
        ),
    },
    {
        "codigo": "espacio_confinado",
        "descripcion_corta": "trabajo en espacio confinado",
        "permiso": "Certificado de apoyo en espacios confinados",
        "palabras_clave": ["espacio confinado", "espacios confinados"],
        "fuente": "GTC 45 — Anexo A, condiciones de seguridad: Espacios confinados",
        "medida_control_sugerida": (
            "Medir la atmósfera antes de ingresar (O2 entre 19.5% y 23.5%, sin gases inflamables "
            "ni tóxicos) y mantener monitoreo continuo. Bloqueo de todas las fuentes de energía, "
            "vigía permanente en el exterior y plan de rescate practicado con rescatista "
            "certificado disponible."
        ),
    },
    {
        "codigo": "sustancias_peligrosas",
        "descripcion_corta": "manejo de sustancias peligrosas",
        "permiso": "Certificado de apoyo en manejo de sustancias peligrosas",
        "palabras_clave": [
            "sustancia peligrosa", "sustancias peligrosas", "material peligroso", "materiales peligrosos",
            "derrame de sustancia", "derrame de quimico", "producto quimico peligroso",
        ],
        "fuente": "GTC 45 — Anexo A, peligro químico",
        "medida_control_sugerida": (
            "Consultar la hoja de seguridad (MSDS) de la sustancia antes de manipularla, EPP "
            "químico específico (guantes, careta, protección respiratoria según corresponda) y "
            "kit de control de derrames disponible en el sitio de trabajo."
        ),
    },
    {
        "codigo": "loto_bloqueo",
        "descripcion_corta": "bloqueo y etiquetado de energías",
        "permiso": "Certificado de apoyo LOTO / bloqueo y etiquetado de energías",
        "palabras_clave": [
            "bloqueo y etiquetado", "bloqueo de energia", "bloqueo de energias",
            "candado y tarjeta", "desenergizar", "energia residual",
        ],
        "fuente": "GTC 45 — Anexo A, condiciones de seguridad: bloqueo de energías (LOTO)",
        "medida_control_sugerida": (
            "Identificar todas las fuentes de energía del equipo (eléctrica, neumática, "
            "hidráulica, mecánica residual), aislarlas con candado y tarjeta personal de cada "
            "trabajador, y verificar energía cero antes de intervenir."
        ),
    },
    {
        "codigo": "trabajo_caliente",
        "descripcion_corta": "trabajo en caliente",
        "permiso": "Trabajos en Caliente",
        "palabras_clave": [
            "soldadura", "esmerilado", "oxicorte", "corte con llama", "trabajo en caliente", "trabajos en caliente",
        ],
        "fuente": "GTC 45 — Anexo A, peligro físico/tecnológico: trabajos en caliente",
        "medida_control_sugerida": (
            "Retirar o proteger materiales combustibles en un radio mínimo de seguridad, vigía "
            "de fuego con extintor disponible durante y después de la actividad, y verificación "
            "de atmósfera libre de gases inflamables si aplica."
        ),
    },
    {
        "codigo": "izaje",
        "descripcion_corta": "izaje de cargas",
        "permiso": "Izaje (grúa, tecle, polipasto, montacargas, poleas)",
        "palabras_clave": [
            "izaje", "grua", "tecle", "polipasto", "montacargas", "elevador de motores", "izador de motores",
        ],
        "fuente": "GTC 45 — Anexo A, condiciones de seguridad: mecánico (izaje de cargas)",
        "medida_control_sugerida": (
            "Plan de izaje sin exceder el 85% de la capacidad de la grúa/equipo, supervisor de "
            "izaje dedicado, segregar el radio de giro/boom (nadie debajo de la carga) y "
            "certificación vigente de grúa, aparejos y operador."
        ),
    },
    {
        "codigo": "manejo_manual_cargas",
        "descripcion_corta": "manejo manual de cargas / riesgo biomecánico",
        "permiso": "Manejo de materiales y ergonomía",
        "palabras_clave": [
            "levantamiento de carga", "levantamiento manual", "manejo manual de cargas",
            "manejo manual de materiales", "sobreesfuerzo", "postura forzada", "movimiento repetitivo",
            "movimientos repetitivos",
        ],
        "fuente": "GTC 45 — Anexo A, peligro biomecánico / VPO.SAFE.1.4 Manejo de Materiales y Ergonomía",
        "medida_control_sugerida": (
            "Usar ayudas mecánicas (grúas, carretillas, polipastos, mesas de altura ajustable) "
            "en vez de levantamiento manual cuando el peso supere 25 kg; para cargas menores, "
            "aplicar técnica correcta de levantamiento y evitar giros de tronco con la carga."
        ),
    },
    {
        "codigo": "seguridad_vial",
        "descripcion_corta": "conducción de vehículos / seguridad vial",
        "permiso": "Certificado de apoyo en seguridad vial y conducción",
        "palabras_clave": [
            "conducir vehiculo", "conduccion de vehiculo", "manejo de vehiculo", "operar vehiculo",
            "transito vehicular", "manejo defensivo",
        ],
        "fuente": "GTC 45 — Anexo A, condiciones de seguridad: tránsito / SAFE 1.8 Seguridad Vial y al Conducir",
        "medida_control_sugerida": (
            "Verificar que el conductor tenga licencia vigente para la categoría del vehículo y "
            "haya aprobado la inspección preoperacional del vehículo antes de circular dentro de "
            "las instalaciones."
        ),
    },
    {
        "codigo": "procesos_alto_riesgo",
        "descripcion_corta": "proceso de alto riesgo (amoniaco, presión, explosión)",
        "permiso": "Certificado de apoyo en procesos de alto riesgo",
        "palabras_clave": [
            "amoniaco", "recipiente a presion", "caldero", "vapor sobrecalentado", "nitrogeno liquido",
            "explosion por polvo", "explosion por gas",
        ],
        "fuente": "GTC 45 — Anexo A, peligro físico/tecnológico / VPO.SAFE.1.2 Gestión de Procesos de Alto Riesgo",
        "medida_control_sugerida": (
            "Verificar la evaluación de riesgos específica del proceso (amoniaco, recipientes a "
            "presión, calderos, N2/CO2 u otro) y que los equipos de detección/control asociados "
            "estén operativos antes de intervenir."
        ),
    },
]


def _texto_sugiere_categoria(texto, categoria):
    if any(palabra in texto for palabra in categoria["palabras_clave"]):
        return True
    patron = categoria.get("patron_contexto")
    return bool(patron and patron.search(texto))


def _alerta_categoria_texto(actividad, etiqueta, categoria):
    descripcion = categoria["descripcion_corta"]
    return _alerta(
        f"texto_sugiere_{categoria['codigo']}_sin_permiso",
        actividad,
        f"El texto sugiere {descripcion} sin el permiso marcado",
        f"La actividad «{etiqueta}» menciona palabras relacionadas con {descripcion}, pero no "
        f'tiene marcado el permiso "{categoria["permiso"]}".',
        f"Verificar si la actividad realmente implica {descripcion} y, de ser así, marcar el "
        "permiso correspondiente.",
        categoria["fuente"],
        categoria.get("medida_control_sugerida", ""),
    )


def _alerta(codigo, actividad, titulo, mensaje, motivo_sugerido, fuente, medida_control_sugerida=""):
    return {
        "codigo": codigo,
        "actividad_id": actividad.id,
        "actividad_orden": actividad.orden,
        "titulo": titulo,
        "mensaje": mensaje,
        "motivo_sugerido": motivo_sugerido,
        "fuente": fuente,
        "medida_control_sugerida": medida_control_sugerida,
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
                    "Arnés industrial de cuerpo completo, con el elemento de enganche dorsal "
                    "por encima del centro de gravedad, conectado a un punto de anclaje fijo "
                    "mediante línea de vida con absorbedor de energía.",
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
                    "Salida de emergencia a máximo 7 m de cualquier trabajador, señalización "
                    "y barrera física del perímetro, material excavado acopiado a más de 60 "
                    "cm del borde, y retén (vigía) exterior dedicado.",
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
                    "Priorizar controles más altos en la jerarquía (eliminación, sustitución, "
                    "controles de ingeniería) antes de depender solo de EPP o procedimientos; "
                    "si el riesgo residual sigue alto, la actividad debería detenerse hasta "
                    "reforzar los controles.",
                )
            )

        texto = _sin_acentos(
            " ".join(
                [actividad.secuencia or "", actividad.tecnicas_herramientas or "", actividad.descripcion_riesgo or ""]
            ).lower()
        )
        for categoria in CATEGORIAS_PELIGRO_TEXTO:
            if categoria["permiso"] in permisos:
                continue
            if not _texto_sugiere_categoria(texto, categoria):
                continue
            alertas.append(_alerta_categoria_texto(actividad, etiqueta, categoria))

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
                    "Marcar el permiso de alturas y verificar sistema anticaída completo "
                    "(arnés, línea de vida, punto de anclaje certificado) antes de iniciar.",
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
                    "Aprobación previa de ZBS del plan de seguridad, redes de seguridad "
                    "certificadas o plataforma/andamio certificado (no usar únicamente el "
                    "sistema anticaída personal como control principal por encima de 4 m).",
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
                    "Rampa o escalera de salida de emergencia a no más de 7 m de cualquier "
                    "punto dentro de la excavación.",
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
                    "Asignar un retén (vigía) exterior dedicado, sin otras tareas, durante "
                    "todo el tiempo que haya personal dentro de la excavación.",
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
                    "Instalar andamiaje o entibado certificado antes de que el personal "
                    "ingrese a una excavación de más de 5 m de profundidad.",
                )
            )

    return _deduplicar(alertas)
