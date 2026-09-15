"""Carga masiva de Trabajador desde un Excel — replica, columna por columna
en lo posible, la hoja real "TABLA INGRESOS" que ya maneja el cliente: cada
fila es un trabajador y una columna "Contratista (empresa)" (desplegable)
indica a qué EmpresaContratista pertenece esa fila, para poder mezclar
personal de varias empresas contratistas en un mismo archivo.

Igual que en la hoja del cliente, cada certificación con fecha de
vencimiento (examen médico, alturas, y cada certificación especial) trae
ADEMÁS una columna de estado "Certificado validado (OutSafety/Drive/NA/No
validado)" inmediatamente antes de su columna de fecha — ese desplegable es
de donde sale el "N/A" real (cuando esa certificación no aplica a ese
trabajador), no de escribir texto libre en la celda de fecha. Si el estado
es "NA", la fecha de esa fila para esa certificación se ignora aunque haya
algo escrito — igual que la fórmula `IF(cert="NA","NA",...)` del Excel
original. El estado en sí (OutSafety/Drive/NA/No validado) es solo
informativo dentro del Excel — no se guarda en la base, porque nada en el
sistema depende de DÓNDE se validó un certificado, solo de si aplica y
cuándo vence.

A diferencia del importador de Declaración de Método (que solo
precarga un formulario), este SÍ crea registros en la base — una fila
por Trabajador válido — reutilizando TrabajadorSerializer y sus mismas
reglas que la creación manual desde el formulario (autorización de
datos obligatoria, documento único por contratista, etc.): una fila
que no pasaría el formulario normal tampoco se crea acá, queda
reportada como error de esa fila sin tumbar el resto del archivo.

Todas las columnas de fecha llevan validación de tipo fecha (el pequeño
calendario junto a la celda, en vez de tener que escribir el texto a
mano) — evita el error más común al llenar el Excel: la fecha en el
formato equivocado.

Campos que en el Excel del cliente viven a nivel de EMPRESA contratista
(tipo de contratista, contrato marco, NIT, responsable SST/SISO de la
contratista) NO se repiten por fila acá — ya se editan una sola vez en
Sistema → Contratistas y se leen del Contratista elegido en cada fila, en
vez de duplicarse. Tampoco se replica la planilla de seguridad social
(número, fecha de reporte, fecha de vencimiento, ARL vigente) — esa
información vive en RadicacionSeguridadSocial, un modelo/flujo aparte con
su propia pantalla, y la carga masiva de trabajadores nunca crea
radicaciones (ver más abajo).

La radicación de seguridad social nunca se crea desde acá — cada
trabajador importado queda igual que si se hubiera registrado a mano:
sin radicaciones, pendiente de que el contratista o SST la cargue
después (ver RadicacionSeguridadSocial, un modelo aparte)."""

import datetime
import unicodedata

import openpyxl
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import PatternFill, Protection
from openpyxl.utils import get_column_letter
from openpyxl.workbook.protection import WorkbookProtection
from openpyxl.worksheet.datavalidation import DataValidation

from .models import CertificacionEspecial, CursoSafetyAcademy, EmpresaContratista, Trabajador


class ErrorImportacionExcel(Exception):
    """Mensaje pensado para mostrarse tal cual al usuario."""


HOJA_TRABAJADORES = "Trabajadores"
HOJA_LISTAS = "Listas (no borrar)"

# Protege la hoja/libro contra ediciones accidentales de las fórmulas de
# validación y contra desocultar "Listas (no borrar)" — no es una medida de
# seguridad real (la protección de Excel se quita sin la contraseña con
# herramientas de terceros), solo evita que alguien la rompa sin querer.
CONTRASENA_PLANTILLA = "SSTBavaria2026"

ESTADO_VALIDACION_OPCIONES = "OutSafety,Drive,NA,No validado"

