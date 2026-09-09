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
from .sincronizacion_config import sincronizar_configuracion_local

logger = logging.getLogger("equipo_local.visor_web")

_PATRON_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
_PATRON_ARCHIVO = re.compile(r"[\w.\-]+\.mp4")


def _validar_zona(datos):
    """Mismas reglas que camaras_ia/serializers.py:ZonaDashboardSerializer.validate()
    — se duplica acá (no se puede importar Django desde el equipo local)
    para no dejar guardar localmente algo que la nube rechazaría al
    sincronizarse (ver sincronizacion_config.py)."""
    if not (datos.get("nombre") or "").strip():
        raise ValueError("La zona necesita un nombre.")
    tipo = datos.get("tipo", "poligono")
    if tipo == "poligono":
        poligono = datos.get("poligono")
        if not poligono or len(poligono) < 3:
            raise ValueError("Una zona tipo Polígono necesita al menos 3 puntos.")
    elif tipo == "punto_radio":
        faltantes = [
            campo for campo in ("centro_x", "centro_y", "radio_metros") if datos.get(campo) is None
        ]
        if faltantes:
            raise ValueError(f"Faltan campos obligatorios para Punto y radio: {', '.join(faltantes)}.")
        if datos["radio_metros"] <= 0:
            raise ValueError("El radio debe ser mayor que cero.")
    else:
        raise ValueError(f"Tipo de zona desconocido: {tipo!r}.")


