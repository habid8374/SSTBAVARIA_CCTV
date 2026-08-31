import secrets

from django.db import models

from core.models import Empresa
from core.validators import validar_tamano_archivo


def generar_api_key():
    return secrets.token_hex(20)


class Camara(models.Model):
    """Una cámara PTZ física registrada en sitio."""

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="camaras")
    nombre = models.CharField(max_length=150)
    ip = models.GenericIPAddressField("dirección IP")
    puerto_onvif = models.PositiveIntegerField("puerto ONVIF", default=80)
    usuario_onvif = models.CharField("usuario ONVIF", max_length=100, blank=True)
    password_onvif = models.CharField("contraseña ONVIF", max_length=100, blank=True)
    rtsp_url = models.CharField(
        "URL RTSP",
        max_length=500,
        blank=True,
        help_text=(
            "URL completa del stream RTSP (con usuario/contraseña si aplica). "
            "Si se deja vacío, el equipo local usa el patrón estándar de Dahua "
            "con la IP y las credenciales ONVIF de arriba — ver Camara.rtsp_url_efectiva."
        ),
    )
    ubicacion = models.CharField(max_length=255, blank=True, help_text="Descripción del punto donde está instalada")
    snapshot_referencia = models.ImageField(
        "snapshot de referencia",
        upload_to="camaras/referencia",
        null=True,
        blank=True,
        validators=[validar_tamano_archivo],
        help_text="Encuadre fijo de la cámara sobre el que se dibujan las zonas restringidas",
    )
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "cámara"
        verbose_name_plural = "cámaras"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.ip})"

    @property
    def rtsp_url_efectiva(self):
        """URL RTSP a usar por el equipo local: la explícita si se configuró,
        o si no el patrón estándar de Dahua (confirmado por investigación de
        hardware — ver CLAUDE_CAMARAS.md) con la IP y credenciales ONVIF.
        subtype=1 (substream) por defecto: menor resolución/bitrate, más
        liviano para detección en tiempo real que el canal principal."""
        if self.rtsp_url:
            return self.rtsp_url
        credenciales = f"{self.usuario_onvif}:{self.password_onvif}@" if self.usuario_onvif else ""
        return f"rtsp://{credenciales}{self.ip}:554/cam/realmonitor?channel=1&subtype=1"


class EquipoLocal(models.Model):
    """Mini-PC/equipo en sitio que reporta eventos. Se autentica con API key propia."""

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="equipos_locales")
    nombre = models.CharField(max_length=150)
    api_key = models.CharField(max_length=64, unique=True, default=generar_api_key, editable=False)
    activo = models.BooleanField(default=True)
    ultima_conexion = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "equipo local"
        verbose_name_plural = "equipos locales"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ZonaRestringida(models.Model):
    """Polígono sobre el encuadre de una cámara donde no debería haber personas."""

    camara = models.ForeignKey(Camara, on_delete=models.CASCADE, related_name="zonas")
    nombre = models.CharField(max_length=150)
    poligono = models.JSONField(
        "polígono",
        help_text="Lista de coordenadas [[x1, y1], [x2, y2], ...] sobre el encuadre de referencia",
    )
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "zona restringida"
        verbose_name_plural = "zonas restringidas"
        ordering = ["camara", "nombre"]

    def __str__(self):
        return f"{self.nombre} — {self.camara.nombre}"


class ReglaAlerta(models.Model):
    """Horario en el que una zona restringida dispara alerta, y a quién avisar."""

    class Canal(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        CORREO = "correo", "Correo"

    class Dia(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    zona = models.ForeignKey(ZonaRestringida, on_delete=models.CASCADE, related_name="reglas")
    nombre = models.CharField(max_length=150, blank=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    dias_semana = models.JSONField(
        "días de la semana",
        default=list,
        help_text="Lista de días activos, 0=Lunes ... 6=Domingo",
    )
    canal_notificacion = models.CharField(max_length=20, choices=Canal.choices, default=Canal.WHATSAPP)
    destinatario = models.CharField(max_length=150, help_text="Número de WhatsApp o correo del destinatario")
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "regla de alerta"
        verbose_name_plural = "reglas de alerta"
        ordering = ["zona", "hora_inicio"]

    def __str__(self):
        return self.nombre or f"Regla de {self.zona.nombre}"


def snapshot_upload_to(instance, filename):
    return f"eventos/{instance.camara_id}/{filename}"


class EventoDetectado(models.Model):
    """Evento puntual reportado por el equipo local: una foto, no video."""

    class Estado(models.TextChoices):
        NUEVO = "nuevo", "Nuevo"
        REVISADO = "revisado", "Revisado"

    camara = models.ForeignKey(Camara, on_delete=models.CASCADE, related_name="eventos")
    zona = models.ForeignKey(
        ZonaRestringida, on_delete=models.SET_NULL, related_name="eventos", null=True, blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    snapshot = models.ImageField(
        upload_to=snapshot_upload_to, null=True, blank=True, validators=[validar_tamano_archivo]
    )
    punto_x = models.FloatField(
        "punto detectado (x)",
        null=True,
        blank=True,
        help_text="Coordenada del punto reportado por el equipo local, mismo sistema que el polígono de la zona",
    )
    punto_y = models.FloatField("punto detectado (y)", null=True, blank=True)
    disparo_alerta = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.NUEVO)
    canal_notificacion = models.CharField(
        "canal de notificación",
        max_length=20,
        choices=ReglaAlerta.Canal.choices,
        blank=True,
        help_text="Canal de la regla que disparó la alerta — vacío si no hubo disparo_alerta",
    )
    notificacion_enviada = models.BooleanField(
        "notificación enviada",
        default=False,
        help_text="True si disparar_alerta logró enviar la notificación (hoy solo canal correo, vía Brevo)",
    )
    notificacion_detalle = models.CharField(
        "detalle de la notificación", max_length=255, blank=True
    )

    class Meta:
        verbose_name = "evento detectado"
        verbose_name_plural = "eventos detectados"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.camara.nombre} — {self.timestamp:%Y-%m-%d %H:%M}"