# Encabezado de la columna de estado que antecede a cada columna de
# vencimiento — se arma con f"{titulo} — certificado validado ..." para que
# quede clarísimo a cuál columna de fecha corresponde.
_SUFIJO_ESTADO = " — certificado validado (OutSafety/Drive/NA/No validado)"
_SUFIJO_FECHA = " — vencimiento (AAAA-MM-DD)"

# Mismo orden que la hoja "TABLA INGRESOS" del Excel real del cliente para
# las columnas iniciales, hasta antes de examen médico/alturas — las
# columnas de curso/certificación especial se agregan después,
# dinámicamente, según el catálogo vigente.
ENCABEZADOS_BASE = [
    "Fecha de revisión y validación (AAAA-MM-DD)",
    "Validación (Ingreso/Renovación)",
    "Contratista (empresa)",
    "Nombres",
    "Apellidos",
    "Documento",
    "Autorización datos (SI/NO)",
    "EPS",
    "ARL",
    "AFP",
    "Tipo de vinculación (Fijo/Temporal)",
    "Fecha inicio contrato (AAAA-MM-DD)",
    "Número de pedido o CM",
    "¿Actualmente es casco rojo? (SI/NO)",
    "Clase de riesgo (I/II/III/IV/V)",
    "Área donde realiza sus actividades",
    "Formato de inclusión firmado por todos los responsables (SI/NO)",
    "Registros de entrega de EPP y dotación (SI/NO)",
    "Pago de seguridad social cumple (SI/NO)",
    "Inducción del empleador registrada (SI/NO)",
    "Responsable de SST en planta — nombre",
    "Responsable de SST en planta — teléfono",
    "Radicación OK (SI/NO)",
    "Radicado por",
    "Validador",
    "Requisitos OK verificados (SI/NO)",
    "Examen médico" + _SUFIJO_ESTADO,
    "Examen médico" + _SUFIJO_FECHA,
    "Certificación de trabajo en alturas" + _SUFIJO_ESTADO,
    "Certificación de trabajo en alturas" + _SUFIJO_FECHA,
]

# Posiciones 1-indexadas (columna Excel) dentro de ENCABEZADOS_BASE.
COL_FECHA_REVISION = 1
COL_VALIDACION = 2
COL_CONTRATISTA = 3
COL_AUTORIZACION = 7
COL_VINCULACION = 11
COL_FECHA_INICIO = 12
COL_CASCO_ROJO = 14
COL_CLASE_RIESGO = 15
COL_AREA_TRABAJO = 16
COL_FORMATO_INCLUSION = 17
COL_REGISTROS_EPP = 18
COL_PAGO_SEGURIDAD = 19
COL_INDUCCION_EMPLEADOR = 20
COL_RADICACION_OK = 23
COL_REQUISITOS_OK = 26
COL_ESTADO_EXAMEN = 27
COL_FECHA_EXAMEN = 28
COL_ESTADO_ALTURAS = 29
COL_FECHA_ALTURAS = 30

_COLUMNAS_SI_NO = [
    COL_AUTORIZACION,
    COL_CASCO_ROJO,
    COL_FORMATO_INCLUSION,
    COL_REGISTROS_EPP,
    COL_PAGO_SEGURIDAD,
    COL_INDUCCION_EMPLEADOR,
    COL_RADICACION_OK,
    COL_REQUISITOS_OK,
]

# Filas con el desplegable ya aplicado en la plantilla descargable, para
# poder pegar/escribir varias de una vez sin tener que repetir la validación.
FILAS_PLANTILLA = 300

