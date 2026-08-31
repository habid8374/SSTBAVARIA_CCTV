"""Visor web local: grilla de cámaras en vivo + navegación de grabaciones.

Pensado para verse desde la misma red local del equipo (nunca sale a
internet — el equipo local no expone puertos públicos, ver README). Usa el
servidor de desarrollo de Flask con `threaded=True`: alcanza de sobra para
unos pocos administradores viendo la grilla desde la red de la planta: no es
para exponerlo a internet ni a un volumen alto de usuarios concurrentes.
"""

from __future__ import annotations

import hmac
import logging
import re
import time
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from .grabador import eliminar_grabaciones, listar_grabaciones

logger = logging.getLogger("equipo_local.visor_web")

_PATRON_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
_PATRON_ARCHIVO = re.compile(r"[\w.\-]+\.mp4")


def generar_stream_mjpeg(obtener_frame, intervalo_segundos=0.3, limite_espera_segundos=20, dormir=time.sleep):
    """Generador MJPEG (multipart/x-mixed-replace) a partir de una función
    `obtener_frame()` que devuelve el último JPEG disponible (o None si
    todavía no hay ninguno). Si pasan `limite_espera_segundos` sin que
    aparezca el primer frame (cámara recién arrancando o desconectada),
    corta el stream solo en vez de quedar colgado para siempre."""
    espera_acumulada = 0.0
    while True:
        frame = obtener_frame()
        if frame is None:
            if espera_acumulada >= limite_espera_segundos:
                return
            espera_acumulada += intervalo_segundos
            dormir(intervalo_segundos)
            continue
        espera_acumulada = 0.0
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        dormir(intervalo_segundos)


