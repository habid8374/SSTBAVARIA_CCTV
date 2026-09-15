import socket
import unittest
from unittest.mock import MagicMock, patch

from equipo_local.mdns import anunciar, dejar_de_anunciar, resolver_ip_local


class _ConfigDePrueba:
    VISOR_WEB_MDNS_NOMBRE = "sstbavaria-camaras"
    VISOR_WEB_PUERTO = 8090


class ResolverIpLocalTests(unittest.TestCase):
    def test_devuelve_una_ip_valida(self):
        ip = resolver_ip_local()
        socket.inet_aton(ip)  # no debe lanzar — confirma que es una IPv4 válida

    @patch("equipo_local.mdns.socket.socket")
    def test_si_falla_la_ruta_devuelve_localhost(self, mock_socket_cls):
        mock_socket_cls.return_value.connect.side_effect = OSError("sin red")
        self.assertEqual(resolver_ip_local(), "127.0.0.1")


class AnunciarTests(unittest.TestCase):
    @patch("equipo_local.mdns.resolver_ip_local", return_value="192.168.1.50")
    @patch("zeroconf.Zeroconf")
    @patch("zeroconf.ServiceInfo")
    def test_registra_el_servicio_con_los_datos_correctos(self, mock_service_info, mock_zeroconf_cls, _mock_ip):
        zeroconf_instancia = mock_zeroconf_cls.return_value

        resultado = anunciar(_ConfigDePrueba)

        mock_service_info.assert_called_once()
        _, kwargs = mock_service_info.call_args
        self.assertEqual(kwargs["port"], 8090)
        self.assertEqual(kwargs["server"], "sstbavaria-camaras.local.")
        self.assertEqual(kwargs["addresses"], [socket.inet_aton("192.168.1.50")])

        zeroconf_instancia.register_service.assert_called_once()
        self.assertIs(resultado, zeroconf_instancia)

    @patch("equipo_local.mdns.resolver_ip_local", return_value="192.168.1.50")
    @patch("zeroconf.Zeroconf")
    @patch("zeroconf.ServiceInfo")
    def test_si_falla_el_registro_devuelve_none_y_cierra(self, _mock_service_info, mock_zeroconf_cls, _mock_ip):
        zeroconf_instancia = mock_zeroconf_cls.return_value
        zeroconf_instancia.register_service.side_effect = OSError("puerto ocupado")

        resultado = anunciar(_ConfigDePrueba)

        self.assertIsNone(resultado)
        zeroconf_instancia.close.assert_called_once()


class DejarDeAnunciarTests(unittest.TestCase):
    def test_cierra_si_no_es_none(self):
        zeroconf = MagicMock()
        dejar_de_anunciar(zeroconf)
        zeroconf.close.assert_called_once()

    def test_no_falla_si_es_none(self):
        dejar_de_anunciar(None)  # no debe lanzar


if __name__ == "__main__":
    unittest.main()
