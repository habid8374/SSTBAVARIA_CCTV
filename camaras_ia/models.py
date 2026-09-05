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

    # Calibración para zonas tipo "punto y radio" (ver ZonaRestringida.Tipo):
    # dos puntos marcados sobre el snapshot de referencia y la distancia real
    # (en metros) entre ellos — de ahí sale Camara.px_por_metro. Es una escala
    # constante, no una homografía completa de perspectiva: suficiente para
    # una zona acotada cerca de esos puntos, pierde precisión lejos de ellos
    # si la cámara tiene mucho ángulo/inclinación.
    calibracion_punto1_x = models.FloatField("calibración: punto 1 (x)", null=True, blank=True)
    calibracion_punto1_y = models.FloatField("calibración: punto 1 (y)", null=True, blank=True)
    calibracion_punto2_x = models.FloatField("calibración: punto 2 (x)", null=True, blank=True)
    calibracion_punto2_y = models.FloatField("calibración: punto 2 (y)", null=True, blank=True)
    calibracion_distancia_metros = models.FloatField(
        "calibración: distancia real (m)",
        null=True,
        blank=True,
        help_text="Distancia real, en metros, entre los dos puntos de calibración marcados sobre el snapshot",
    )

    class Meta:
        verbose_name = "cámara"
        verbose_name_plural = "cámaras"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.ip})"

    @property
    def px_por_metro(self):
        """Escala de la cámara (píxeles por metro real), o None si no está
        calibrada. Ver evaluar_zona_horario/ZonaRestringida.Tipo.PUNTO_RADIO."""
        campos = (
            self.calibracion_punto1_x,
            self.calibracion_punto1_y,
            self.calibracion_punto2_x,
            self.calibracion_punto2_y,
            self.calibracion_distancia_metros,
        )
        if any(c is None for c in campos):
            return None
        if self.calibracion_distancia_metros <= 0:
            return None
        dx = self.calibracion_punto2_x - self.calibracion_punto1_x
        dy = self.calibracion_punto2_y - self.calibracion_punto1_y
        distancia_px = (dx**2 + dy**2) ** 0.5
        if distancia_px <= 0:
            return None
        return distancia_px / self.calibracion_distancia_metros

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


class ConfiguracionNotificaciones(models.Model):
    """Fila única (singleton) con las credenciales de Brevo, editables desde
    el dashboard (sección Sistema) en vez de solo por variable de entorno —
    así el cliente no depende de que alguien le toque Railway para
    activar/cambiar el envío de correos de alerta. Si queda vacío, se usa el
    fallback de settings.BREVO_* (ver camaras_ia/notificaciones.py)."""

    brevo_api_key = models.CharField("Brevo API key", max_length=255, blank=True)
    brevo_remitente_email = models.EmailField("correo remitente", blank=True)
    brevo_remitente_nombre = models.CharField("nombre remitente", max_length=150, blank=True)
    actualizada_en = models.DateTimeField("actualizada en", auto_now=True)

    class Meta:
        verbose_name = "configuración de notificaciones"
        verbose_name_plural = "configuración de notificaciones"

    def __str__(self):
        return "Configuración de notificaciones"

    @classmethod
    def obtener(cls):
        objeto, _ = cls.objects.get_or_create(pk=1)
        return objeto


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
    """Área sobre el encuadre de una cámara donde no debería haber personas —
    un polígono dibujado a mano, o un punto marcado (ej. una estiba) más un
    radio en metros reales (requiere que la cámara esté calibrada, ver
    Camara.px_por_metro) para zonas que se deben recalcular si ese punto se
    mueve, sin tener que redibujar nada."""

    class Tipo(models.TextChoices):
        POLIGONO = "poligono", "Polígono"
        PUNTO_RADIO = "punto_radio", "Punto y radio"

    camara = models.ForeignKey(Camara, on_delete=models.CASCADE, related_name="zonas")
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.POLIGONO)
    poligono = models.JSONField(
        "polígono",
        blank=True,
        default=list,
        help_text="Lista de coordenadas [[x1, y1], [x2, y2], ...] sobre el encuadre de referencia — solo para tipo Polígono",
    )
    centro_x = models.FloatField(
        "centro (x)",
        null=True,
        blank=True,
        help_text="Punto marcado (ej. una estiba) sobre el encuadre de referencia — solo para tipo Punto y radio",
    )
    centro_y = models.FloatField("centro (y)", null=True, blank=True)
    radio_metros = models.FloatField(
        "radio (metros)",
        null=True,
        blank=True,
        help_text="Distancia real, en metros, alrededor del centro que se considera zona restringida — solo para tipo Punto y radio",
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
