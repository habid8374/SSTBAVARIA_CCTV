import datetime
import io
import urllib.error
import zipfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa

from .models import Camara, ConfiguracionNotificaciones, EquipoLocal, EventoDetectado, ReglaAlerta, ZonaRestringida
from .services import _regla_vigente, disparar_alerta, evaluar_zona_horario, punto_en_poligono

Usuario = get_user_model()

CUADRADO = [[0, 0], [10, 0], [10, 10], [0, 10]]


class RtspUrlEfectivaTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Bavaria Planta")

    def test_usa_rtsp_url_explicita_si_esta_configurada(self):
        camara = Camara.objects.create(
            empresa=self.empresa, nombre="Cam 1", ip="10.0.0.1", rtsp_url="rtsp://otra-marca.example/stream"
        )
        self.assertEqual(camara.rtsp_url_efectiva, "rtsp://otra-marca.example/stream")

    def test_construye_patron_dahua_con_credenciales(self):
        camara = Camara.objects.create(
            empresa=self.empresa, nombre="Cam 1", ip="10.0.0.1", usuario_onvif="admin", password_onvif="clave123"
        )
        self.assertEqual(
            camara.rtsp_url_efectiva,
            "rtsp://admin:clave123@10.0.0.1:554/cam/realmonitor?channel=1&subtype=1",
        )

    def test_construye_patron_dahua_sin_credenciales(self):
        camara = Camara.objects.create(empresa=self.empresa, nombre="Cam 1", ip="10.0.0.1")
        self.assertEqual(
            camara.rtsp_url_efectiva, "rtsp://10.0.0.1:554/cam/realmonitor?channel=1&subtype=1"
        )


class PuntoEnPoligonoTests(TestCase):
    def test_punto_dentro(self):
        self.assertTrue(punto_en_poligono((5, 5), CUADRADO))

    def test_punto_fuera(self):
        self.assertFalse(punto_en_poligono((15, 5), CUADRADO))

    def test_poligono_invalido(self):
        self.assertFalse(punto_en_poligono((1, 1), [[0, 0], [1, 1]]))


class ReglaVigenteTests(TestCase):
    def _regla(self, hora_inicio, hora_fin, dias):
        return ReglaAlerta(
            hora_inicio=datetime.time.fromisoformat(hora_inicio),
            hora_fin=datetime.time.fromisoformat(hora_fin),
            dias_semana=dias,
        )

    def test_horario_normal_dentro(self):
        regla = self._regla("08:00", "17:00", [0, 1, 2, 3, 4])
        momento = timezone.make_aware(datetime.datetime(2026, 8, 24, 12, 0))  # lunes
        self.assertTrue(_regla_vigente(regla, momento))

    def test_horario_normal_fuera_de_hora(self):
        regla = self._regla("08:00", "17:00", [0, 1, 2, 3, 4])
        momento = timezone.make_aware(datetime.datetime(2026, 8, 24, 20, 0))  # lunes noche
        self.assertFalse(_regla_vigente(regla, momento))

    def test_horario_normal_dia_incorrecto(self):
        regla = self._regla("08:00", "17:00", [5, 6])  # solo fin de semana
        momento = timezone.make_aware(datetime.datetime(2026, 8, 24, 12, 0))  # lunes
        self.assertFalse(_regla_vigente(regla, momento))

    def test_horario_nocturno_antes_de_medianoche(self):
        regla = self._regla("22:00", "06:00", [4])  # viernes en la noche
        momento = timezone.make_aware(datetime.datetime(2026, 8, 28, 23, 30))  # viernes
        self.assertTrue(_regla_vigente(regla, momento))

    def test_horario_nocturno_despues_de_medianoche(self):
        regla = self._regla("22:00", "06:00", [4])  # viernes en la noche
        momento = timezone.make_aware(datetime.datetime(2026, 8, 29, 3, 0))  # sábado 3am
        self.assertTrue(_regla_vigente(regla, momento))

    def test_horario_nocturno_fuera_de_ventana(self):
        regla = self._regla("22:00", "06:00", [4])
        momento = timezone.make_aware(datetime.datetime(2026, 8, 29, 12, 0))  # sábado mediodía
        self.assertFalse(_regla_vigente(regla, momento))


class EvaluarZonaHorarioTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Bavaria Planta")
        self.camara = Camara.objects.create(empresa=self.empresa, nombre="Cam 1", ip="10.0.0.1")
        self.zona = ZonaRestringida.objects.create(camara=self.camara, nombre="Bodega", poligono=CUADRADO)
        self.regla = ReglaAlerta.objects.create(
            zona=self.zona,
            hora_inicio=datetime.time(0, 0),
            hora_fin=datetime.time(23, 59, 59),
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            destinatario="+573000000000",
        )

    def test_punto_dentro_con_regla_vigente(self):
        zona, regla = evaluar_zona_horario(self.camara, (5, 5))
        self.assertEqual(zona, self.zona)
        self.assertEqual(regla, self.regla)

    def test_punto_fuera_de_toda_zona(self):
        zona, regla = evaluar_zona_horario(self.camara, (50, 50))
        self.assertIsNone(zona)
        self.assertIsNone(regla)

    def test_punto_dentro_sin_regla_vigente(self):
        self.regla.activa = False
        self.regla.save()
        zona, regla = evaluar_zona_horario(self.camara, (5, 5))
        self.assertEqual(zona, self.zona)
        self.assertIsNone(regla)

    def test_zona_inactiva_se_ignora(self):
        self.zona.activa = False
        self.zona.save()
        zona, regla = evaluar_zona_horario(self.camara, (5, 5))
        self.assertIsNone(zona)
        self.assertIsNone(regla)


