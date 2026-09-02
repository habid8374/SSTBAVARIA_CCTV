from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from contratistas.models import EmpresaContratista

from .models import PerfilUsuario, SuscripcionPush

Usuario = get_user_model()


def _validar_contratista_segun_rol(datos):
    """El campo contratista solo tiene sentido para el rol Contratista — se
    exige si se elige ese rol, y se limpia si se elige cualquier otro."""
    rol = datos.get("rol")
    contratista = datos.get("contratista")
    if rol == PerfilUsuario.Rol.CONTRATISTA and contratista is None:
        raise serializers.ValidationError(
            {"contratista": "Hay que elegir la empresa contratista para este usuario."}
        )
    if rol != PerfilUsuario.Rol.CONTRATISTA:
        datos["contratista"] = None
    return datos


class UsuarioSerializer(serializers.ModelSerializer):
    """Lectura y edición (rol, activo, nombre) de un usuario existente."""

    rol = serializers.ChoiceField(source="perfil.rol", choices=PerfilUsuario.Rol.choices)
    contratista = serializers.PrimaryKeyRelatedField(
        source="perfil.contratista", queryset=EmpresaContratista.objects.all(), required=False, allow_null=True
    )
    contratista_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "rol",
            "contratista",
            "contratista_nombre",
            "date_joined",
        ]
        read_only_fields = ["id", "username", "date_joined"]

    def get_contratista_nombre(self, usuario):
        perfil = getattr(usuario, "perfil", None)
        return perfil.contratista.nombre if perfil and perfil.contratista else None

    def validate(self, datos):
        perfil_data = datos.get("perfil")
        if perfil_data:
            rol = perfil_data.get("rol", getattr(self.instance.perfil, "rol", None) if self.instance else None)
            perfil_data = _validar_contratista_segun_rol({**perfil_data, "rol": rol})
            datos["perfil"] = perfil_data
        return datos

    def update(self, instance, validated_data):
        perfil_data = validated_data.pop("perfil", None)
        instance = super().update(instance, validated_data)
        if perfil_data:
            if "rol" in perfil_data:
                instance.perfil.rol = perfil_data["rol"]
            if "contratista" in perfil_data:
                instance.perfil.contratista = perfil_data["contratista"]
            instance.perfil.save(update_fields=["rol", "contratista"])
        return instance


class UsuarioCrearSerializer(serializers.ModelSerializer):
    """Alta de un usuario nuevo del dashboard, con su rol inicial."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    rol = serializers.ChoiceField(choices=PerfilUsuario.Rol.choices, default=PerfilUsuario.Rol.OPERADOR)
    contratista = serializers.PrimaryKeyRelatedField(
        queryset=EmpresaContratista.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Usuario
        fields = ["id", "username", "first_name", "last_name", "email", "password", "rol", "contratista"]
        read_only_fields = ["id"]

    def validate(self, datos):
        return _validar_contratista_segun_rol(datos)

    def create(self, validated_data):
        rol = validated_data.pop("rol")
        contratista = validated_data.pop("contratista", None)
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        user.perfil.rol = rol
        user.perfil.contratista = contratista
        user.perfil.save(update_fields=["rol", "contratista"])
        return user


class SuscripcionPushSerializer(serializers.Serializer):
    """Lo que manda el navegador al suscribirse (PushSubscription.toJSON()) —
    no es un ModelSerializer porque `usuario` se asigna en la vista, nunca
    lo elige el cliente."""

    endpoint = serializers.URLField(max_length=500)
    keys = serializers.DictField(child=serializers.CharField())

    def validate_keys(self, keys):
        faltantes = {"p256dh", "auth"} - set(keys)
        if faltantes:
            raise serializers.ValidationError(f"Faltan las llaves: {', '.join(sorted(faltantes))}.")
        return keys