def _validar_regla(datos):
    if not datos.get("hora_inicio") or not datos.get("hora_fin"):
        raise ValueError("La regla necesita hora de inicio y de fin.")
    if not (datos.get("destinatario") or "").strip():
        raise ValueError("La regla necesita un destinatario (correo o WhatsApp).")
    if not datos.get("dias_semana"):
        raise ValueError("Elige al menos un día de la semana.")


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

    @app.route("/api/camaras/<int:camara_id>/frame.jpg")
    def api_frame(camara_id):
        """Un solo frame JPEG (no el stream) — es el fondo fijo sobre el que
        se dibujan las zonas en /configurar/<id>, igual que el snapshot de
        referencia que antes se subía a mano desde el dashboard."""
        monitor = sincronizador.monitores.get(camara_id)
        if monitor is None:
            abort(404)
        frame = monitor.obtener_ultimo_frame_jpeg()
        if frame is None:
            abort(404)
        return Response(frame, mimetype="image/jpeg")

    def _almacenamiento_o_404():
        almacenamiento = getattr(sincronizador, "almacenamiento", None)
        if almacenamiento is None:
            abort(404)
        return almacenamiento

    @app.route("/api/config/camaras/<int:camara_id>/zonas", methods=["GET", "POST"])
    def api_config_zonas(camara_id):
        almacenamiento = _almacenamiento_o_404()
        if request.method == "GET":
            return jsonify(almacenamiento.listar_zonas_por_camara(camara_id, incluir_inactivas=True))

        datos = request.get_json(silent=True) or {}
        try:
            _validar_zona(datos)
        except ValueError as err:
            return jsonify({"detail": str(err)}), 400
        zona_id = almacenamiento.crear_zona(
            camara_id,
            nombre=datos.get("nombre", "").strip(),
            tipo=datos.get("tipo", "poligono"),
            poligono=datos.get("poligono"),
            centro_x=datos.get("centro_x"),
            centro_y=datos.get("centro_y"),
            radio_metros=datos.get("radio_metros"),
            activa=datos.get("activa", True),
        )
        return jsonify(almacenamiento.obtener_zona(zona_id)), 201

    @app.route("/api/config/zonas/<int:zona_id>", methods=["PUT", "DELETE"])
    def api_config_zona_detalle(zona_id):
        almacenamiento = _almacenamiento_o_404()
        if almacenamiento.obtener_zona(zona_id) is None:
            abort(404)
        if request.method == "DELETE":
            almacenamiento.eliminar_zona(zona_id)
            return jsonify({"eliminada": True})

        datos = request.get_json(silent=True) or {}
        actual = almacenamiento.obtener_zona(zona_id)
        combinado = {**actual, **datos}
        try:
            _validar_zona(combinado)
        except ValueError as err:
            return jsonify({"detail": str(err)}), 400
        campos = {
            campo: datos[campo]
            for campo in ("nombre", "tipo", "poligono", "centro_x", "centro_y", "radio_metros", "activa")
            if campo in datos
        }
        almacenamiento.actualizar_zona(zona_id, **campos)
        return jsonify(almacenamiento.obtener_zona(zona_id))

    @app.route("/api/config/zonas/<int:zona_id>/reglas", methods=["POST"])
    def api_config_crear_regla(zona_id):
        almacenamiento = _almacenamiento_o_404()
        if almacenamiento.obtener_zona(zona_id) is None:
            abort(404)
        datos = request.get_json(silent=True) or {}
        try:
            _validar_regla(datos)
        except ValueError as err:
            return jsonify({"detail": str(err)}), 400
        regla_id = almacenamiento.crear_regla(
            zona_id,
            hora_inicio=datos["hora_inicio"],
            hora_fin=datos["hora_fin"],
            dias_semana=datos.get("dias_semana", []),
            canal_notificacion=datos.get("canal_notificacion", "whatsapp"),
            destinatario=datos.get("destinatario", "").strip(),
            nombre=datos.get("nombre", "").strip(),
            activa=datos.get("activa", True),
        )
        return jsonify(almacenamiento.obtener_regla(regla_id)), 201

    @app.route("/api/config/reglas/<int:regla_id>", methods=["PUT", "DELETE"])
    def api_config_regla_detalle(regla_id):
        almacenamiento = _almacenamiento_o_404()
        if almacenamiento.obtener_regla(regla_id) is None:
            abort(404)
        if request.method == "DELETE":
            almacenamiento.eliminar_regla(regla_id)
            return jsonify({"eliminada": True})

        datos = request.get_json(silent=True) or {}
        actual = almacenamiento.obtener_regla(regla_id)
        combinado = {**actual, **datos}
        try:
            _validar_regla(combinado)
        except ValueError as err:
            return jsonify({"detail": str(err)}), 400
        campos = {
            campo: datos[campo]
            for campo in ("nombre", "hora_inicio", "hora_fin", "dias_semana", "canal_notificacion",
                          "destinatario", "activa")
            if campo in datos
        }
        almacenamiento.actualizar_regla(regla_id, **campos)
        return jsonify(almacenamiento.obtener_regla(regla_id))

    @app.route("/api/config/sincronizar", methods=["POST"])
    def api_config_sincronizar():
        """Fuerza un empujón inmediato de la configuración local pendiente
        hacia la nube (normalmente ocurre solo, en cada ciclo de
        sincronización de main.py) — para que la persona configurando vea
        de una que sí quedó reflejado, sin esperar hasta 60s."""
        almacenamiento = _almacenamiento_o_404()
        sincronizar_configuracion_local(almacenamiento, sincronizador.cliente_api)
        return jsonify({"ok": True})

    @app.route("/configurar")
    def configurar_index():
        return Response(_PAGINA_CONFIGURAR_INDEX, mimetype="text/html")

    @app.route("/configurar/<int:camara_id>")
    def configurar_camara(camara_id):
        return Response(_PAGINA_CONFIGURAR_CAMARA.replace("__CAMARA_ID__", str(camara_id)), mimetype="text/html")

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
<header><h1>SST Bavaria — Equipo Local (cámaras y grabaciones)</h1>
  <a href="/configurar" style="color:#93c5fd">Configurar zonas y horarios →</a>
</header>
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


