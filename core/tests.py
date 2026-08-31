from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from contratistas.models import EmpresaContratista
from core.models import Empresa

from .models import PerfilUsuario
from .validators import MAX_UPLOAD_MB, validar_tamano_archivo

Usuario = get_user_model()


class _ArchivoFalso:
    def __init__(self, tamano_bytes):
        self.size = tamano_bytes


class ValidarTamanoArchivoTests(TestCase):
    def test_acepta_archivo_dentro_del_limite(self):
        validar_tamano_archivo(_ArchivoFalso((MAX_UPLOAD_MB - 1) * 1024 * 1024))

    def test_rechaza_archivo_que_excede_el_limite(self):
        with self.assertRaises(ValidationError):
            validar_tamano_archivo(_ArchivoFalso((MAX_UPLOAD_MB + 1) * 1024 * 1024))


class PerfilUsuarioSignalTests(TestCase):
    def test_superusuario_recibe_rol_administrador(self):
        admin = Usuario.objects.create_superuser("admin", "admin@x.com", "clave12345")
        self.assertEqual(admin.perfil.rol, PerfilUsuario.Rol.ADMINISTRADOR)

    def test_usuario_normal_recibe_rol_operador(self):
        user = Usuario.objects.create_user("operador1", "op@x.com", "clave12345")
        self.assertEqual(user.perfil.rol, PerfilUsuario.Rol.OPERADOR)


class LoginViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser("admin", "admin@x.com", "clave12345")
        self.url = reverse("core:login")

    def test_login_devuelve_token_y_rol(self):
        response = self.client.post(
            self.url, {"username": "admin", "password": "clave12345"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["usuario"]["rol"], "administrador")

    def test_login_credenciales_invalidas(self):
        response = self.client.post(
            self.url, {"username": "admin", "password": "mala"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)


class LoginThrottleTests(TestCase):
    """Verifica que el límite de intentos de login (fuerza bruta) funciona."""

    def setUp(self):
        cache.clear()
        Usuario.objects.create_superuser("admin", "admin@x.com", "clave12345")
        self.url = reverse("core:login")

    def test_bloquea_despues_del_limite_de_intentos(self):
        from rest_framework.settings import api_settings

        limite = int(api_settings.DEFAULT_THROTTLE_RATES["login"].split("/")[0])
        for _ in range(limite):
            response = self.client.post(
                self.url, {"username": "admin", "password": "mala"}, content_type="application/json"
            )
            self.assertEqual(response.status_code, 401)

        bloqueado = self.client.post(
            self.url, {"username": "admin", "password": "clave12345"}, content_type="application/json"
        )
        self.assertEqual(bloqueado.status_code, 429)


class UsuarioManagementTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser("admin", "admin@x.com", "clave12345")
        self.operador = Usuario.objects.create_user("operador1", "op@x.com", "clave12345")
        self.lista_url = reverse("core:usuarios_lista")

    def _token(self, user):
        response = self.client.post(
            reverse("core:login"),
            {"username": user.username, "password": "clave12345"},
            content_type="application/json",
        )
        return response.data["token"]

    def test_operador_no_puede_listar_usuarios(self):
        token = self._token(self.operador)
        response = self.client.get(self.lista_url, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 403)

    def test_admin_puede_listar_usuarios(self):
        token = self._token(self.admin)
        response = self.client.get(self.lista_url, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_admin_crea_usuario_operador(self):
        token = self._token(self.admin)
        response = self.client.post(
            self.lista_url,
            {
                "username": "nuevo1",
                "email": "nuevo1@x.com",
                "password": "otraclave123",
                "rol": "operador",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 201, response.data)
        nuevo = Usuario.objects.get(username="nuevo1")
        self.assertEqual(nuevo.perfil.rol, PerfilUsuario.Rol.OPERADOR)
        self.assertTrue(nuevo.check_password("otraclave123"))

    def test_admin_cambia_rol_de_usuario(self):
        token = self._token(self.admin)
        detalle_url = reverse("core:usuarios_detalle", args=[self.operador.pk])
        response = self.client.patch(
            detalle_url,
            {"rol": "administrador"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.perfil.rol, PerfilUsuario.Rol.ADMINISTRADOR)

    def test_admin_no_puede_desactivar_su_propia_cuenta(self):
        token = self._token(self.admin)
        detalle_url = reverse("core:usuarios_detalle", args=[self.admin.pk])
        response = self.client.patch(
            detalle_url,
            {"is_active": False},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_no_puede_eliminar_su_propia_cuenta(self):
        token = self._token(self.admin)
        detalle_url = reverse("core:usuarios_detalle", args=[self.admin.pk])
        response = self.client.delete(detalle_url, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 403)

    def test_admin_elimina_otro_usuario(self):
        token = self._token(self.admin)
        detalle_url = reverse("core:usuarios_detalle", args=[self.operador.pk])
        response = self.client.delete(detalle_url, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Usuario.objects.filter(pk=self.operador.pk).exists())

    def test_sin_autenticar_devuelve_401(self):
        response = self.client.get(self.lista_url)
        self.assertEqual(response.status_code, 401)


class UsuarioContratistaTests(TestCase):
    """El rol Contratista exige elegir una empresa — es lo que scopea todo
    lo que ese usuario del portal puede ver y editar."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser("admin", "admin@x.com", "clave12345")
        empresa = Empresa.objects.create(nombre="Bavaria Planta")
        self.contratista = EmpresaContratista.objects.create(empresa=empresa, nombre="SCEPSA")
        self.lista_url = reverse("core:usuarios_lista")

    def _token(self, user):
        response = self.client.post(
            reverse("core:login"),
            {"username": user.username, "password": "clave12345"},
            content_type="application/json",
        )
        return response.data["token"]

    def test_crear_usuario_contratista_sin_empresa_devuelve_400(self):
        token = self._token(self.admin)
        response = self.client.post(
            self.lista_url,
            {"username": "portal1", "email": "portal1@x.com", "password": "otraclave123", "rol": "contratista"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("contratista", response.data)

    def test_crear_usuario_contratista_con_empresa(self):
        token = self._token(self.admin)
        response = self.client.post(
            self.lista_url,
            {
                "username": "portal1",
                "email": "portal1@x.com",
                "password": "otraclave123",
                "rol": "contratista",
                "contratista": self.contratista.pk,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 201, response.data)
        nuevo = Usuario.objects.get(username="portal1")
        self.assertEqual(nuevo.perfil.rol, PerfilUsuario.Rol.CONTRATISTA)
        self.assertEqual(nuevo.perfil.contratista_id, self.contratista.pk)
        self.assertFalse(nuevo.perfil.es_interno)

    def test_cambiar_rol_a_operador_limpia_la_empresa(self):
        usuario = Usuario.objects.create_user("portal1", "portal1@x.com", "clave12345")
        usuario.perfil.rol = PerfilUsuario.Rol.CONTRATISTA
        usuario.perfil.contratista = self.contratista
        usuario.perfil.save(update_fields=["rol", "contratista"])

        token = self._token(self.admin)
        response = self.client.patch(
            reverse("core:usuarios_detalle", args=[usuario.pk]),
            {"rol": "operador"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200, response.data)
        usuario.refresh_from_db()
        self.assertEqual(usuario.perfil.rol, PerfilUsuario.Rol.OPERADOR)
        self.assertIsNone(usuario.perfil.contratista_id)
        self.assertTrue(usuario.perfil.es_interno)

    def test_login_de_usuario_contratista_incluye_su_empresa(self):
        usuario = Usuario.objects.create_user("portal1", "portal1@x.com", "clave12345")
        usuario.perfil.rol = PerfilUsuario.Rol.CONTRATISTA
        usuario.perfil.contratista = self.contratista
        usuario.perfil.save(update_fields=["rol", "contratista"])

        response = self.client.post(
            reverse("core:login"),
            {"username": "portal1", "password": "clave12345"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["usuario"]["contratista_id"], self.contratista.pk)
        self.assertEqual(response.data["usuario"]["contratista_nombre"], "SCEPSA")
