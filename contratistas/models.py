from django.core.validators import FileExtensionValidator
from django.db import models

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


class FirmaMetodo(models.Model):
    """Firma/aprobación de uno de los roles requeridos en la declaración de método."""

    class Rol(models.TextChoices):
        SUPERVISOR_CONTRATISTA = "supervisor_contratista", "Supervisor de Seguridad del Contratista"
        DELEGADO_ABI = "delegado_abi", "Delegado (Contratante)"
        SEGURIDAD_PLANTA = "seguridad_planta", "Seguridad de Planta (Site)"
        LIDER_AREA = "lider_area", "Líder de Área"
        DUENO_TERRITORIO = "dueno_territorio", "Dueño de Territorio"

    declaracion = models.ForeignKey(DeclaracionMetodo, on_delete=models.CASCADE, related_name="firmas")
    rol = models.CharField(max_length=30, choices=Rol.choices)
    nombre_firmante = models.CharField(max_length=150)
    firmado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "firma de declaración de método"
        verbose_name_plural = "firmas de declaración de método"
        unique_together = [("declaracion", "rol")]
        ordering = ["declaracion", "rol"]

    def __str__(self):
        return f"{self.get_rol_display()}: {self.nombre_firmante}"
