from rest_framework import serializers

from core.models import Empresa

from .models import (
    PERMISOS_TRABAJO,
    ActividadMetodo,
    DeclaracionMetodo,
    EmpresaContratista,
    FirmaMetodo,
    RadicacionSeguridadSocial,
    Trabajador,
    nivel_riesgo,
)


class EmpresaContratistaSerializer(serializers.ModelSerializer):
    trabajadores_count = serializers.SerializerMethodField()

    class Meta:
        model = EmpresaContratista
        fields = [
            "id",
            "nombre",
            "nit",
            "contacto_nombre",
            "contacto_telefono",
            "contacto_correo",
            "responsable_sst_nombre",
            "responsable_sst_telefono",
            "activa",
            "creada_en",
            "trabajadores_count",
        ]

    def get_trabajadores_count(self, contratista):
        return contratista.trabajadores.count()


class EmpresaContratistaCrearSerializer(serializers.ModelSerializer):
    """Alta de una empresa contratista. La empresa cliente dueña se asigna sola,
    igual que CamaraCrearSerializer en camaras_ia."""

    class Meta:
        model = EmpresaContratista
        fields = [
            "id",
            "nombre",
            "nit",
            "contacto_nombre",
            "contacto_telefono",
            "contacto_correo",
            "responsable_sst_nombre",
            "responsable_sst_telefono",
            "activa",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        empresa = Empresa.objects.first()
        if empresa is None:
            empresa = Empresa.objects.create(nombre="Empresa")
        return EmpresaContratista.objects.create(empresa=empresa, **validated_data)


class RadicacionResumenSerializer(serializers.ModelSerializer):
    vencida = serializers.BooleanField(read_only=True)
    dias_para_vencer = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = RadicacionSeguridadSocial
        fields = ["id", "anio", "mes", "estado", "fecha_vencimiento", "vencida", "dias_para_vencer"]


class TrabajadorSerializer(serializers.ModelSerializer):
    contratista_nombre = serializers.CharField(source="contratista.nombre", read_only=True)
    ultima_radicacion = serializers.SerializerMethodField()

    class Meta:
        model = Trabajador
        fields = [
            "id",
            "contratista",
            "contratista_nombre",
            "nombres",
            "apellidos",
            "documento",
            "eps",
            "arl",
            "afp",
            "tipo_vinculacion",
            "fecha_inicio_contrato",
            "cursos_safety_academy",
            "activo",
            "creado_en",
            "ultima_radicacion",
        ]

    def get_ultima_radicacion(self, trabajador):
        radicacion = trabajador.radicaciones.order_by("-radicada_en").first()
        if not radicacion:
            return None
        return RadicacionResumenSerializer(radicacion).data


class RadicacionSeguridadSocialSerializer(serializers.ModelSerializer):
    trabajador_nombre = serializers.SerializerMethodField()
    contratista_nombre = serializers.CharField(source="trabajador.contratista.nombre", read_only=True)
    vencida = serializers.BooleanField(read_only=True)
    dias_para_vencer = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = RadicacionSeguridadSocial
        fields = [
            "id",
            "trabajador",
            "trabajador_nombre",
            "contratista_nombre",
            "anio",
            "mes",
            "numero_planilla",
            "fecha_vencimiento",
            "vencida",
            "dias_para_vencer",
            "soporte_pago",
            "interventor",
            "estado",
            "observaciones",
            "radicada_en",
            "revisada_en",
        ]
        read_only_fields = ["id", "radicada_en", "revisada_en"]

    def get_trabajador_nombre(self, radicacion):
        return f"{radicacion.trabajador.apellidos} {radicacion.trabajador.nombres}"


class DecisionRadicacionSerializer(serializers.Serializer):
    """Payload para aprobar/rechazar una radicación."""

    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class FirmaMetodoSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)

    class Meta:
        model = FirmaMetodo
        fields = ["id", "rol", "rol_display", "nombre_firmante", "firmado_en"]
        read_only_fields = ["id", "firmado_en"]