_PAGINA_CONFIGURAR_INDEX = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Configurar zonas y horarios — SST Bavaria</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
  header { padding: 1rem 1.5rem; background: #1e2761; }
  header h1 { margin: 0; font-size: 1.1rem; }
  header a { color: #93c5fd; font-size: .85rem; }
  main { padding: 1.5rem; max-width: 800px; margin: 0 auto; }
  .lista { display: flex; flex-direction: column; gap: .5rem; }
  .lista a { display: block; background: #1e293b; border-radius: .5rem; padding: 1rem; color: #e2e8f0;
             text-decoration: none; }
  .lista a:hover { background: #253449; }
  .vacio { color: #94a3b8; font-size: .85rem; padding: 1rem 0; }
</style>
</head>
<body>
<header><h1>Configurar zonas y horarios</h1><a href="/">← Volver al visor</a></header>
<main>
  <p style="color:#94a3b8">Elige una cámara para dibujar sus zonas restringidas y definir en qué horarios
  avisan. Esto se guarda en este PC — no hace falta el dashboard en la nube.</p>
  <div id="lista-camaras" class="lista"></div>
</main>
<script>
async function cargar() {
  const resp = await fetch("/api/camaras");
  const camaras = await resp.json();
  const lista = document.getElementById("lista-camaras");
  if (camaras.length === 0) {
    lista.innerHTML = '<p class="vacio">Todavía no hay cámaras activas.</p>';
    return;
  }
  lista.innerHTML = "";
  camaras.forEach((c) => {
    const a = document.createElement("a");
    a.href = `/configurar/${c.id}`;
    a.textContent = `${c.nombre} →`;
    lista.appendChild(a);
  });
}
cargar();
</script>
</body>
</html>
"""


_PAGINA_CONFIGURAR_CAMARA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Configurar cámara — SST Bavaria</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
  header { padding: 1rem 1.5rem; background: #1e2761; display: flex; justify-content: space-between;
            align-items: center; }
  header h1 { margin: 0; font-size: 1.1rem; }
  header a { color: #93c5fd; font-size: .85rem; }
  main { padding: 1.5rem; max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: 1fr 380px;
         gap: 1.5rem; }
  @media (max-width: 900px) { main { grid-template-columns: 1fr; } }
  .lienzo-wrap { position: relative; background: #000; border-radius: .5rem; overflow: hidden; }
  .lienzo-wrap img, .lienzo-wrap canvas { display: block; width: 100%; }
  .lienzo-wrap canvas { position: absolute; top: 0; left: 0; cursor: crosshair; }
  .barra { display: flex; gap: .5rem; margin-bottom: .75rem; flex-wrap: wrap; align-items: center; }
  button, select, input { padding: .4rem .6rem; border-radius: .4rem; border: 1px solid #334155;
                           background: #0f172a; color: #e2e8f0; font-size: .85rem; }
  button { cursor: pointer; background: #2563eb; border-color: #2563eb; }
  button.secundario { background: #334155; border-color: #334155; }
  button.borrar { background: #b91c1c; border-color: #b91c1c; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  .panel { display: flex; flex-direction: column; gap: 1rem; }
  .tarjeta { background: #1e293b; border-radius: .5rem; padding: .85rem; }
  .tarjeta h3 { margin: 0 0 .5rem; font-size: .95rem; display: flex; justify-content: space-between; }
  .tarjeta .meta { color: #94a3b8; font-size: .78rem; margin-bottom: .5rem; }
  .regla { border-top: 1px solid #334155; padding-top: .5rem; margin-top: .5rem; font-size: .82rem; }
  .fila { display: flex; gap: .4rem; flex-wrap: wrap; align-items: center; margin-bottom: .35rem; }
  .fila label { font-size: .78rem; color: #94a3b8; display: flex; flex-direction: column; gap: .15rem; }
  .dias { display: flex; gap: .25rem; flex-wrap: wrap; }
  .dias label { flex-direction: row; align-items: center; gap: .2rem; color: #e2e8f0; }
  .vacio { color: #94a3b8; font-size: .85rem; }
  .estado { font-size: .78rem; color: #94a3b8; }
  .mensaje { font-size: .8rem; padding: .5rem; border-radius: .4rem; margin-bottom: .5rem; }
  .mensaje.error { background: #7f1d1d; color: #fecaca; }
  .mensaje.ok { background: #14532d; color: #bbf7d0; }
</style>
</head>
<body>
<header>
  <h1>Configurar zonas y horarios</h1>
  <a href="/configurar">← Todas las cámaras</a>
</header>
<main>
  <div>
    <div class="barra">
      <button id="btn-refrescar" type="button" class="secundario">Refrescar imagen</button>
      <button id="btn-nueva-zona" type="button">+ Nueva zona (polígono)</button>
      <button id="btn-cerrar-zona" type="button" class="secundario" disabled>Cerrar y guardar zona</button>
      <button id="btn-cancelar-zona" type="button" class="secundario" disabled>Cancelar</button>
    </div>
    <div id="mensaje-dibujo" class="mensaje" style="display:none"></div>
    <div class="lienzo-wrap">
      <img id="frame" src="/api/camaras/__CAMARA_ID__/frame.jpg" alt="Encuadre de la cámara">
      <canvas id="lienzo"></canvas>
    </div>
    <p class="vacio">Clic para marcar cada esquina del polígono; con 3 o más puntos, "Cerrar y guardar zona".</p>
  </div>
  <div class="panel">
    <div class="barra">
      <button id="btn-sincronizar" type="button" class="secundario">Sincronizar con la nube ahora</button>
    </div>
    <div id="mensaje-sync" class="mensaje" style="display:none"></div>
    <div id="lista-zonas"></div>
  </div>
</main>
<script>
const CAMARA_ID = __CAMARA_ID__;
const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
let zonas = [];
let dibujando = false;
let puntoActual = [];

function mostrarMensaje(id, texto, tipo) {
  const el = document.getElementById(id);
  el.textContent = texto;
  el.className = "mensaje " + tipo;
  el.style.display = texto ? "block" : "none";
}

function ajustarLienzo() {
  const img = document.getElementById("frame");
  const canvas = document.getElementById("lienzo");
  canvas.width = img.naturalWidth || img.clientWidth;
  canvas.height = img.naturalHeight || img.clientHeight;
  dibujar();
}

function dibujar() {
  const canvas = document.getElementById("lienzo");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  zonas.filter((z) => z.tipo === "poligono" && z.activa).forEach((z) => dibujarPoligono(ctx, z.poligono, "#22c55e"));
  if (dibujando && puntoActual.length > 0) {
    dibujarPoligono(ctx, puntoActual, "#facc15", true);
  }
}

function dibujarPoligono(ctx, puntos, color, abierto) {
  if (puntos.length === 0) return;
  ctx.strokeStyle = color;
  ctx.fillStyle = color + "33";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(puntos[0][0], puntos[0][1]);
  puntos.slice(1).forEach((p) => ctx.lineTo(p[0], p[1]));
  if (!abierto) { ctx.closePath(); ctx.fill(); }
  ctx.stroke();
  puntos.forEach((p) => {
    ctx.beginPath();
    ctx.arc(p[0], p[1], 4, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  });
}

document.getElementById("lienzo").addEventListener("click", (ev) => {
  if (!dibujando) return;
  const canvas = ev.target;
  const rect = canvas.getBoundingClientRect();
  const escalaX = canvas.width / rect.width;
  const escalaY = canvas.height / rect.height;
  const x = (ev.clientX - rect.left) * escalaX;
  const y = (ev.clientY - rect.top) * escalaY;
  puntoActual.push([Math.round(x), Math.round(y)]);
  document.getElementById("btn-cerrar-zona").disabled = puntoActual.length < 3;
  dibujar();
});

document.getElementById("btn-nueva-zona").addEventListener("click", () => {
  dibujando = true;
  puntoActual = [];
  document.getElementById("btn-cerrar-zona").disabled = true;
  document.getElementById("btn-cancelar-zona").disabled = false;
  document.getElementById("btn-nueva-zona").disabled = true;
  mostrarMensaje("mensaje-dibujo", "Haciendo clic sobre la imagen, marca cada esquina de la zona.", "ok");
});

document.getElementById("btn-cancelar-zona").addEventListener("click", () => {
  dibujando = false;
  puntoActual = [];
  document.getElementById("btn-cerrar-zona").disabled = true;
  document.getElementById("btn-cancelar-zona").disabled = true;
  document.getElementById("btn-nueva-zona").disabled = false;
  mostrarMensaje("mensaje-dibujo", "", "ok");
  dibujar();
});

document.getElementById("btn-cerrar-zona").addEventListener("click", async () => {
  const nombre = prompt("Nombre de la zona (ej. \\"Bodega de químicos\\"):");
  if (!nombre) return;
  const resp = await fetch(`/api/config/camaras/${CAMARA_ID}/zonas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre, tipo: "poligono", poligono: puntoActual, activa: true }),
  });
  const datos = await resp.json();
  if (!resp.ok) {
    mostrarMensaje("mensaje-dibujo", datos.detail || "No se pudo guardar la zona.", "error");
    return;
  }
  document.getElementById("btn-cancelar-zona").click();
  mostrarMensaje("mensaje-dibujo", "Zona guardada.", "ok");
  cargarZonas();
});

document.getElementById("btn-refrescar").addEventListener("click", () => {
  document.getElementById("frame").src = `/api/camaras/${CAMARA_ID}/frame.jpg?t=${Date.now()}`;
});

document.getElementById("btn-sincronizar").addEventListener("click", async () => {
  mostrarMensaje("mensaje-sync", "Sincronizando…", "ok");
  const resp = await fetch("/api/config/sincronizar", { method: "POST" });
  if (resp.ok) {
    mostrarMensaje("mensaje-sync", "Listo, sincronizado con la nube.", "ok");
    cargarZonas();
  } else {
    mostrarMensaje("mensaje-sync", "No se pudo sincronizar — revisa la conexión.", "error");
  }
});

function estadoSync(zona) {
  return zona.cloud_id ? "Sincronizada" : "Pendiente de sincronizar";
}

async function eliminarZona(zonaId) {
  if (!confirm("¿Eliminar esta zona y sus horarios? No se puede deshacer.")) return;
  await fetch(`/api/config/zonas/${zonaId}`, { method: "DELETE" });
  cargarZonas();
}

async function alternarZona(zonaId, activa) {
  await fetch(`/api/config/zonas/${zonaId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ activa: !activa }),
  });
  cargarZonas();
}

async function agregarRegla(zonaId) {
  const destinatario = prompt("Correo o WhatsApp que recibe la alerta:");
  if (!destinatario) return;
  const horaInicio = prompt("Hora de inicio (HH:MM), ej. 22:00:", "22:00");
  const horaFin = prompt("Hora de fin (HH:MM), ej. 06:00:", "06:00");
  if (!horaInicio || !horaFin) return;
  const canal = confirm("¿Aceptar = Correo, Cancelar = WhatsApp?") ? "correo" : "whatsapp";
  const resp = await fetch(`/api/config/zonas/${zonaId}/reglas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hora_inicio: horaInicio + ":00",
      hora_fin: horaFin + ":00",
      dias_semana: [0, 1, 2, 3, 4, 5, 6],
      canal_notificacion: canal,
      destinatario,
      activa: true,
    }),
  });
  const datos = await resp.json();
  if (!resp.ok) {
    alert(datos.detail || "No se pudo guardar el horario.");
    return;
  }
  cargarZonas();
}

async function eliminarRegla(reglaId) {
  if (!confirm("¿Eliminar este horario?")) return;
  await fetch(`/api/config/reglas/${reglaId}`, { method: "DELETE" });
  cargarZonas();
}

function tarjetaZona(zona) {
  const div = document.createElement("div");
  div.className = "tarjeta";
  const reglasHtml = zona.reglas.length
    ? zona.reglas.map((r) => `
        <div class="regla">
          ${DIAS.filter((_, i) => r.dias_semana.includes(i)).join(", ") || "(sin días)"} ·
          ${r.hora_inicio.slice(0, 5)}–${r.hora_fin.slice(0, 5)} · ${r.canal_notificacion} · ${r.destinatario}
          <button type="button" class="borrar" onclick="eliminarRegla(${r.id})" style="float:right">Borrar</button>
        </div>`).join("")
    : '<p class="vacio">Sin horarios — esta zona no dispara alertas todavía.</p>';
  div.innerHTML = `
    <h3>${zona.nombre} <span class="estado">${estadoSync(zona)}</span></h3>
    <div class="meta">${zona.tipo === "poligono" ? zona.poligono.length + " puntos" : "Punto y radio"} ·
      ${zona.activa ? "Activa" : "Desactivada"}</div>
    ${reglasHtml}
    <div class="barra" style="margin-top:.6rem">
      <button type="button" class="secundario" onclick="agregarRegla(${zona.id})">+ Horario</button>
      <button type="button" class="secundario" onclick="alternarZona(${zona.id}, ${zona.activa})">
        ${zona.activa ? "Desactivar" : "Activar"}</button>
      <button type="button" class="borrar" onclick="eliminarZona(${zona.id})">Eliminar zona</button>
    </div>`;
  return div;
}

async function cargarZonas() {
  const resp = await fetch(`/api/config/camaras/${CAMARA_ID}/zonas`);
  zonas = await resp.json();
  const lista = document.getElementById("lista-zonas");
  lista.innerHTML = "";
  if (zonas.length === 0) {
    lista.innerHTML = '<p class="vacio">Todavía no hay zonas — dibuja una sobre la imagen.</p>';
  } else {
    zonas.forEach((z) => lista.appendChild(tarjetaZona(z)));
  }
  dibujar();
}

document.getElementById("frame").addEventListener("load", ajustarLienzo);
if (document.getElementById("frame").complete) ajustarLienzo();
cargarZonas();
</script>
</body>
</html>
"""
