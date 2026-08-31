import hashlib
import json

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from core.models import Empresa
from core.validators import validar_tamano_archivo


class EmpresaContratista(models.Model):
    """Empresa contratista que envía personal a trabajar en las plantas de la empresa cliente."""

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="contratistas")
    nombre = models.CharField(max_length=200)
    nit = models.CharField("NIT", max_length=30, blank=True)
    contacto_nombre = models.CharField("nombre de contacto", max_length=150, blank=True)
    contacto_telefono = models.CharField("teléfono de contacto", max_length=30, blank=True)
    contacto_correo = models.EmailField("correo de contacto", blank=True)
    responsable_sst_nombre = models.CharField("responsable SST/SISO", max_length=150, blank=True)
    responsable_sst_telefono = models.CharField("teléfono responsable SST", max_length=30, blank=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "empresa contratista"
        verbose_name_plural = "empresas contratistas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


def soporte_autorizacion_upload_to(instance, filename):
    return f"autorizaciones_datos/{instance.contratista_id}/{filename}"


class Trabajador(models.Model):
    """Trabajador de una empresa contratista, con sus datos de afiliación."""

    class TipoVinculacion(models.TextChoices):
        FIJO = "fijo", "Fijo"
        TEMPORAL = "temporal", "Temporal"

    contratista = models.ForeignKey(EmpresaContratista, on_delete=models.CASCADE, related_name="trabajadores")
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    documento = models.CharField("documento de identidad", max_length=30)
    eps = models.CharField("EPS", max_length=100, blank=True)
    arl = models.CharField("ARL", max_length=100, blank=True)
    afp = models.CharField("AFP", max_length=100, blank=True)
    tipo_vinculacion = models.CharField(max_length=20, choices=TipoVinculacion.choices, default=TipoVinculacion.FIJO)
    fecha_inicio_contrato = models.DateField(null=True, blank=True)
    cursos_safety_academy = models.JSONField(
        "cursos Safety Academy",
        default=dict,
        blank=True,
        help_text="Mapa {tipo_curso: fecha ISO o null} — ver Trabajador.CURSOS para las claves válidas",
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    autorizacion_datos = models.BooleanField(
        "autorización de tratamiento de datos personales",
        default=False,
        help_text=(
            "Habeas Data (Ley 1581 de 2012) — el trabajador (o quien radica en su nombre) autorizó el "
            "tratamiento de sus datos personales, incluidos los de afiliación a seguridad social."
        ),
    )
    autorizacion_datos_en = models.DateTimeField(
        "autorización otorgada el", null=True, blank=True
    )
    soporte_autorizacion_datos = models.FileField(
        "evidencia de la autorización",
        upload_to=soporte_autorizacion_upload_to,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png"]),
            validar_tamano_archivo,
        ],
        help_text=(
            "Foto o PDF del formato de autorización firmado por el trabajador — respalda la casilla "
            "marcada arriba. Opcional pero recomendado como evidencia."
        ),
    )

    CURSOS = {
        "induccion_sst": "Inducción SST",
        "riesgo_quimico": "Gestión de Riesgo Químico",
        "sam_jog_lototo": "SAM JOG LOTOTO",
        "pasos_seguros": "Pasos seguros",
        "comportamientos_condiciones": "Grupo de comportamientos y condiciones",
        "identificacion_peligros": "Identificación de peligros, valoración y control del riesgo",
        "epp": "Elementos de protección personal",
    }

    class Meta:
        verbose_name = "trabajador"
        verbose_name_plural = "trabajadores"
        ordering = ["apellidos", "nombres"]
        unique_together = [("contratista", "documento")]

    def __str__(self):
        return f"{self.apellidos} {self.nombres} ({self.documento})"

    @property
    def cursos_pendientes(self):
        """Cursos Safety Academy marcados como obligatorios que este
        trabajador todavía no tiene completados (sin fecha registrada).
        Se calcula al vuelo contra el catálogo actual — nada queda
        guardado, así que un curso recién marcado obligatorio aplica a
        todos los trabajadores activos sin necesidad de tocarlos uno por uno."""
        completados = self.cursos_safety_academy or {}
        return [
            {"clave": c.clave, "etiqueta": c.etiqueta}
            for c in CursoSafetyAcademy.objects.filter(activo=True, obligatorio=True)
            if not completados.get(c.clave)
        ]


def soporte_pago_upload_to(instance, filename):
    return f"seguridad_social/{instance.trabajador.contratista_id}/{filename}"


class RadicacionSeguridadSocial(models.Model):
    """Radicación mensual del soporte de pago de seguridad social de un trabajador."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name="radicaciones")
    anio = models.PositiveIntegerField()
    mes = models.CharField(max_length=20)
    numero_planilla = models.CharField("número de planilla", max_length=40, blank=True)
    fecha_vencimiento = models.DateField("fecha de vencimiento de la planilla", null=True, blank=True)
    soporte_pago = models.FileField(
        "soporte de pago",
        upload_to=soporte_pago_upload_to,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png"]),
            validar_tamano_archivo,
        ],
        help_text="PDF de la planilla integrada de autoliquidación de aportes (PILA)",
    )
    interventor = models.CharField(max_length=150, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.TextField(blank=True)
    radicada_en = models.DateTimeField(auto_now_add=True)
    revisada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "radicación de seguridad social"
        verbose_name_plural = "radicaciones de seguridad social"
        ordering = ["-radicada_en"]

    def __str__(self):
        return f"{self.trabajador} — {self.mes} {self.anio}"

    @property
    def vencida(self):
        """True si la planilla ya pasó su fecha de vencimiento — nada la
        marca sola en la base, se calcula al vuelo contra la fecha de hoy."""
        return bool(self.fecha_vencimiento and self.fecha_vencimiento < timezone.localdate())

    @property
    def dias_para_vencer(self):
        """Días que faltan para vencer (negativo si ya venció). None si no
        tiene fecha de vencimiento registrada."""
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - timezone.localdate()).days


DIAS_ALERTA_VENCIMIENTO = 15  # a cuántos días de vencer se considera "por vencer" en los indicadores


class DeclaracionMetodo(models.Model):
    """Declaración de método y evaluación de riesgo (formato GEINCOR/Kinney) para un trabajo puntual."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ENVIADA = "enviada", "Enviada"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    contratista = models.ForeignKey(
        EmpresaContratista, on_delete=models.CASCADE, related_name="declaraciones_metodo"
    )
    planta_area = models.CharField("planta / área", max_length=150, blank=True)
    numero_pedido = models.CharField("número de pedido", max_length=50, blank=True)
    gerente_proyecto = models.CharField(max_length=150, blank=True)
    contacto_nombre = models.CharField(max_length=150, blank=True)
    contacto_telefono = models.CharField(max_length=30, blank=True)
    fecha_elaboracion = models.DateField()
    duracion_dias = models.PositiveIntegerField(default=1)
    descripcion_trabajo = models.TextField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    observaciones = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "declaración de método"
        verbose_name_plural = "declaraciones de método"
        ordering = ["-creada_en"]

    def __str__(self):
        return f"{self.descripcion_trabajo[:50]} — {self.contratista.nombre}"


