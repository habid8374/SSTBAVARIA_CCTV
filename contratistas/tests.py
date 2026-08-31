import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

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


class RadicacionVencimientoTests(TestCase):
    def setUp(self):
        empresa = Empresa.objects.create(nombre="Bavaria Planta")
        contratista = EmpresaContratista.objects.create(empresa=empresa, nombre="SCEPSA")
        self.trabajador = Trabajador.objects.create(
            contratista=contratista, nombres="Ana", apellidos="Ríos", documento="123"
        )

    def test_vencida_true_si_la_fecha_ya_paso(self):
        radicacion = RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            mes="ENERO",
            fecha_vencimiento=timezone.localdate() - datetime.timedelta(days=1),
        )
        self.assertTrue(radicacion.vencida)
        self.assertEqual(radicacion.dias_para_vencer, -1)

    def test_vencida_false_si_la_fecha_es_futura(self):
        radicacion = RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            mes="ENERO",
            fecha_vencimiento=timezone.localdate() + datetime.timedelta(days=5),
        )
        self.assertFalse(radicacion.vencida)
        self.assertEqual(radicacion.dias_para_vencer, 5)

    def test_sin_fecha_de_vencimiento_no_esta_vencida_ni_tiene_dias(self):
        radicacion = RadicacionSeguridadSocial.objects.create(trabajador=self.trabajador, anio=2026, mes="ENERO")
        self.assertFalse(radicacion.vencida)
        self.assertIsNone(radicacion.dias_para_vencer)


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