class ActividadMetodoSerializer(serializers.ModelSerializer):
    riesgo_sin = serializers.FloatField(read_only=True)
    riesgo_con = serializers.FloatField(read_only=True)
    nivel_riesgo_sin = serializers.SerializerMethodField()
    nivel_riesgo_con = serializers.SerializerMethodField()

    class Meta:
        model = ActividadMetodo
        fields = [
            "id",
            "orden",
            "secuencia",
            "tecnicas_herramientas",
            "descripcion_riesgo",
            "probabilidad_sin",
            "frecuencia_sin",
            "impacto_sin",
            "riesgo_sin",
            "nivel_riesgo_sin",
            "medidas_mitigacion",
            "probabilidad_con",
            "frecuencia_con",
            "impacto_con",
            "riesgo_con",
            "nivel_riesgo_con",
            "permisos_requeridos",
            "tarea_sif",
        ]
        read_only_fields = ["id"]

    def get_nivel_riesgo_sin(self, actividad):
        clave, etiqueta = nivel_riesgo(actividad.riesgo_sin)
        return {"clave": clave, "etiqueta": etiqueta}

    def get_nivel_riesgo_con(self, actividad):
        clave, etiqueta = nivel_riesgo(actividad.riesgo_con)
        return {"clave": clave, "etiqueta": etiqueta}


class DeclaracionMetodoSerializer(serializers.ModelSerializer):
    """Declaración completa, con sus actividades escribibles de forma anidada
    (se reemplazan todas en cada guardado — más simple y predecible para un
    formulario dinámico de N filas que se editan siempre en conjunto) y sus
    firmas de solo lectura (se agregan con el endpoint dedicado /firmar/)."""

    contratista_nombre = serializers.CharField(source="contratista.nombre", read_only=True)
    actividades = ActividadMetodoSerializer(many=True, required=False)
    firmas = FirmaMetodoSerializer(many=True, read_only=True)

    class Meta:
        model = DeclaracionMetodo
        fields = [
            "id",
            "contratista",
            "contratista_nombre",
            "planta_area",
            "numero_pedido",
            "gerente_proyecto",
            "contacto_nombre",
            "contacto_telefono",
            "fecha_elaboracion",
            "duracion_dias",
            "descripcion_trabajo",
            "estado",
            "observaciones",
            "creada_en",
            "actualizada_en",
            "actividades",
            "firmas",
        ]
        read_only_fields = ["id", "creada_en", "actualizada_en"]

    def validate(self, datos):
        if datos.get("estado") == DeclaracionMetodo.Estado.APROBADA:
            tiene_firmas = self.instance is not None and self.instance.firmas.exists()
            if not tiene_firmas:
                raise serializers.ValidationError(
                    {"estado": "No se puede aprobar sin al menos una firma registrada."}
                )
        return datos

    def create(self, validated_data):
        actividades_data = validated_data.pop("actividades", [])
        declaracion = DeclaracionMetodo.objects.create(**validated_data)
        self._guardar_actividades(declaracion, actividades_data)
        return declaracion

    def update(self, instance, validated_data):
        actividades_data = validated_data.pop("actividades", None)
        for atributo, valor in validated_data.items():
            setattr(instance, atributo, valor)
        instance.save()
        if actividades_data is not None:
            instance.actividades.all().delete()
            self._guardar_actividades(instance, actividades_data)
        return instance

    def _guardar_actividades(self, declaracion, actividades_data):
        for indice, actividad in enumerate(actividades_data):
            actividad.pop("id", None)
            actividad.setdefault("orden", indice)
            ActividadMetodo.objects.create(declaracion=declaracion, **actividad)


class CatalogosSerializer(serializers.Serializer):
    """Listas fijas que el frontend necesita para armar los formularios,
    centralizadas acá para no duplicarlas en el cliente."""

    cursos_safety_academy = serializers.SerializerMethodField()
    permisos_trabajo = serializers.SerializerMethodField()
    roles_firma = serializers.SerializerMethodField()

    def get_cursos_safety_academy(self, obj):
        return [{"clave": clave, "etiqueta": etiqueta} for clave, etiqueta in Trabajador.CURSOS.items()]

    def get_permisos_trabajo(self, obj):
        return PERMISOS_TRABAJO

    def get_roles_firma(self, obj):
        return [{"clave": clave, "etiqueta": etiqueta} for clave, etiqueta in FirmaMetodo.Rol.choices]