def crear_app(sincronizador, config):
    """`sincronizador` es el SincronizadorCamaras de main.py — se consulta
    en vivo (no se copia) para siempre reflejar las cámaras activas."""
    app = Flask(__name__)

    if not config.VISOR_WEB_USUARIO:
        logger.warning(
            "VISOR_WEB_USUARIO/VISOR_WEB_PASSWORD no configurados — el visor web "
            "queda sin autenticación. Solo recomendable si la red local ya es de confianza."
        )

    @app.before_request
    def _verificar_auth():
        if not config.VISOR_WEB_USUARIO:
            return None
        auth = request.authorization
        credenciales_ok = (
            auth is not None
            and hmac.compare_digest(auth.username or "", config.VISOR_WEB_USUARIO)
            and hmac.compare_digest(auth.password or "", config.VISOR_WEB_PASSWORD)
        )
        if not credenciales_ok:
            return Response(
                "Autenticación requerida.",
                401,
                {"WWW-Authenticate": 'Basic realm="Equipo Local SST Bavaria"'},
            )
        return None

    @app.route("/")
    def index():
        return Response(_PAGINA_HTML, mimetype="text/html")

    @app.route("/api/camaras")
    def api_camaras():
        return jsonify(
            [{"id": monitor.id, "nombre": monitor.nombre} for monitor in sincronizador.monitores.values()]
        )

    @app.route("/vivo/<int:camara_id>")
    def vivo(camara_id):
        monitor = sincronizador.monitores.get(camara_id)
        if monitor is None:
            abort(404)
        return Response(
            generar_stream_mjpeg(monitor.obtener_ultimo_frame_jpeg),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/api/grabaciones")
    def api_grabaciones():
        camara_id = request.args.get("camara", type=int)
        fecha = request.args.get("fecha") or None
        if fecha and not _PATRON_FECHA.fullmatch(fecha):
            return jsonify({"detail": "Fecha inválida, usar YYYY-MM-DD."}), 400
        grabaciones = listar_grabaciones(config.GRABACIONES_DIR, camara_id=camara_id, fecha=fecha)
        return jsonify(
            [
                {
                    "camara_id": g.camara_id,
                    "fecha": g.fecha,
                    "archivo": g.archivo,
                    "tamano_bytes": g.tamano_bytes,
                    "url": f"/grabaciones/{g.camara_id}/{g.fecha}/{g.archivo}",
                }
                for g in grabaciones
            ]
        )

    @app.route("/api/grabaciones/eliminar", methods=["POST"])
    def api_eliminar_grabaciones():
        datos = request.get_json(silent=True) or {}
        camara_id = datos.get("camara_id")
        fecha = datos.get("fecha") or None
        if fecha and not _PATRON_FECHA.fullmatch(fecha):
            return jsonify({"detail": "Fecha inválida, usar YYYY-MM-DD."}), 400
        try:
            borrados = eliminar_grabaciones(config.GRABACIONES_DIR, camara_id=camara_id, fecha=fecha)
        except ValueError as err:
            return jsonify({"detail": str(err)}), 400
        return jsonify({"borrados": borrados})

    @app.route("/grabaciones/<int:camara_id>/<fecha>/<archivo>")
    def servir_grabacion(camara_id, fecha, archivo):
        if not _PATRON_FECHA.fullmatch(fecha) or not _PATRON_ARCHIVO.fullmatch(archivo):
            abort(404)
        carpeta = Path(config.GRABACIONES_DIR) / str(camara_id) / fecha
        return send_from_directory(carpeta, archivo)

    return app


def iniciar_en_hilo(sincronizador, config):
    """Levanta el visor web en un hilo daemon aparte — no bloquea el loop
    principal de sincronización de main.py."""
    import threading

    app = crear_app(sincronizador, config)

    def _correr():
        app.run(host=config.VISOR_WEB_HOST, port=config.VISOR_WEB_PUERTO, threaded=True, use_reloader=False)

    hilo = threading.Thread(target=_correr, name="visor-web", daemon=True)
    hilo.start()
    logger.info("Visor web escuchando en http://%s:%s", config.VISOR_WEB_HOST, config.VISOR_WEB_PUERTO)
    return hilo


_PAGINA_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>SST Bavaria — Equipo Local</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
  header { padding: 1rem 1.5rem; background: #1e2761; }
  header h1 { margin: 0; font-size: 1.1rem; }
  main { padding: 1.5rem; max-width: 1200px; margin: 0 auto; }
  h2 { font-size: 1rem; text-transform: uppercase; letter-spacing: .05em; color: #94a3b8; margin-top: 2rem; }
  .grilla { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; }
  .camara { background: #1e293b; border-radius: .5rem; overflow: hidden; }
  .camara img { width: 100%; display: block; background: #000; aspect-ratio: 16/9; object-fit: contain; }
  .camara p { margin: 0; padding: .5rem .75rem; font-size: .85rem; }
  .filtros { display: flex; gap: .75rem; flex-wrap: wrap; align-items: end; margin-bottom: 1rem; }
  .filtros label { display: flex; flex-direction: column; font-size: .8rem; color: #94a3b8; gap: .25rem; }
  select, input, button { padding: .4rem .6rem; border-radius: .4rem; border: 1px solid #334155; background: #0f172a; color: #e2e8f0; font-size: .85rem; }
  button { cursor: pointer; background: #2563eb; border-color: #2563eb; }
  button.borrar { background: #b91c1c; border-color: #b91c1c; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th, td { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid #334155; }
  a { color: #60a5fa; }
  .vacio { color: #94a3b8; font-size: .85rem; padding: 1rem 0; }
</style>
</head>
<body>
<header><h1>SST Bavaria — Equipo Local (cámaras y grabaciones)</h1></header>
<main>
  <h2>Cámaras en vivo</h2>
  <div id="grilla-camaras" class="grilla"></div>

  <h2>Grabaciones</h2>
  <div class="filtros">
    <label>Cámara
      <select id="filtro-camara"><option value="">Todas</option></select>
    </label>
    <label>Fecha
      <input type="date" id="filtro-fecha">
    </label>
    <button id="btn-buscar" type="button">Buscar</button>
    <button id="btn-eliminar" type="button" class="borrar">Eliminar por fecha</button>
  </div>
  <div id="mensaje" class="vacio"></div>
  <table id="tabla-grabaciones" style="display:none">
    <thead><tr><th>Cámara</th><th>Fecha</th><th>Archivo</th><th>Tamaño</th><th></th></tr></thead>
    <tbody></tbody>
  </table>
</main>
<script>
async function cargarCamaras() {
  const resp = await fetch("/api/camaras");
  const camaras = await resp.json();
  const grilla = document.getElementById("grilla-camaras");
  const select = document.getElementById("filtro-camara");
  grilla.innerHTML = "";
  camaras.forEach((c) => {
    const div = document.createElement("div");
    div.className = "camara";
    div.innerHTML = `<img src="/vivo/${c.id}" alt="${c.nombre}"><p>${c.nombre}</p>`;
    grilla.appendChild(div);
    const opcion = document.createElement("option");
    opcion.value = c.id;
    opcion.textContent = c.nombre;
    select.appendChild(opcion);
  });
  if (camaras.length === 0) {
    grilla.innerHTML = '<p class="vacio">Todavía no hay cámaras activas.</p>';
  }
}

function formatoTamano(bytes) {
  if (bytes > 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / 1024).toFixed(0) + " KB";
}

async function buscarGrabaciones() {
  const camara = document.getElementById("filtro-camara").value;
  const fecha = document.getElementById("filtro-fecha").value;
  const params = new URLSearchParams();
  if (camara) params.set("camara", camara);
  if (fecha) params.set("fecha", fecha);
  const resp = await fetch("/api/grabaciones?" + params.toString());
  const grabaciones = await resp.json();
  const tabla = document.getElementById("tabla-grabaciones");
  const cuerpo = tabla.querySelector("tbody");
  const mensaje = document.getElementById("mensaje");
  cuerpo.innerHTML = "";
  if (!Array.isArray(grabaciones) || grabaciones.length === 0) {
    tabla.style.display = "none";
    mensaje.textContent = "No hay grabaciones con estos filtros.";
    return;
  }
  mensaje.textContent = "";
  tabla.style.display = "table";
  grabaciones.forEach((g) => {
    const fila = document.createElement("tr");
    fila.innerHTML = `<td>${g.camara_id}</td><td>${g.fecha}</td><td>${g.archivo}</td>` +
      `<td>${formatoTamano(g.tamano_bytes)}</td><td><a href="${g.url}" target="_blank">Ver/descargar</a></td>`;
    cuerpo.appendChild(fila);
  });
}

async function eliminarPorFecha() {
  const camara = document.getElementById("filtro-camara").value;
  const fecha = document.getElementById("filtro-fecha").value;
  if (!fecha) {
    alert("Elige una fecha para poder eliminar.");
    return;
  }
  const etiquetaCamara = camara ? "de esa cámara " : "de TODAS las cámaras ";
  if (!confirm(`¿Eliminar las grabaciones ${etiquetaCamara}del ${fecha}? Esta acción no se puede deshacer.`)) {
    return;
  }
  const cuerpo = {};
  if (camara) cuerpo.camara_id = Number(camara);
  cuerpo.fecha = fecha;
  const resp = await fetch("/api/grabaciones/eliminar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
  const datos = await resp.json();
  if (!resp.ok) {
    alert(datos.detail || "No se pudo eliminar.");
    return;
  }
  alert(`Se eliminaron ${datos.borrados} archivo(s).`);
  buscarGrabaciones();
}

document.getElementById("btn-buscar").addEventListener("click", buscarGrabaciones);
document.getElementById("btn-eliminar").addEventListener("click", eliminarPorFecha);
cargarCamaras();
buscarGrabaciones();
</script>
</body>
</html>
"""
