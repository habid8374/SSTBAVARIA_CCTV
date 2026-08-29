from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import PerfilUsuario

Usuario = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    """Lectura y edición (rol, activo, nombre) de un usuario existente."""

    rol = serializers.ChoiceField(source="perfil.rol", choices=PerfilUsuario.Rol.choices)

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
            "date_joined",
        ]
        read_only_fields = ["id", "username", "date_joined"]

    def update(self, instance, validated_data):
        perfil_data = validated_data.pop("perfil", None)
        instance = super().update(instance, validated_data)
        if perfil_data:
            instance.perfil.rol = perfil_data["rol"]
            instance.perfil.save(update_fields=["rol"])
        return instance


class UsuarioCrearSerializer(serializers.ModelSerializer):
    """Alta de un usuario nuevo del dashboard, con su rol inicial."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    rol = serializers.ChoiceField(choices=PerfilUsuario.Rol.choices, default=PerfilUsuario.Rol.OPERADOR)

    class Meta:
        model = Usuario
        fields = ["id", "username", "first_name", "last_name", "email", "password", "rol"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        rol = validated_data.pop("rol")
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        user.perfil.rol = rol
        user.perfil.save(update_fields=["rol"])
        return user