PERMISOS_TRABAJO = [
    "Trabajos de LOTOTO",
    "Trabajos en Altura > 1.8 m",
    "Espacio Confinado",
    "Excavaciones o Demolición",
    "Izaje (grúa, tecle, polipasto, montacargas, poleas)",
    "Subestaciones (sistemas eléctricos vivos)",
    "Trabajos en Caliente",
    "Sustancias Peligrosas a Granel",
    "Otros",
]


class ActividadMetodo(models.Model):
    """Un paso de la secuencia de actividades, con su evaluación de riesgo Kinney
    antes y después de aplicar las medidas de mitigación (R = Probabilidad × Frecuencia × Impacto)."""

    declaracion = models.ForeignKey(DeclaracionMetodo, on_delete=models.CASCADE, related_name="actividades")
    orden = models.PositiveIntegerField(default=0)
    secuencia = models.TextField("secuencia de actividad")
    tecnicas_herramientas = models.TextField("técnicas / herramientas / equipos", blank=True)
    descripcion_riesgo = models.TextField(blank=True)
    probabilidad_sin = models.FloatField("probabilidad (sin mitigación)", default=0)
    frecuencia_sin = models.FloatField("frecuencia (sin mitigación)", default=0)
    impacto_sin = models.FloatField("impacto (sin mitigación)", default=0)
    medidas_mitigacion = models.TextField(blank=True)
    probabilidad_con = models.FloatField("probabilidad (con mitigación)", default=0)
    frecuencia_con = models.FloatField("frecuencia (con mitigación)", default=0)
    impacto_con = models.FloatField("impacto (con mitigación)", default=0)
    permisos_requeridos = models.JSONField(default=list, blank=True)
    tarea_sif = models.BooleanField("tarea SIF", default=False)

    class Meta:
        verbose_name = "actividad de declaración de método"
        verbose_name_plural = "actividades de declaración de método"
        ordering = ["declaracion", "orden"]

    def __str__(self):
        return self.secuencia[:60]

    @property
    def riesgo_sin(self):
        return round(self.probabilidad_sin * self.frecuencia_sin * self.impacto_sin, 2)

    @property
    def riesgo_con(self):
        return round(self.probabilidad_con * self.frecuencia_con * self.impacto_con, 2)


