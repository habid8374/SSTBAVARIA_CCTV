import datetime

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa

from .models import (
    ActividadMetodo,
    DeclaracionMetodo,
    EmpresaContratista,
    FirmaMetodo,
    RadicacionSeguridadSocial,
    Trabajador,
    nivel_riesgo,
)

Usuario = get_user_model()


class NivelRiesgoTests(TestCase):
    def test_muy_alto(self):
        clave, _ = nivel_riesgo(450)
        self.assertEqual(clave, "muy_alto")

    def test_alto(self):
        clave, _ = nivel_riesgo(300)
        self.assertEqual(clave, "alto")

    def test_considerable(self):
        clave, _ = nivel_riesgo(100)
        self.assertEqual(clave, "considerable")

    def test_posible(self):
        clave, _ = nivel_riesgo(50)
        self.assertEqual(clave, "posible")

    def test_bajo(self):
        clave, _ = nivel_riesgo(9)
        self.assertEqual(clave, "bajo")


class ActividadMetodoCalculoTests(TestCase):
    def test_riesgo_es_producto_p_f_i(self):
        actividad = ActividadMetodo(
            probabilidad_sin=6, frecuencia_sin=3, impacto_sin=3,
            probabilidad_con=1, frecuencia_con=3, impacto_con=1,
        )
        self.assertEqual(actividad.riesgo_sin, 54)
        self.assertEqual(actividad.riesgo_con, 3)


class ApiTestsBase(TestCase):
    def setUp(self):
        # El throttle de login cuenta por IP y el test client siempre usa la
        # misma — sin esto, los _token() de tests anteriores se acumularían.
        cache.clear()
        self.empresa = Empresa.objects.create(nombre="Bavaria Planta")
        self.admin = Usuario.objects.create_superuser("admin", "admin@x.com", "clave12345")
        self.operador = Usuario.objects.create_user("operador1", "op@x.com", "clave12345")
        self.contratista = EmpresaContratista.objects.create(
            empresa=self.empresa, nombre="SCEPSA COLOMBIA SAS", nit="900588170-2"
        )
        self.trabajador = Trabajador.objects.create(
            contratista=self.contratista,
            nombres="Gerald Marcelo",
            apellidos="Garzón Beltrán",
            documento="80432071",
            eps="Nueva EPS",
            arl="Positiva",
            afp="Protección",
        )

    def _token(self, user):
        response = self.client.post(
            reverse("core:login"),
            {"username": user.username, "password": "clave12345"},
            content_type="application/json",
        )
        return response.data["token"]

    def _auth(self, user):
        return {"HTTP_AUTHORIZATION": f"Token {self._token(user)}"}


class CatalogosTests(ApiTestsBase):
    def test_catalogos_requiere_autenticacion(self):
        response = self.client.get(reverse("contratistas:catalogos"))
        self.assertEqual(response.status_code, 401)

    def test_catalogos_devuelve_listas(self):
        response = self.client.get(reverse("contratistas:catalogos"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["cursos_safety_academy"]), 7)
        self.assertIn("Trabajos en Altura > 1.8 m", response.data["permisos_trabajo"])
        self.assertEqual(len(response.data["roles_firma"]), 5)