class IndicadoresTests(ApiTestsBase):
    def test_cuenta_vencidas_y_por_vencer(self):
        RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            mes="ENERO",
            fecha_vencimiento=timezone.localdate() - datetime.timedelta(days=1),
        )
        RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            mes="FEBRERO",
            fecha_vencimiento=timezone.localdate() + datetime.timedelta(days=5),
        )
        RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            mes="MARZO",
            fecha_vencimiento=timezone.localdate() + datetime.timedelta(days=60),
        )

        response = self.client.get(reverse("contratistas:indicadores"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["radicaciones_vencidas"], 1)
        self.assertEqual(response.data["radicaciones_por_vencer"], 1)

    def test_excluye_rechazadas(self):
        RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            mes="ENERO",
            fecha_vencimiento=timezone.localdate() - datetime.timedelta(days=1),
            estado="rechazada",
        )
        response = self.client.get(reverse("contratistas:indicadores"), **self._auth(self.operador))
        self.assertEqual(response.data["radicaciones_vencidas"], 0)

    def test_requiere_autenticacion(self):
        response = self.client.get(reverse("contratistas:indicadores"))
        self.assertEqual(response.status_code, 401)


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

    def test_rechazar_sin_observaciones_devuelve_400(self):
        radicacion = RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador, anio=2026, mes="AGOSTO"
        )
        response = self.client.post(
            reverse("contratistas:radicaciones_rechazar", args=[radicacion.pk]),
            {},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 400)
        radicacion.refresh_from_db()
        self.assertEqual(radicacion.estado, "pendiente")

    def test_aprobar_no_exige_observaciones(self):
        radicacion = RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador, anio=2026, mes="AGOSTO"
        )
        response = self.client.post(
            reverse("contratistas:radicaciones_aprobar", args=[radicacion.pk]),
            {},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 200, response.data)

    @override_settings(BREVO_API_KEY="clave-de-prueba")
    @patch("camaras_ia.notificaciones.urllib.request.urlopen")
    def test_aprobar_notifica_al_correo_de_contacto(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.status = 201
        self.contratista.contacto_correo = "contacto@contratista.com"
        self.contratista.save()
        radicacion = RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador, anio=2026, mes="AGOSTO"
        )
        response = self.client.post(
            reverse("contratistas:radicaciones_aprobar", args=[radicacion.pk]),
            {"observaciones": "Todo en orden"},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 200)
        mock_urlopen.assert_called_once()

    @patch("camaras_ia.notificaciones.urllib.request.urlopen")
    def test_sin_correo_de_contacto_no_intenta_notificar(self, mock_urlopen):
        radicacion = RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador, anio=2026, mes="AGOSTO"
        )
        response = self.client.post(
            reverse("contratistas:radicaciones_aprobar", args=[radicacion.pk]),
            {"observaciones": "Todo en orden"},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 200)
        mock_urlopen.assert_not_called()

    def test_filtra_por_vencida(self):
        RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            mes="ENERO",
            fecha_vencimiento=timezone.localdate() - datetime.timedelta(days=1),
        )
        RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            mes="FEBRERO",
            fecha_vencimiento=timezone.localdate() + datetime.timedelta(days=10),
        )

        response = self.client.get(
            reverse("contratistas:radicaciones_lista"), {"vencida": "true"}, **self._auth(self.operador)
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["mes"], "ENERO")

    def test_exportar_devuelve_xlsx_con_las_filas(self):
        import openpyxl
        from io import BytesIO

        RadicacionSeguridadSocial.objects.create(
            trabajador=self.trabajador, anio=2026, mes="AGOSTO", numero_planilla="94075251"
        )
        response = self.client.get(reverse("contratistas:radicaciones_exportar"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        libro = openpyxl.load_workbook(BytesIO(response.content))
        hoja = libro.active
        filas = list(hoja.iter_rows(values_only=True))
        self.assertEqual(filas[0][0], "Contratista")  # encabezado
        self.assertIn("94075251", filas[1])

    def test_exportar_respeta_filtro_de_contratista(self):
        from io import BytesIO

        import openpyxl

        otro_contratista = EmpresaContratista.objects.create(empresa=self.empresa, nombre="Otra SAS")
        otro_trabajador = Trabajador.objects.create(
            contratista=otro_contratista, nombres="X", apellidos="Y", documento="999"
        )
        RadicacionSeguridadSocial.objects.create(trabajador=self.trabajador, anio=2026, mes="AGOSTO")
        RadicacionSeguridadSocial.objects.create(trabajador=otro_trabajador, anio=2026, mes="AGOSTO")

        response = self.client.get(
            reverse("contratistas:radicaciones_exportar"),
            {"contratista": self.contratista.pk},
            **self._auth(self.operador),
        )
        libro = openpyxl.load_workbook(BytesIO(response.content))
        filas = list(libro.active.iter_rows(values_only=True))
        self.assertEqual(len(filas), 2)  # encabezado + 1 fila

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

    def test_aprobar_declaracion_sin_firmas_devuelve_400(self):
        declaracion = DeclaracionMetodo.objects.create(
            contratista=self.contratista,
            fecha_elaboracion=datetime.date(2026, 7, 11),
            descripcion_trabajo="Instalación de pórtico",
        )
        response = self.client.patch(
            reverse("contratistas:declaraciones_detalle", args=[declaracion.pk]),
            {"estado": "aprobada"},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 400)
        declaracion.refresh_from_db()
        self.assertEqual(declaracion.estado, "borrador")

    def test_aprobar_declaracion_con_firma_permite(self):
        declaracion = DeclaracionMetodo.objects.create(
            contratista=self.contratista,
            fecha_elaboracion=datetime.date(2026, 7, 11),
            descripcion_trabajo="Instalación de pórtico",
        )
        FirmaMetodo.objects.create(declaracion=declaracion, rol="supervisor_contratista", nombre_firmante="Ana")
        response = self.client.patch(
            reverse("contratistas:declaraciones_detalle", args=[declaracion.pk]),
            {"estado": "aprobada"},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["estado"], "aprobada")

    @override_settings(BREVO_API_KEY="clave-de-prueba")
    @patch("camaras_ia.notificaciones.urllib.request.urlopen")
    def test_aprobar_declaracion_notifica_al_contratista(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.status = 201
        self.contratista.contacto_correo = "contacto@contratista.com"
        self.contratista.save()
        declaracion = DeclaracionMetodo.objects.create(
            contratista=self.contratista,
            fecha_elaboracion=datetime.date(2026, 7, 11),
            descripcion_trabajo="Instalación de pórtico",
        )
        FirmaMetodo.objects.create(declaracion=declaracion, rol="supervisor_contratista", nombre_firmante="Ana")

        response = self.client.patch(
            reverse("contratistas:declaraciones_detalle", args=[declaracion.pk]),
            {"estado": "aprobada"},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 200, response.data)
        mock_urlopen.assert_called_once()

    @patch("camaras_ia.notificaciones.urllib.request.urlopen")
    def test_sin_correo_de_contacto_no_intenta_notificar(self, mock_urlopen):
        declaracion = DeclaracionMetodo.objects.create(
            contratista=self.contratista,  # contacto_correo vacío por defecto
            fecha_elaboracion=datetime.date(2026, 7, 11),
            descripcion_trabajo="Instalación de pórtico",
        )
        FirmaMetodo.objects.create(declaracion=declaracion, rol="supervisor_contratista", nombre_firmante="Ana")

        response = self.client.patch(
            reverse("contratistas:declaraciones_detalle", args=[declaracion.pk]),
            {"estado": "aprobada"},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 200, response.data)
        mock_urlopen.assert_not_called()

    def test_editar_sin_cambiar_estado_no_exige_firma(self):
        """Solo la transición A 'aprobada' exige firma — editar cualquier
        otro campo (o dejar el estado en borrador) sigue libre."""
        declaracion = DeclaracionMetodo.objects.create(
            contratista=self.contratista,
            fecha_elaboracion=datetime.date(2026, 7, 11),
            descripcion_trabajo="Instalación de pórtico",
        )
        response = self.client.patch(
            reverse("contratistas:declaraciones_detalle", args=[declaracion.pk]),
            {"planta_area": "Cervecería Tocancipá"},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_pdf_devuelve_documento(self):
        declaracion = DeclaracionMetodo.objects.create(
            contratista=self.contratista,
            fecha_elaboracion=datetime.date(2026, 7, 11),
            descripcion_trabajo="Instalación de pórtico",
        )
        ActividadMetodo.objects.create(
            declaracion=declaracion,
            orden=0,
            secuencia="Ingreso a planta",
            probabilidad_sin=6,
            frecuencia_sin=3,
            impacto_sin=3,
        )
        FirmaMetodo.objects.create(declaracion=declaracion, rol="supervisor_contratista", nombre_firmante="Ana")

        response = self.client.get(
            reverse("contratistas:declaraciones_pdf", args=[declaracion.pk]), **self._auth(self.operador)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_pdf_requiere_autenticacion(self):
        declaracion = DeclaracionMetodo.objects.create(
            contratista=self.contratista,
            fecha_elaboracion=datetime.date(2026, 7, 11),
            descripcion_trabajo="Instalación de pórtico",
        )
        response = self.client.get(reverse("contratistas:declaraciones_pdf", args=[declaracion.pk]))
        self.assertEqual(response.status_code, 401)

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