def nivel_riesgo(valor):
    """Clasifica un puntaje de riesgo Kinney (P×F×I) según las bandas estándar del método."""
    if valor > 400:
        return "muy_alto", "Riesgo muy alto — detener esta actividad específica"
    if valor > 200:
        return "alto", "Riesgo alto — requiere acción inmediata"
    if valor > 70:
        return "considerable", "Riesgo considerable — requiere corrección"
    if valor > 20:
        return "posible", "Riesgo posible — requiere supervisión/atención"
    return "bajo", "Riesgo bajo — aceptable"


def calcular_hash_declaracion(declaracion):
    """Huella digital (sha256) del contenido de la declaración en un momento
    dado — encabezado + actividades, en un orden fijo — para poder detectar
    después si el documento cambió tras haber sido firmado."""
    actividades = [
        {
            "orden": a.orden,
            "secuencia": a.secuencia,
            "tecnicas_herramientas": a.tecnicas_herramientas,
            "descripcion_riesgo": a.descripcion_riesgo,
            "probabilidad_sin": a.probabilidad_sin,
            "frecuencia_sin": a.frecuencia_sin,
            "impacto_sin": a.impacto_sin,
            "medidas_mitigacion": a.medidas_mitigacion,
            "probabilidad_con": a.probabilidad_con,
            "frecuencia_con": a.frecuencia_con,
            "impacto_con": a.impacto_con,
            "permisos_requeridos": a.permisos_requeridos,
            "tarea_sif": a.tarea_sif,
        }
        for a in declaracion.actividades.order_by("orden")
    ]
    contenido = {
        "planta_area": declaracion.planta_area,
        "numero_pedido": declaracion.numero_pedido,
        "gerente_proyecto": declaracion.gerente_proyecto,
        "contacto_nombre": declaracion.contacto_nombre,
        "contacto_telefono": declaracion.contacto_telefono,
        "fecha_elaboracion": str(declaracion.fecha_elaboracion),
        "duracion_dias": declaracion.duracion_dias,
        "descripcion_trabajo": declaracion.descripcion_trabajo,
        "actividades": actividades,
    }
    bruto = json.dumps(contenido, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(bruto).hexdigest()


class FirmaMetodo(models.Model):
    """Firma electrónica de uno de los roles requeridos en la declaración de
    método: queda ligada a la cuenta autenticada que firmó (no a un texto
    libre que cualquiera podría escribir) y a una huella del documento en
    el momento de la firma, para poder detectar cambios posteriores."""

    class Rol(models.TextChoices):
        SUPERVISOR_CONTRATISTA = "supervisor_contratista", "Supervisor de Seguridad del Contratista"
        DELEGADO_ABI = "delegado_abi", "Delegado (Contratante)"
        SEGURIDAD_PLANTA = "seguridad_planta", "Seguridad de Planta (Site)"
        LIDER_AREA = "lider_area", "Líder de Área"
        DUENO_TERRITORIO = "dueno_territorio", "Dueño de Territorio"

    declaracion = models.ForeignKey(DeclaracionMetodo, on_delete=models.CASCADE, related_name="firmas")
    rol = models.CharField(max_length=30, choices=Rol.choices)
    nombre_firmante = models.CharField(max_length=150)
    firmante_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="firmas_metodo",
        null=True,
        blank=True,
        help_text=(
            "Cuenta autenticada que ejecutó la firma — no se puede eliminar mientras tenga firmas "
            "registradas. Nulo solo en firmas anteriores a este control."
        ),
    )
    hash_documento = models.CharField(
        max_length=64,
        blank=True,
        help_text="Huella sha256 de la declaración en el momento de esta firma.",
    )
    firmado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "firma de declaración de método"
        verbose_name_plural = "firmas de declaración de método"
        unique_together = [("declaracion", "rol")]
        ordering = ["declaracion", "rol"]

    def __str__(self):
        return f"{self.get_rol_display()}: {self.nombre_firmante}"

    @property
    def documento_modificado_despues_de_firmar(self):
        """True si la declaración cambió después de esta firma — compara la
        huella guardada al firmar contra el contenido actual."""
        if not self.hash_documento:
            return False
        return self.hash_documento != calcular_hash_declaracion(self.declaracion)


