"""Anuncio del visor web en la red local por mDNS/Bonjour — así se puede
entrar por http://<nombre>.local:8090 en vez de tener que buscar/memorizar
la IP del PC. No sale a internet: mDNS solo funciona dentro de la red local
(el mismo alcance que ya tiene el visor web).

Soporte por sistema operativo del lado de quien mira (no de este equipo):
- **Mac**: funciona directo (Bonjour es parte de macOS).
- **Linux de escritorio**: funciona directo en la mayoría (Avahi viene
  preinstalado en Ubuntu/Fedora/etc.).
- **Windows**: no trae mDNS de fábrica — hace falta instalar una vez
  "Bonjour Print Services" (gratis, de Apple) para que resuelva `.local`.
  Alternativa sin instalar nada: usar el nombre del PC en la red
  (`http://NOMBRE-DEL-PC:8090`, vía NetBIOS/LLMNR) — ver README.
"""

from __future__ import annotations

import logging
import socket

logger = logging.getLogger("equipo_local.mdns")


def resolver_ip_local():
    """IP de este PC en la red local — no depende de tener internet real:
    un socket UDP "conectado" solo hace una búsqueda de ruta, no manda nada."""
    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        socket_udp.connect(("8.8.8.8", 80))
        return socket_udp.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        socket_udp.close()


def anunciar(config):
    """Registra `<VISOR_WEB_MDNS_NOMBRE>.local` en la red apuntando a este
    PC. Devuelve el objeto Zeroconf a cerrar con dejar_de_anunciar() al
    detener el programa, o None si no se pudo anunciar (no rompe el resto
    del equipo local — el visor sigue disponible por IP igual)."""
    from zeroconf import ServiceInfo, Zeroconf

    ip = resolver_ip_local()
    hostname = f"{config.VISOR_WEB_MDNS_NOMBRE}.local."
    info = ServiceInfo(
        "_http._tcp.local.",
        f"{config.VISOR_WEB_MDNS_NOMBRE}._http._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=config.VISOR_WEB_PUERTO,
        server=hostname,
    )

    zeroconf = Zeroconf()
    try:
        zeroconf.register_service(info)
    except Exception:
        logger.exception(
            "No se pudo anunciar %s por mDNS — el visor web sigue disponible por IP (%s).", hostname, ip
        )
        zeroconf.close()
        return None

    logger.info(
        "Visor web anunciado en la red como http://%s:%s (además de http://%s:%s)",
        hostname.rstrip("."),
        config.VISOR_WEB_PUERTO,
        ip,
        config.VISOR_WEB_PUERTO,
    )
    return zeroconf


def dejar_de_anunciar(zeroconf):
    if zeroconf is not None:
        zeroconf.close()