class EmpresaContratistaTests(ApiTestsBase):
    def test_lista(self):
        response = self.client.get(reverse("contratistas:empresas_lista"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["trabajadores_count"], 1)

    def test_crear(self):
        response = self.client.post(
            reverse("contratistas:empresas_lista"),
            {"nombre": "Gestión y Control Integral del Riesgo SAS", "nit": "900123456-1"},
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(EmpresaContratista.objects.count(), 2)

    def test_operador_no_puede_eliminar_empresa(self):
        url = reverse("contratistas:empresas_detalle", args=[self.contratista.pk])
        response = self.client.delete(url, **self._auth(self.operador))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(EmpresaContratista.objects.filter(pk=self.contratista.pk).exists())

    def test_admin_puede_eliminar_empresa(self):
        url = reverse("contratistas:empresas_detalle", args=[self.contratista.pk])
        response = self.client.delete(url, **self._auth(self.admin))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(EmpresaContratista.objects.filter(pk=self.contratista.pk).exists())


class TrabajadorTests(ApiTestsBase):
    def test_crear_trabajador(self):
        response = self.client.post(
            reverse("contratistas:trabajadores_lista"),
            {
                "contratista": self.contratista.pk,
                "nombres": "Luis Alfonso",
                "apellidos": "Estepa Patiño",
                "documento": "80431911",
                "cursos_safety_academy": {"induccion_sst": "2026-08-01"},
            },
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Trabajador.objects.count(), 2)

    def test_filtro_por_contratista(self):
        otro_contratista = EmpresaContratista.objects.create(empresa=self.empresa, nombre="Otra SAS")
        Trabajador.objects.create(
            contratista=otro_contratista, nombres="X", apellidos="Y", documento="1"
        )
        response = self.client.get(
            reverse("contratistas:trabajadores_lista"),
            {"contratista": self.contratista.pk},
            **self._auth(self.operador),
        )
        self.assertEqual(len(response.data), 1)


class RadicacionSeguridadSocialTests(ApiTestsBase):
    def test_radicar_y_aprobar(self):
        response = self.client.post(
            reverse("contratistas:radicaciones_lista"),
            {
                "trabajador": self.trabajador.pk,
                "anio": 2026,
                "mes": "AGOSTO",
                "numero_planilla": "94075251",
                "fecha_vencimiento": "2026-09-19",
            },
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 201)
        radicacion_id = response.data["id"]
        self.assertEqual(response.data["estado"], "pendiente")

        response = self.client.post(
            reverse("contratistas:radicaciones_aprobar", args=[radicacion_id]),
            {"observaciones": "Todo en orden"},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["estado"], "aprobada")
        radicacion = RadicacionSeguridadSocial.objects.get(pk=radicacion_id)
        self.assertIsNotNone(radicacion.revisada_en)

    def test_rechazar(self):
        radicacion = RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador, anio=2026, mes="AGOSTO"
        )
        response = self.client.post(
            reverse("contratistas:radicaciones_rechazar", args=[radicacion.pk]),
            {"observaciones": "Planilla vencida"},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["estado"], "rechazada")

    def test_requiere_autenticacion(self):
        response = self.client.get(reverse("contratistas:radicaciones_lista"))
        self.assertEqual(response.status_code, 401)

    def test_rechaza_extension_de_archivo_no_permitida(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        archivo = SimpleUploadedFile("malware.exe", b"MZ contenido falso", content_type="application/octet-stream")
        response = self.client.post(
            reverse("contratistas:radicaciones_lista"),
            {"trabajador": self.trabajador.pk, "anio": 2026, "mes": "AGOSTO", "soporte_pago": archivo},
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("soporte_pago", response.data)

    def test_solo_admin_puede_eliminar_radicacion(self):
        radicacion = RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador, anio=2026, mes="AGOSTO"
        )
        url = reverse("contratistas:radicaciones_detalle", args=[radicacion.pk])

        respuesta_operador = self.client.delete(url, **self._auth(self.operador))
        self.assertEqual(respuesta_operador.status_code, 403)

        respuesta_admin = self.client.delete(url, **self._auth(self.admin))
        self.assertEqual(respuesta_admin.status_code, 204)


class DeclaracionMetodoTests(ApiTestsBase):
    def test_crear_con_actividades_anidadas(self):
        payload = {
            "contratista": self.contratista.pk,
            "planta_area": "Cervecería Tocancipá - Tapas",
            "fecha_elaboracion": "2026-07-11",
            "duracion_dias": 30,
            "descripcion_trabajo": "Instalación de polipasto / tecle",
            "actividades": [
                {
                    "orden": 0,
                    "secuencia": "1. Ingreso y salida a planta",
                    "probabilidad_sin": 6,
                    "frecuencia_sin": 3,
                    "impacto_sin": 3,
                    "medidas_mitigacion": "Uso de senderos peatonales",
                    "probabilidad_con": 3,
                    "frecuencia_con": 3,
                    "impacto_con": 1,
                    "permisos_requeridos": ["Trabajos en Altura > 1.8 m"],
                    "tarea_sif": True,
                },
                {
                    "orden": 1,
                    "secuencia": "2. Inducción por el cliente",
                    "probabilidad_sin": 6,
                    "frecuencia_sin": 2,
                    "impacto_sin": 3,
                },
            ],
        }
        response = self.client.post(
            reverse("contratistas:declaraciones_lista"),
            payload,
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 201, response.data)
        declaracion_id = response.data["id"]
        self.assertEqual(len(response.data["actividades"]), 2)
        self.assertEqual(response.data["actividades"][0]["riesgo_sin"], 54)
        self.assertEqual(response.data["actividades"][0]["nivel_riesgo_sin"]["clave"], "posible")

        declaracion = DeclaracionMetodo.objects.get(pk=declaracion_id)
        self.assertEqual(declaracion.actividades.count(), 2)

    def test_editar_reemplaza_actividades(self):
        declaracion = DeclaracionMetodo.objects.create(
            contratista=self.contratista,
            fecha_elaboracion=datetime.date(2026, 7, 11),
            descripcion_trabajo="Instalación de pórtico",
        )
        ActividadMetodo.objects.create(declaracion=declaracion, orden=0, secuencia="Actividad vieja")

        response = self.client.patch(
            reverse("contratistas:declaraciones_detalle", args=[declaracion.pk]),
            {"actividades": [{"orden": 0, "secuencia": "Actividad nueva"}]},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 200, response.data)
        declaracion.refresh_from_db()
        self.assertEqual(declaracion.actividades.count(), 1)
        self.assertEqual(declaracion.actividades.first().secuencia, "Actividad nueva")

    def test_firmar_declaracion(self):
        declaracion = DeclaracionMetodo.objects.create(
            contratista=self.contratista,
            fecha_elaboracion=datetime.date(2026, 7, 11),
            descripcion_trabajo="Instalación de pórtico",
        )
        response = self.client.post(
            reverse("contratistas:declaraciones_firmar", args=[declaracion.pk]),
            {"rol": "supervisor_contratista", "nombre_firmante": "Andres Felipe Lujan"},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(FirmaMetodo.objects.count(), 1)

        # Firmar de nuevo el mismo rol reemplaza en vez de duplicar.
        response = self.client.post(
            reverse("contratistas:declaraciones_firmar", args=[declaracion.pk]),
            {"rol": "supervisor_contratista", "nombre_firmante": "Otro Nombre"},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(FirmaMetodo.objects.count(), 1)
        self.assertEqual(FirmaMetodo.objects.first().nombre_firmante, "Otro Nombre")