class Funcionario(models.Model):
    """Persona autorizada para firmar declaraciones de método en uno de los
    roles internos de la empresa cliente (no el supervisor del contratista,
    que cambia por proyecto y se sigue escribiendo libre). Es el padrón que
    el formulario de firma ofrece para elegir en vez de un texto libre."""

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="funcionarios")
    nombre = models.CharField(max_length=150)
    cargo = models.CharField(max_length=150, blank=True)
    rol_firma = models.CharField(
        max_length=30,
        choices=[c for c in FirmaMetodo.Rol.choices if c[0] != FirmaMetodo.Rol.SUPERVISOR_CONTRATISTA],
    )
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "funcionario firmante"
        verbose_name_plural = "funcionarios firmantes"
        ordering = ["rol_firma", "nombre"]

    def __str__(self):
        return f"{self.nombre} — {self.get_rol_firma_display()}"


class CursoSafetyAcademy(models.Model):
    """Catálogo editable de cursos Safety Academy — reemplaza el diccionario
    fijo Trabajador.CURSOS para que un Administrador pueda agregar o
    desactivar cursos sin tocar código. La clave sigue siendo la que se
    guarda en Trabajador.cursos_safety_academy."""

    clave = models.SlugField(max_length=50, unique=True)
    etiqueta = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    obligatorio = models.BooleanField(
        "obligatorio para todo trabajador",
        default=False,
        help_text="Si está marcado, se avisa cuando un trabajador activo no lo tiene completado.",
    )
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "curso Safety Academy"
        verbose_name_plural = "cursos Safety Academy"
        ordering = ["orden", "etiqueta"]

    def __str__(self):
        return self.etiqueta