@override_settings(BREVO_API_KEY="clave-de-prueba", BREVO_REMITENTE_EMAIL="a@x.com", BREVO_REMITENTE_NOMBRE="Test")
class DispararAlertaCorreoTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Bavaria Planta")
        self.camara = Camara.objects.create(empresa=self.empresa, nombre="Cam 1", ip="10.0.0.1")
        self.zona = ZonaRestringida.objects.create(camara=self.camara, nombre="Bodega", poligono=CUADRADO)
        self.regla_correo = ReglaAlerta.objects.create(
            zona=self.zona,
            hora_inicio=datetime.time(0, 0),
            hora_fin=datetime.time(23, 59, 59),
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            canal_notificacion=ReglaAlerta.Canal.CORREO,
            destinatario="seguridad@bavaria.com",
        )
        self.regla_whatsapp = ReglaAlerta.objects.create(
            zona=self.zona,
            hora_inicio=datetime.time(0, 0),
            hora_fin=datetime.time(23, 59, 59),
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            canal_notificacion=ReglaAlerta.Canal.WHATSAPP,
            destinatario="+573000000000",
        )
        self.evento = EventoDetectado.objects.create(camara=self.camara, zona=self.zona, punto_x=1, punto_y=1)

    @patch("camaras_ia.notificaciones.urllib.request.urlopen")
    def test_correo_exitoso_marca_evento(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.status = 201
        disparar_alerta(self.evento, self.regla_correo)
        self.evento.refresh_from_db()
        self.assertTrue(self.evento.notificacion_enviada)
        self.assertEqual(self.evento.canal_notificacion, "correo")
        self.assertIn("seguridad@bavaria.com", self.evento.notificacion_detalle)
        mock_urlopen.assert_called_once()

    @patch("camaras_ia.notificaciones.urllib.request.urlopen")
    def test_correo_fallido_registra_el_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        disparar_alerta(self.evento, self.regla_correo)
        self.evento.refresh_from_db()
        self.assertFalse(self.evento.notificacion_enviada)
        self.assertTrue(self.evento.notificacion_detalle)

    @override_settings(BREVO_API_KEY="")
    def test_sin_api_key_no_rompe_y_queda_registrado(self):
        disparar_alerta(self.evento, self.regla_correo)
        self.evento.refresh_from_db()
        self.assertFalse(self.evento.notificacion_enviada)
        self.assertIn("Brevo", self.evento.notificacion_detalle)

    @override_settings(BREVO_API_KEY="desde-variable-de-entorno")
    @patch("camaras_ia.notificaciones.urllib.request.urlopen")
    def test_api_key_de_la_bd_tiene_prioridad_sobre_settings(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.status = 201
        config = ConfiguracionNotificaciones.obtener()
        config.brevo_api_key = "desde-la-bd"
        config.save()

        disparar_alerta(self.evento, self.regla_correo)

        # urlopen(request, timeout=...) — la Request enviada queda en args[0]
        request_enviado = mock_urlopen.call_args[0][0]
        self.assertEqual(request_enviado.get_header("Api-key"), "desde-la-bd")

    @patch("camaras_ia.notificaciones.urllib.request.urlopen")
    def test_canal_whatsapp_no_intenta_enviar_correo(self, mock_urlopen):
        disparar_alerta(self.evento, self.regla_whatsapp)
        mock_urlopen.assert_not_called()
        self.evento.refresh_from_db()
        self.assertFalse(self.evento.notificacion_enviada)
        self.assertEqual(self.evento.canal_notificacion, "whatsapp")
        self.assertTrue(self.evento.notificacion_detalle)

    @patch("core.push.enviar_push_a_personal_interno")
    @patch("camaras_ia.notificaciones.urllib.request.urlopen")
    def test_dispara_push_al_personal_interno(self, mock_urlopen, mock_push):
        mock_urlopen.return_value.__enter__.return_value.status = 201
        disparar_alerta(self.evento, self.regla_correo)
        mock_push.assert_called_once()
        titulo, mensaje = mock_push.call_args[0][:2]
        self.assertIn("cámaras", titulo.lower())
        self.assertIn("Bodega", mensaje)
        self.assertEqual(mock_push.call_args.kwargs.get("url"), "/dashboard?ir=alertas")

    @patch("core.push.enviar_push_a_personal_interno")
    def test_dispara_push_tambien_en_canal_whatsapp(self, mock_push):
        disparar_alerta(self.evento, self.regla_whatsapp)
        mock_push.assert_called_once()


class RecibirEventoCamaraViewTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Bavaria Planta")
        self.otra_empresa = Empresa.objects.create(nombre="Otra Empresa")
        self.equipo = EquipoLocal.objects.create(empresa=self.empresa, nombre="Equipo 1")
        self.camara = Camara.objects.create(empresa=self.empresa, nombre="Cam 1", ip="10.0.0.1")
        self.zona = ZonaRestringida.objects.create(camara=self.camara, nombre="Bodega", poligono=CUADRADO)
        ReglaAlerta.objects.create(
            zona=self.zona,
            hora_inicio=datetime.time(0, 0),
            hora_fin=datetime.time(23, 59, 59),
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            destinatario="+573000000000",
        )
        self.url = reverse("camaras_ia:recibir_evento_camara")

    def test_sin_api_key_devuelve_401(self):
        response = self.client.post(self.url, {"camara": self.camara.pk, "punto_x": 5, "punto_y": 5})
        self.assertEqual(response.status_code, 401)

    def test_evento_dentro_de_zona_dispara_alerta(self):
        response = self.client.post(
            self.url,
            {"camara": self.camara.pk, "punto_x": 5, "punto_y": 5},
            HTTP_X_API_KEY=self.equipo.api_key,
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["disparo_alerta"])
        evento = EventoDetectado.objects.get(pk=response.data["id"])
        self.assertEqual(evento.zona, self.zona)
        self.assertTrue(evento.disparo_alerta)

    def test_evento_fuera_de_zona_no_dispara(self):
        response = self.client.post(
            self.url,
            {"camara": self.camara.pk, "punto_x": 50, "punto_y": 50},
            HTTP_X_API_KEY=self.equipo.api_key,
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["disparo_alerta"])

    def test_camara_de_otra_empresa_devuelve_403(self):
        camara_ajena = Camara.objects.create(empresa=self.otra_empresa, nombre="Cam ajena", ip="10.0.0.2")
        response = self.client.post(
            self.url,
            {"camara": camara_ajena.pk, "punto_x": 5, "punto_y": 5},
            HTTP_X_API_KEY=self.equipo.api_key,
        )
        self.assertEqual(response.status_code, 403)


class ObtenerReglasActivasViewTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Bavaria Planta")
        self.equipo = EquipoLocal.objects.create(empresa=self.empresa, nombre="Equipo 1")
        self.camara = Camara.objects.create(empresa=self.empresa, nombre="Cam 1", ip="10.0.0.1")
        self.zona = ZonaRestringida.objects.create(camara=self.camara, nombre="Bodega", poligono=CUADRADO)
        self.regla = ReglaAlerta.objects.create(
            zona=self.zona,
            hora_inicio=datetime.time(8, 0),
            hora_fin=datetime.time(17, 0),
            dias_semana=[0, 1, 2, 3, 4],
            destinatario="+573000000000",
        )
        self.url = reverse("camaras_ia:obtener_reglas_activas")

    def test_sin_api_key_devuelve_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_devuelve_estructura_anidada(self):
        response = self.client.get(self.url, HTTP_X_API_KEY=self.equipo.api_key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["equipo"], self.equipo.nombre)
        camaras = response.data["camaras"]
        self.assertEqual(len(camaras), 1)
        self.assertEqual(camaras[0]["id"], self.camara.pk)
        self.assertEqual(len(camaras[0]["zonas"]), 1)
        self.assertEqual(len(camaras[0]["zonas"][0]["reglas"]), 1)
        self.assertEqual(camaras[0]["zonas"][0]["reglas"][0]["id"], self.regla.pk)

    def test_incluye_rtsp_url_efectiva(self):
        response = self.client.get(self.url, HTTP_X_API_KEY=self.equipo.api_key)
        self.assertEqual(response.data["camaras"][0]["rtsp_url"], self.camara.rtsp_url_efectiva)

    def test_snapshot_referencia_es_url_absoluta(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.camara.snapshot_referencia = SimpleUploadedFile("ref.jpg", b"contenido-jpeg-falso")
        self.camara.save()
        response = self.client.get(self.url, HTTP_X_API_KEY=self.equipo.api_key)
        url_snapshot = response.data["camaras"][0]["snapshot_referencia"]
        self.assertTrue(url_snapshot.startswith("http://testserver/"), url_snapshot)

    def test_zona_inactiva_no_aparece(self):
        self.zona.activa = False
        self.zona.save()
        response = self.client.get(self.url, HTTP_X_API_KEY=self.equipo.api_key)
        self.assertEqual(response.data["camaras"][0]["zonas"], [])


class DashboardEndpointsTests(TestCase):
    def setUp(self):
        # El throttle de login cuenta por IP y el test client siempre usa la
        # misma — sin esto, los _token() de tests anteriores se acumularían.
        cache.clear()
        self.empresa = Empresa.objects.create(nombre="Bavaria Planta")
        self.admin = Usuario.objects.create_superuser("admin", "admin@x.com", "clave12345")
        self.operador = Usuario.objects.create_user("operador1", "op@x.com", "clave12345")
        self.camara = Camara.objects.create(empresa=self.empresa, nombre="Cam 1", ip="10.0.0.1", activa=True)
        self.zona = ZonaRestringida.objects.create(camara=self.camara, nombre="Bodega", poligono=CUADRADO)
        self.regla = ReglaAlerta.objects.create(
            zona=self.zona,
            hora_inicio=datetime.time(0, 0),
            hora_fin=datetime.time(23, 59, 59),
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            destinatario="+573000000000",
        )
        self.evento = EventoDetectado.objects.create(
            camara=self.camara, zona=self.zona, punto_x=5, punto_y=5, disparo_alerta=True
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

    def test_indicadores(self):
        response = self.client.get(reverse("camaras_ia:indicadores_dashboard"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["camaras_activas"], 1)
        self.assertEqual(response.data["camaras_total"], 1)
        self.assertEqual(response.data["disponibilidad"], 100)

    def test_eventos_por_zona(self):
        response = self.client.get(reverse("camaras_ia:eventos_por_zona"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{"zona": "Bodega", "camara": "Cam 1", "total": 1}])

    def test_lista_eventos_y_filtro_estado(self):
        response = self.client.get(reverse("camaras_ia:eventos_lista"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        response = self.client.get(
            reverse("camaras_ia:eventos_lista") + "?estado=revisado", **self._auth(self.operador)
        )
        self.assertEqual(len(response.data), 0)

    def test_operador_puede_marcar_evento_revisado(self):
        url = reverse("camaras_ia:eventos_detalle", args=[self.evento.pk])
        response = self.client.patch(
            url, {"estado": "revisado"}, content_type="application/json", **self._auth(self.operador)
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.estado, "revisado")

    def test_lista_camaras_incluye_ultimo_evento_y_zonas(self):
        response = self.client.get(reverse("camaras_ia:camaras_lista"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        camara = response.data[0]
        self.assertEqual(camara["ultimo_evento"]["id"], self.evento.pk)
        self.assertEqual(len(camara["zonas"]), 1)

    def test_operador_no_puede_crear_zona(self):
        response = self.client.post(
            reverse("camaras_ia:zonas_lista"),
            {"camara": self.camara.pk, "nombre": "Nueva", "poligono": CUADRADO},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 403)

    def test_operador_puede_listar_zonas(self):
        response = self.client.get(reverse("camaras_ia:zonas_lista"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_admin_crea_zona(self):
        response = self.client.post(
            reverse("camaras_ia:zonas_lista"),
            {"camara": self.camara.pk, "nombre": "Nueva zona", "poligono": CUADRADO},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(ZonaRestringida.objects.filter(nombre="Nueva zona").exists())

    def test_admin_crea_regla_para_zona(self):
        response = self.client.post(
            reverse("camaras_ia:reglas_lista"),
            {
                "zona": self.zona.pk,
                "hora_inicio": "22:00",
                "hora_fin": "06:00",
                "dias_semana": [4, 5],
                "canal_notificacion": "correo",
                "destinatario": "seguridad@bavaria.com",
            },
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_operador_no_puede_eliminar_zona(self):
        url = reverse("camaras_ia:zonas_detalle", args=[self.zona.pk])
        response = self.client.delete(url, **self._auth(self.operador))
        self.assertEqual(response.status_code, 403)

    def test_admin_elimina_zona(self):
        url = reverse("camaras_ia:zonas_detalle", args=[self.zona.pk])
        response = self.client.delete(url, **self._auth(self.admin))
        self.assertEqual(response.status_code, 204)

    def test_sin_autenticar_devuelve_401(self):
        response = self.client.get(reverse("camaras_ia:indicadores_dashboard"))
        self.assertEqual(response.status_code, 401)

    def test_operador_no_puede_crear_camara(self):
        response = self.client.post(
            reverse("camaras_ia:camaras_lista"),
            {"nombre": "Cam nueva", "ip": "10.0.0.9"},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_crea_camara_sin_empresa_previa(self):
        Camara.objects.all().delete()
        Empresa.objects.all().delete()
        response = self.client.post(
            reverse("camaras_ia:camaras_lista"),
            {"nombre": "Cam nueva", "ip": "10.0.0.9", "ubicacion": "Bodega 2"},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 201, response.data)
        camara = Camara.objects.get(nombre="Cam nueva")
        self.assertIsNotNone(camara.empresa)
        self.assertEqual(camara.ip, "10.0.0.9")

    def test_admin_edita_camara(self):
        url = reverse("camaras_ia:camaras_detalle", args=[self.camara.pk])
        response = self.client.patch(
            url,
            {"ubicacion": "Nueva ubicación", "activa": False},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.camara.refresh_from_db()
        self.assertEqual(self.camara.ubicacion, "Nueva ubicación")
        self.assertFalse(self.camara.activa)

    def test_operador_no_puede_editar_camara(self):
        url = reverse("camaras_ia:camaras_detalle", args=[self.camara.pk])
        response = self.client.patch(
            url, {"activa": False}, content_type="application/json", **self._auth(self.operador)
        )
        self.assertEqual(response.status_code, 403)

    # --- Sección Sistema: configuración de notificaciones ---

    def test_operador_puede_leer_configuracion_notificaciones(self):
        response = self.client.get(
            reverse("camaras_ia:configuracion_notificaciones"), **self._auth(self.operador)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("brevo_api_key_configurada", response.data)
        self.assertNotIn("brevo_api_key", response.data)  # write_only: nunca se devuelve el secreto

    def test_operador_no_puede_editar_configuracion_notificaciones(self):
        response = self.client.patch(
            reverse("camaras_ia:configuracion_notificaciones"),
            {"brevo_api_key": "xkeysib-nueva"},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_guarda_api_key_de_brevo(self):
        response = self.client.patch(
            reverse("camaras_ia:configuracion_notificaciones"),
            {
                "brevo_api_key": "xkeysib-nueva",
                "brevo_remitente_email": "alertas@bavaria.com",
                "brevo_remitente_nombre": "Bavaria SST",
            },
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["brevo_api_key_configurada"])
        self.assertEqual(response.data["brevo_remitente_email"], "alertas@bavaria.com")

        config = ConfiguracionNotificaciones.obtener()
        self.assertEqual(config.brevo_api_key, "xkeysib-nueva")

    def test_sin_configurar_reporta_no_configurada(self):
        response = self.client.get(
            reverse("camaras_ia:configuracion_notificaciones"), **self._auth(self.admin)
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["brevo_api_key_configurada"])

    @override_settings(BREVO_API_KEY="desde-variable-de-entorno")
    def test_configurada_por_variable_de_entorno_cuenta_como_configurada(self):
        response = self.client.get(
            reverse("camaras_ia:configuracion_notificaciones"), **self._auth(self.admin)
        )
        self.assertTrue(response.data["brevo_api_key_configurada"])

    # --- Sección Sistema: equipos locales ---

    def test_operador_puede_listar_equipos_locales(self):
        EquipoLocal.objects.create(empresa=self.empresa, nombre="Equipo Bodega")
        response = self.client.get(reverse("camaras_ia:equipos_locales_lista"), **self._auth(self.operador))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIn("api_key", response.data[0])

    def test_operador_no_puede_crear_equipo_local(self):
        response = self.client.post(
            reverse("camaras_ia:equipos_locales_lista"),
            {"nombre": "Equipo Bodega"},
            content_type="application/json",
            **self._auth(self.operador),
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_crea_equipo_local_sin_empresa_previa(self):
        response = self.client.post(
            reverse("camaras_ia:equipos_locales_lista"),
            {"nombre": "Equipo Bodega"},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 201, response.data)
        equipo = EquipoLocal.objects.get(nombre="Equipo Bodega")
        self.assertIsNotNone(equipo.empresa)
        self.assertTrue(equipo.api_key)
        self.assertFalse(response.data["conectado"])

    def test_conectado_true_con_conexion_reciente(self):
        equipo = EquipoLocal.objects.create(
            empresa=self.empresa, nombre="Equipo Bodega", ultima_conexion=timezone.now()
        )
        response = self.client.get(
            reverse("camaras_ia:equipos_locales_detalle", args=[equipo.pk]), **self._auth(self.admin)
        )
        self.assertTrue(response.data["conectado"])

    def test_conectado_false_con_conexion_vieja(self):
        equipo = EquipoLocal.objects.create(
            empresa=self.empresa,
            nombre="Equipo Bodega",
            ultima_conexion=timezone.now() - datetime.timedelta(minutes=10),
        )
        response = self.client.get(
            reverse("camaras_ia:equipos_locales_detalle", args=[equipo.pk]), **self._auth(self.admin)
        )
        self.assertFalse(response.data["conectado"])

    def test_admin_desactiva_equipo_local(self):
        equipo = EquipoLocal.objects.create(empresa=self.empresa, nombre="Equipo Bodega")
        response = self.client.patch(
            reverse("camaras_ia:equipos_locales_detalle", args=[equipo.pk]),
            {"activo": False},
            content_type="application/json",
            **self._auth(self.admin),
        )
        self.assertEqual(response.status_code, 200, response.data)
        equipo.refresh_from_db()
        self.assertFalse(equipo.activo)

    def test_operador_no_puede_eliminar_equipo_local(self):
        equipo = EquipoLocal.objects.create(empresa=self.empresa, nombre="Equipo Bodega")
        response = self.client.delete(
            reverse("camaras_ia:equipos_locales_detalle", args=[equipo.pk]), **self._auth(self.operador)
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_elimina_equipo_local(self):
        equipo = EquipoLocal.objects.create(empresa=self.empresa, nombre="Equipo Bodega")
        response = self.client.delete(
            reverse("camaras_ia:equipos_locales_detalle", args=[equipo.pk]), **self._auth(self.admin)
        )
        self.assertEqual(response.status_code, 204)

    def test_operador_puede_descargar_el_zip_de_equipo_local(self):
        response = self.client.get(
            reverse("camaras_ia:equipos_locales_descargar_zip"), **self._auth(self.operador)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        contenido = zipfile.ZipFile(io.BytesIO(response.content))
        nombres = contenido.namelist()
        self.assertIn("equipo_local/instalar.bat", nombres)
        self.assertIn("equipo_local/instalar.sh", nombres)
        self.assertIn("equipo_local/main.py", nombres)
        self.assertTrue(all(not n.startswith("equipo_local/venv/") for n in nombres))
        self.assertTrue(all("__pycache__" not in n for n in nombres))
        self.assertTrue(all(not n.startswith("equipo_local/tests/") for n in nombres))
        self.assertTrue(all(not n.startswith("equipo_local/grabaciones/") for n in nombres))

    def test_anonimo_no_puede_descargar_el_zip_de_equipo_local(self):
        response = self.client.get(reverse("camaras_ia:equipos_locales_descargar_zip"))
        self.assertEqual(response.status_code, 401)

    def test_zip_de_equipo_local_conserva_el_bit_ejecutable_de_instalar_sh(self):
        response = self.client.get(
            reverse("camaras_ia:equipos_locales_descargar_zip"), **self._auth(self.admin)
        )
        contenido = zipfile.ZipFile(io.BytesIO(response.content))
        info = contenido.getinfo("equipo_local/instalar.sh")
        modo = (info.external_attr >> 16) & 0o777
        self.assertTrue(modo & 0o111)
