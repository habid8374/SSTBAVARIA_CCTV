import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa

from .models import Camara, EquipoLocal, EventoDetectado, ReglaAlerta, ZonaRestringida
from .services import _regla_vigente, evaluar_zona_horario, punto_en_poligono

CUADRADO = [[0, 0], [10, 0], [10, 10], [0, 10]]


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

    def test_zona_inactiva_no_aparece(self):
        self.zona.activa = False
        self.zona.save()
        response = self.client.get(self.url, HTTP_X_API_KEY=self.equipo.api_key)
        self.assertEqual(response.data["camaras"][0]["zonas"], [])