class PermisoTrabajo(models.Model):
    """Catálogo editable de permisos de trabajo/certificados requeridos —
    reemplaza la lista fija PERMISOS_TRABAJO."""

    nombre = models.CharField(max_length=200, unique=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "permiso de trabajo"
        verbose_name_plural = "permisos de trabajo"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class ConfiguracionAlertas(models.Model):
    """Fila única (singleton), igual que ConfiguracionNotificaciones en
    camaras_ia — a cuántos días de vencer una planilla se considera "por
    vencer" en los indicadores, editable desde el dashboard."""

    dias_alerta_vencimiento = models.PositiveIntegerField(
        "días de alerta antes de vencer",
        default=DIAS_ALERTA_VENCIMIENTO,
        help_text="A cuántos días de vencer una planilla se considera 'por vencer' en los indicadores.",
    )
    correo_revisor = models.EmailField(
        "correo para avisos de revisión pendiente",
        blank=True,
        help_text=(
            "A dónde avisar cuando se radica seguridad social o se envía una declaración de método que "
            "queda pendiente de revisión. Vacío = no se envía ese aviso (el de aprobado/rechazado sigue "
            "yendo siempre al contacto de la empresa contratista)."
        ),
    )
    actualizada_en = models.DateTimeField("actualizada en", auto_now=True)

    class Meta:
        verbose_name = "configuración de alertas"
        verbose_name_plural = "configuración de alertas"

    def __str__(self):
        return "Configuración de alertas"

    @classmethod
    def obtener(cls):
        objeto, _ = cls.objects.get_or_create(pk=1)
        return objeto


class RegistroAuditoria(models.Model):
    """Traza de quién creó/editó/eliminó un registro y qué cambió — para los
    modelos críticos de cumplimiento (contratistas, trabajadores,
    radicaciones, declaraciones de método, funcionarios firmantes). Guarda
    un string del objeto y no solo su id, para que la traza siga siendo
    legible aunque el registro original ya se haya eliminado."""

    class Accion(models.TextChoices):
        CREADO = "creado", "Creado"
        ACTUALIZADO = "actualizado", "Actualizado"
        ELIMINADO = "eliminado", "Eliminado"

    modelo = models.CharField(max_length=100)
    objeto_id = models.PositiveIntegerField()
    objeto_str = models.CharField(max_length=300)
    accion = models.CharField(max_length=20, choices=Accion.choices)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    cambios = models.JSONField(default=dict, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.get_accion_display()} — {self.modelo} #{self.objeto_id}"


class AutorizacionIngreso(models.Model):
    """Autorización de ingreso de personal contratista a la planta —
    formato real "AUTORIZACION DE INGRESO PERSONAL CONTRATISTA": vigencia,
    horario, área de trabajo, sitio de encuentro en emergencia y
    responsable SISO del grupo, con la lista de trabajadores incluidos o
    excluidos del ingreso (ver TrabajadorAutorizacionIngreso)."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ENVIADA = "enviada", "Enviada"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    contratista = models.ForeignKey(
        EmpresaContratista, on_delete=models.CASCADE, related_name="autorizaciones_ingreso"
    )
    declaracion = models.ForeignKey(
        DeclaracionMetodo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="autorizaciones_ingreso",
        help_text="Declaración de método a la que corresponde este trabajo, si aplica.",
    )
    fecha_inicio = models.DateField("vigencia — desde")
    fecha_fin = models.DateField("vigencia — hasta")
    hora_inicio = models.TimeField("horario — desde", null=True, blank=True)
    hora_fin = models.TimeField("horario — hasta", null=True, blank=True)
    area_trabajo = models.CharField(max_length=200)
    sitio_encuentro_emergencia = models.CharField(
        "sitio de encuentro en caso de emergencia", max_length=200, blank=True
    )
    responsable_siso_nombre = models.CharField("responsable SISO del grupo", max_length=150)
    responsable_siso_cargo = models.CharField("cargo del responsable SISO", max_length=150, blank=True)
    responsable_siso_telefono = models.CharField(max_length=30, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    observaciones = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "autorización de ingreso"
        verbose_name_plural = "autorizaciones de ingreso"
        ordering = ["-creada_en"]

    def __str__(self):
        return f"Ingreso {self.contratista.nombre} ({self.fecha_inicio} a {self.fecha_fin})"

    @property
    def vigente(self):
        hoy = timezone.localdate()
        return self.fecha_inicio <= hoy <= self.fecha_fin


class TrabajadorAutorizacionIngreso(models.Model):
    """Una línea de la lista de inclusiones/exclusiones: cada trabajador
    queda explícitamente incluido o excluido del ingreso autorizado, con
    motivo obligatorio cuando queda excluido."""

    autorizacion = models.ForeignKey(AutorizacionIngreso, on_delete=models.CASCADE, related_name="trabajadores")
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name="autorizaciones_ingreso")
    incluido = models.BooleanField(default=True)
    motivo_exclusion = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "trabajador en autorización de ingreso"
        verbose_name_plural = "trabajadores en autorización de ingreso"
        unique_together = [("autorizacion", "trabajador")]
        ordering = ["-incluido", "trabajador__apellidos"]

    def __str__(self):
        return f"{self.trabajador} — {'Incluido' if self.incluido else 'Excluido'}"
