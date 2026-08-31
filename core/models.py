from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Empresa(models.Model):
    """Tenant: la empresa cliente dueña de las cámaras y reglas."""

    nombre = models.CharField(max_length=200)
    nit = models.CharField("NIT", max_length=30, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    contacto_nombre = models.CharField("nombre de contacto", max_length=150, blank=True)
    contacto_telefono = models.CharField("teléfono de contacto", max_length=30, blank=True)
    contacto_correo = models.EmailField("correo de contacto", blank=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class PerfilUsuario(models.Model):
    """Rol de un usuario del dashboard. Complementa al User de Django."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        OPERADOR = "operador", "Operador"
        CONTRATISTA = "contratista", "Contratista"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.OPERADOR)
    contratista = models.ForeignKey(
        "contratistas.EmpresaContratista",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios_portal",
        help_text="Solo aplica para el rol Contratista: la empresa a la que representa este usuario "
        "en el portal — define qué datos puede ver y editar.",
    )

    class Meta:
        verbose_name = "perfil de usuario"
        verbose_name_plural = "perfiles de usuario"

    def __str__(self):
        return f"{self.usuario.username} ({self.get_rol_display()})"

    @property
    def es_interno(self):
        """Personal de SST/interventoría — Administrador u Operador, nunca Contratista."""
        return self.rol in (self.Rol.ADMINISTRADOR, self.Rol.OPERADOR)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """Todo usuario nuevo recibe un perfil automáticamente: Administrador si
    se creó como superusuario (ej. createsuperuser), Operador en cualquier
    otro caso — se puede cambiar después desde la gestión de usuarios."""
    if created:
        PerfilUsuario.objects.get_or_create(
            usuario=instance,
            defaults={
                "rol": PerfilUsuario.Rol.ADMINISTRADOR
                if instance.is_superuser
                else PerfilUsuario.Rol.OPERADOR
            },
        )