_ETIQUETA_A_TIPO_VINCULACION = {
    "fijo": Trabajador.TipoVinculacion.FIJO,
    "temporal": Trabajador.TipoVinculacion.TEMPORAL,
}
_ETIQUETA_A_TIPO_VALIDACION = {
    "ingreso": Trabajador.TipoValidacion.INGRESO,
    "renovacion": Trabajador.TipoValidacion.RENOVACION,
}
_ETIQUETA_A_AREA_TRABAJO = {
    "proyecto": Trabajador.AreaTrabajo.PROYECTO,
    "envase": Trabajador.AreaTrabajo.ENVASE,
    "elaboracion": Trabajador.AreaTrabajo.ELABORACION,
    "ingenieria y serv": Trabajador.AreaTrabajo.INGENIERIA_SERV,
    "calidad": Trabajador.AreaTrabajo.CALIDAD,
    "people": Trabajador.AreaTrabajo.PEOPLE,
}
_VALORES_SI = {"si", "s", "x", "yes", "true", "1"}
_VALORES_NO_APLICA = {"na", "n/a", "n.a.", "n.a", "no aplica"}


def _sin_acentos(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).strip().lower()


def _texto_celda(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _es_si(valor):
    return _sin_acentos(valor or "") in _VALORES_SI


def _valor_fecha(celda):
    """Acepta una fecha real de Excel (elegida con el calendario), texto
    AAAA-MM-DD o DD/MM/AAAA, o "N/A" (y variantes) para "no aplica" — en
    los tres casos que no sean una fecha reconocible el resultado es
    simplemente None: el campo es opcional y una celda con N/A o vacía
    significan lo mismo (no diligenciado), así que ninguna tumba la fila.
    Para examen médico, alturas y certificaciones especiales, la forma
    "oficial" de marcar N/A es la columna de estado que antecede a la
    fecha (ver `_fecha_segun_estado`) — esto solo cubre el caso en que
    alguien lo escriba directo en la celda de fecha de todas formas."""
    if celda in (None, ""):
        return None
    if isinstance(celda, datetime.datetime):
        return celda.date()
    if isinstance(celda, datetime.date):
        return celda
    texto = str(celda).strip()
    if not texto or _sin_acentos(texto) in _VALORES_NO_APLICA:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _fecha_segun_estado(celda_estado, celda_fecha):
    """Réplica de la fórmula del cliente `IF(estado="NA","NA",fecha)`: si la
    columna de estado (OutSafety/Drive/NA/No validado) dice "NA", esa
    certificación no aplica y la fecha se ignora aunque haya algo escrito —
    así el estado manda, igual que en el Excel original."""
    if _sin_acentos(celda_estado or "") in _VALORES_NO_APLICA:
        return None
    return _valor_fecha(celda_fecha)


def _catalogo_cursos():
    return list(CursoSafetyAcademy.objects.filter(activo=True).order_by("orden", "etiqueta"))


def _catalogo_certificaciones():
    return list(CertificacionEspecial.objects.filter(activo=True).order_by("orden", "etiqueta"))


def _encabezados_y_catalogos():
    """(encabezados, claves_cursos, claves_certificaciones) — se calcula en
    cada llamada (no una vez al importar el módulo) porque ambos catálogos
    son editables desde el dashboard. Los cursos Safety Academy son una
    sola columna de fecha cada uno (igual que en el Excel del cliente, que
    los agrupa en un solo paquete de inducciones); las certificaciones
    especiales llevan, como examen médico y alturas, su columna de estado
    antes de la fecha."""
    cursos = _catalogo_cursos()
    certificaciones = _catalogo_certificaciones()
    encabezados_cursos = [f"Curso: {c.etiqueta} — vencimiento (AAAA-MM-DD o N/A)" for c in cursos]
    encabezados_certificaciones = []
    for c in certificaciones:
        encabezados_certificaciones.append(f"Certificación: {c.etiqueta}{_SUFIJO_ESTADO}")
        encabezados_certificaciones.append(f"Certificación: {c.etiqueta}{_SUFIJO_FECHA}")
    encabezados = ENCABEZADOS_BASE + encabezados_cursos + encabezados_certificaciones
    claves_cursos = [c.clave for c in cursos]
    claves_certificaciones = [c.clave for c in certificaciones]
    return encabezados, claves_cursos, claves_certificaciones


def _agregar_lista(hoja, columna, opciones, primera_fila, ultima_fila, allow_blank=True):
    letra = get_column_letter(columna)
    dv = DataValidation(type="list", formula1=f'"{opciones}"', allow_blank=allow_blank)
    hoja.add_data_validation(dv)
    dv.add(f"{letra}{primera_fila}:{letra}{ultima_fila}")


def _agregar_validacion_fecha(hoja, columna, primera_fila, ultima_fila):
    """Restringe la columna a fechas — Excel muestra el ícono de calendario
    junto a la celda para elegirla sin escribir nada. `errorStyle="warning"`
    (no "stop") para no bloquear a quien deja la fecha vacía porque la
    columna de estado ya dice "NA"."""
    letra = get_column_letter(columna)
    dv = DataValidation(
        type="date",
        operator="between",
        formula1="DATE(2000,1,1)",
        formula2="DATE(2099,12,31)",
        allow_blank=True,
        showErrorMessage=True,
        errorStyle="warning",
        errorTitle="¿Es una fecha?",
        error="Usa el calendario junto a la celda para elegir la fecha, o deja la columna de estado en NA si no aplica.",
    )
    hoja.add_data_validation(dv)
    dv.add(f"{letra}{primera_fila}:{letra}{ultima_fila}")


def _agregar_colores_vigencia(hoja, columna, primera_fila, ultima_fila):
    """3 colores sobre la fecha de vencimiento misma (no una columna de
    estado aparte, para no duplicar columnas): rojo vencida, ámbar si vence
    en 15 días o menos, verde si todavía falta más — mismo umbral que usa
    el resto de la app. Una celda vacía no cae en ninguna regla, así que
    queda sin colorear."""
    letra = get_column_letter(columna)
    rango = f"{letra}{primera_fila}:{letra}{ultima_fila}"
    ref = f"{letra}{primera_fila}"
    hoja.conditional_formatting.add(
        rango, FormulaRule(formula=[f"AND(ISNUMBER({ref}),{ref}<TODAY())"], fill=FILL_VENCIDO)
    )
    hoja.conditional_formatting.add(
        rango,
        FormulaRule(formula=[f"AND(ISNUMBER({ref}),{ref}>=TODAY(),{ref}<=TODAY()+15)"], fill=FILL_POR_VENCER),
    )
    hoja.conditional_formatting.add(
        rango, FormulaRule(formula=[f"AND(ISNUMBER({ref}),{ref}>TODAY()+15)"], fill=FILL_VIGENTE)
    )


FILL_VENCIDO = PatternFill(start_color="FFFF0000", end_color="FFFF0000", fill_type="solid")
FILL_POR_VENCER = PatternFill(start_color="FFFFC000", end_color="FFFFC000", fill_type="solid")
FILL_VIGENTE = PatternFill(start_color="FF00B050", end_color="FF00B050", fill_type="solid")


def generar_plantilla_trabajadores_excel():
    """Libro .xlsx en blanco con los encabezados y los desplegables
    (Contratista, autorización de datos, tipo de vinculación, validación,
    SI/NO, estados de certificado — solo empresas activas) ya aplicados a
    las primeras FILAS_PLANTILLA filas — lista para llenar y volver a
    subir. Las columnas de fecha quedan con selector de calendario, y las
    de vencimiento (examen médico, alturas, cursos, certificaciones) con
    los mismos 3 colores de vigencia que usa el resto del sistema.
    "Fecha de revisión y validación" viene prellenada con la fecha de hoy
    (cuando se descarga la plantilla), editable si la revisión real fue
    otro día."""
    contratistas = list(
        EmpresaContratista.objects.filter(activa=True).order_by("nombre").values_list("nombre", flat=True)
    )
    encabezados, claves_cursos, claves_certificaciones = _encabezados_y_catalogos()
    ultima_columna = len(encabezados)
    ultima_fila = FILAS_PLANTILLA + 1

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = HOJA_TRABAJADORES
    hoja.append(encabezados)
    for celda in hoja[1]:
        celda.font = celda.font.copy(bold=True)

    hoy = datetime.date.today()
    for fila in range(2, ultima_fila + 1):
        celda = hoja.cell(row=fila, column=COL_FECHA_REVISION, value=hoy)
        celda.number_format = "YYYY-MM-DD"

    hoja_listas = libro.create_sheet(HOJA_LISTAS)
    for fila, nombre in enumerate(contratistas, start=1):
        hoja_listas.cell(row=fila, column=1, value=nombre)
    hoja_listas.sheet_state = "hidden"

    ultima_fila_listas = max(len(contratistas), 1)
    letra_contratista = get_column_letter(COL_CONTRATISTA)
    dv_contratista = DataValidation(
        type="list",
        formula1=f"'{HOJA_LISTAS}'!$A$1:$A${ultima_fila_listas}",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Contratista no válido",
        error="Elige una empresa contratista de la lista desplegable.",
    )
    hoja.add_data_validation(dv_contratista)
    dv_contratista.add(f"{letra_contratista}2:{letra_contratista}{ultima_fila}")

    _agregar_lista(hoja, COL_VALIDACION, "Ingreso,Renovación", 2, ultima_fila)
    _agregar_lista(hoja, COL_VINCULACION, "Fijo,Temporal", 2, ultima_fila)
    _agregar_lista(hoja, COL_CLASE_RIESGO, "I,II,III,IV,V", 2, ultima_fila)
    _agregar_lista(
        hoja, COL_AREA_TRABAJO, "Proyecto,Envase,Elaboración,Ingeniería y Serv,Calidad,People", 2, ultima_fila
    )
    for columna in _COLUMNAS_SI_NO:
        _agregar_lista(hoja, columna, "SI,NO", 2, ultima_fila)

    # Columnas de estado (OutSafety/Drive/NA/No validado) — una por cada
    # vencimiento que puede "no aplicar": examen médico, alturas y cada
    # certificación especial. Los cursos Safety Academy no llevan columna
    # de estado (el cliente los agrupa en un solo paquete sin ese detalle).
    columnas_estado = [COL_ESTADO_EXAMEN, COL_ESTADO_ALTURAS]
    columnas_vencimiento = [COL_FECHA_EXAMEN, COL_FECHA_ALTURAS]
    primera_columna_cursos = len(ENCABEZADOS_BASE) + 1
    columnas_vencimiento += list(range(primera_columna_cursos, primera_columna_cursos + len(claves_cursos)))

    primera_columna_certificaciones = primera_columna_cursos + len(claves_cursos)
    for indice in range(len(claves_certificaciones)):
        columna_estado = primera_columna_certificaciones + indice * 2
        columnas_estado.append(columna_estado)
        columnas_vencimiento.append(columna_estado + 1)

    for columna in columnas_estado:
        _agregar_lista(hoja, columna, ESTADO_VALIDACION_OPCIONES, 2, ultima_fila)
    for columna in columnas_vencimiento:
        _agregar_validacion_fecha(hoja, columna, 2, ultima_fila)
        _agregar_colores_vigencia(hoja, columna, 2, ultima_fila)

    for columna in (COL_FECHA_REVISION, COL_FECHA_INICIO):
        _agregar_validacion_fecha(hoja, columna, 2, ultima_fila)

    anchos_base = [
        26, 22, 26, 20, 20, 16, 24, 14, 14, 14, 26, 24, 22,
        20, 18, 26, 30, 28, 24, 26, 26, 22, 18, 22, 22, 24,
        32, 28, 32, 28,
    ]
    # Los cursos son 1 columna (fecha) cada uno; las certificaciones 2
    # (estado + fecha), igual que examen médico/alturas arriba.
    anchos = anchos_base + [30] * len(claves_cursos) + [24, 30] * len(claves_certificaciones)
    for indice, ancho in enumerate(anchos, start=1):
        hoja.column_dimensions[get_column_letter(indice)].width = ancho

    # Deja libres para escribir solo las celdas de datos (encabezado incluido
    # como referencia, pero bloqueado); todo lo demás de la hoja —fórmulas de
    # validación, formato— queda protegido una vez se activa hoja.protection.
    celda_desbloqueada = Protection(locked=False)
    for fila in hoja.iter_rows(min_row=2, max_row=ultima_fila, min_col=1, max_col=ultima_columna):
        for celda in fila:
            celda.protection = celda_desbloqueada

    hoja.protection.sheet = True
    hoja.protection.password = CONTRASENA_PLANTILLA
    hoja.protection.formatColumns = False
    hoja.protection.formatRows = False

    hoja_listas.protection.sheet = True
    hoja_listas.protection.password = CONTRASENA_PLANTILLA

    libro.security = WorkbookProtection(lockStructure=True)
    libro.security.set_workbook_password(CONTRASENA_PLANTILLA)

    return libro


def procesar_trabajadores_excel(archivo):
    """Lee el Excel y devuelve (filas, errores_lectura):

    - `filas`: lista de dicts, uno por fila con datos, con las mismas
      claves que TrabajadorSerializer espera, más "_fila_excel" (el
      número de fila real del Excel, para señalarlo en los mensajes de
      error del caller si la fila no pasa la validación del serializer).
    - `errores_lectura`: filas que no se pudieron ni armar (ej. el
      nombre de la columna Contratista no calza con ninguna empresa) —
      errores de estructura, no de validación de negocio."""
    try:
        libro = openpyxl.load_workbook(archivo, data_only=True)
    except Exception as exc:
        raise ErrorImportacionExcel("No se pudo leer el archivo — asegúrate de que sea un .xlsx válido.") from exc

    hoja = libro[HOJA_TRABAJADORES] if HOJA_TRABAJADORES in libro.sheetnames else libro.active

    contratistas_por_nombre = {
        _sin_acentos(nombre): id_
        for id_, nombre in EmpresaContratista.objects.filter(activa=True).values_list("id", "nombre")
    }
    encabezados, claves_cursos, claves_certificaciones = _encabezados_y_catalogos()
    indice_cursos = len(ENCABEZADOS_BASE)
    indice_certificaciones = indice_cursos + len(claves_cursos)

    filas = []
    errores_lectura = []
    for numero_fila, fila in enumerate(hoja.iter_rows(min_row=2, values_only=True), start=2):
        if fila is None or all(c in (None, "") for c in fila):
            continue
        celdas = list(fila) + [None] * (len(encabezados) - len(fila))
        celdas = celdas[: len(encabezados)]
        (
            fecha_revision_txt,
            validacion_txt,
            contratista_txt,
            nombres,
            apellidos,
            documento,
            autorizacion_txt,
            eps,
            arl,
            afp,
            vinculacion_txt,
            fecha_inicio,
            numero_pedido_cm,
            casco_rojo_txt,
            clase_riesgo_txt,
            area_trabajo_txt,
            formato_inclusion_txt,
            registros_epp_txt,
            pago_seguridad_txt,
            induccion_empleador_txt,
            responsable_sst_planta_nombre,
            responsable_sst_planta_telefono,
            radicacion_ok_txt,
            radicado_por,
            validador,
            requisitos_ok_txt,
            estado_examen,
            fecha_examen,
            estado_alturas,
            fecha_alturas,
        ) = celdas[:indice_cursos]
        celdas_cursos = celdas[indice_cursos:indice_certificaciones]
        celdas_certificaciones = celdas[indice_certificaciones:]

        if not any([contratista_txt, nombres, apellidos, documento]):
            continue

        contratista_id = contratistas_por_nombre.get(_sin_acentos(contratista_txt or ""))
        if contratista_id is None:
            errores_lectura.append(
                {
                    "fila": numero_fila,
                    "mensaje": (
                        f'No se encontró la empresa contratista "{contratista_txt or "(vacío)"}" — '
                        "usa el desplegable de la columna Contratista."
                    ),
                }
            )
            continue

        vinculacion = _ETIQUETA_A_TIPO_VINCULACION.get(
            _sin_acentos(vinculacion_txt or ""), Trabajador.TipoVinculacion.FIJO
        )
        tipo_validacion = _ETIQUETA_A_TIPO_VALIDACION.get(_sin_acentos(validacion_txt or ""), "")
        area_trabajo = _ETIQUETA_A_AREA_TRABAJO.get(_sin_acentos(area_trabajo_txt or ""), "")
        clase_riesgo = _texto_celda(clase_riesgo_txt).upper()
        if clase_riesgo not in {c.value for c in Trabajador.ClaseRiesgo}:
            clase_riesgo = ""

        cursos_safety_academy = {}
        for clave, celda_curso in zip(claves_cursos, celdas_cursos):
            fecha_curso = _valor_fecha(celda_curso)
            if fecha_curso is not None:
                cursos_safety_academy[clave] = fecha_curso.isoformat()

        certificaciones_especiales = {}
        for indice, clave in enumerate(claves_certificaciones):
            celda_estado = celdas_certificaciones[indice * 2] if indice * 2 < len(celdas_certificaciones) else None
            celda_fecha = (
                celdas_certificaciones[indice * 2 + 1] if indice * 2 + 1 < len(celdas_certificaciones) else None
            )
            fecha_cert = _fecha_segun_estado(celda_estado, celda_fecha)
            if fecha_cert is not None:
                certificaciones_especiales[clave] = fecha_cert.isoformat()

        filas.append(
            {
                "_fila_excel": numero_fila,
                "contratista": contratista_id,
                "nombres": _texto_celda(nombres),
                "apellidos": _texto_celda(apellidos),
                "documento": _texto_celda(documento),
                "autorizacion_datos": _es_si(autorizacion_txt),
                "eps": _texto_celda(eps),
                "arl": _texto_celda(arl),
                "afp": _texto_celda(afp),
                "tipo_vinculacion": vinculacion,
                "fecha_inicio_contrato": _valor_fecha(fecha_inicio),
                "fecha_revision_validacion": _valor_fecha(fecha_revision_txt),
                "tipo_validacion": tipo_validacion,
                "numero_pedido_cm": _texto_celda(numero_pedido_cm),
                "casco_rojo": _es_si(casco_rojo_txt),
                "clase_riesgo": clase_riesgo,
                "area_trabajo": area_trabajo,
                "formato_inclusion_firmado": _es_si(formato_inclusion_txt),
                "registros_epp_entregados": _es_si(registros_epp_txt),
                "pago_seguridad_cumple": _es_si(pago_seguridad_txt),
                "induccion_empleador_registrada": _es_si(induccion_empleador_txt),
                "responsable_sst_planta_nombre": _texto_celda(responsable_sst_planta_nombre),
                "responsable_sst_planta_telefono": _texto_celda(responsable_sst_planta_telefono),
                "radicacion_ok": _es_si(radicacion_ok_txt),
                "radicado_por": _texto_celda(radicado_por),
                "validador": _texto_celda(validador),
                "requisitos_ok_verificados": _es_si(requisitos_ok_txt),
                "fecha_vencimiento_examen_medico": _fecha_segun_estado(estado_examen, fecha_examen),
                "fecha_vencimiento_certificacion_alturas": _fecha_segun_estado(estado_alturas, fecha_alturas),
                "cursos_safety_academy": cursos_safety_academy,
                "certificaciones_especiales": certificaciones_especiales,
            }
        )

    return filas, errores_lectura
