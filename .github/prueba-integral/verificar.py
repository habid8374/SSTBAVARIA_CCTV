"""Revisa el resultado de la prueba integral escenario por escenario y
escribe un informe en Markdown (también al resumen de GitHub Actions). Sale
con código 1 si algún resultado obligatorio no se cumple.

Uso (desde la raíz del repo):
  python .github/prueba-integral/verificar.py <carpeta_estado> <log_equipo_local> <hora_zona_local>
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone as tz
from pathlib import Path

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

import requests  # noqa: E402
from django.utils import timezone  # noqa: E402

from camaras_ia.models import ConsumoIA, EquipoLocal, EventoDetectado, ZonaRestringida  # noqa: E402

carpeta = Path(sys.argv[1])
log_equipo = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
hora_zona_local = datetime.fromtimestamp(float(sys.argv[3]), tz=tz.utc)
ids = json.loads((carpeta / "ids.json").read_text())


def _jsonl(nombre):
    archivo = carpeta / nombre
    if not archivo.exists():
        return []
    return [json.loads(linea) for linea in archivo.read_text(encoding="utf-8").splitlines() if linea.strip()]


llamadas_claude = _jsonl("claude_llamadas.jsonl")
pushes = _jsonl("pushes.jsonl")
filas = []
fallas = []


def comprobar(escenario, descripcion, ok, detalle="", obligatorio=True):
    estado = "✅" if ok else ("❌" if obligatorio else "⚠️")
    filas.append(f"| {escenario} | {descripcion} | {estado} | {detalle} |")
    if obligatorio and not ok:
        fallas.append(f"{escenario}: {descripcion} ({detalle})")


def eventos(numero):
    return EventoDetectado.objects.filter(camara_id=ids["camaras"][str(numero)]).order_by("timestamp")


def pushes_de(texto):
    return [p for p in pushes if texto in p["cuerpo"] or texto in p["titulo"]]


def conectada(nombre):
    return f"Conectado a {nombre}" in log_equipo


# --- Equipo local -----------------------------------------------------------
equipo = EquipoLocal.objects.get(pk=ids["equipo"])
comprobar(
    "Equipo local",
    "Sincroniza con el backend (Conectado en el dashboard)",
    equipo.ultima_conexion is not None and timezone.now() - equipo.ultima_conexion < timedelta(minutes=3),
    f"última conexión {equipo.ultima_conexion:%H:%M:%S}" if equipo.ultima_conexion else "nunca",
)

# --- Cámara 1: alerta + IA que detecta ---------------------------------------
ev1 = list(eventos(1))
comprobar("Cam 1", "Persona en zona con horario vigente → eventos con alerta",
          len(ev1) >= 3 and all(e.disparo_alerta and e.zona for e in ev1), f"{len(ev1)} eventos")
comprobar("Cam 1", "Regla por correo: queda registrado el resultado del envío",
          bool(ev1) and all(e.canal_notificacion == "correo" and e.notificacion_detalle for e in ev1),
          (ev1[0].notificacion_detalle[:70] if ev1 else ""))
detectados_1 = [e for e in ev1 if e.tipos_ia.filter(pk=ids["tipos_ia"]["1"]).exists()]
comprobar("Cam 1", "La IA marca \"Sin casco\" en los eventos que revisa", len(detectados_1) >= 1,
          f"{len(detectados_1)} eventos con Sin casco")
consumo_1 = ConsumoIA.objects.filter(camara_id=ids["camaras"]["1"]).count()
sin_ia_1 = [e for e in ev1 if "Cuota" in e.ia_error or "Tope" in e.ia_error]
comprobar("Cam 1", "Cuota de IA por cámara: máx. 3 llamadas, después se frena",
          consumo_1 <= 3 and (len(ev1) <= consumo_1 or len(sin_ia_1) >= 1),
          f"{consumo_1} llamadas a Claude, {len(sin_ia_1)} eventos frenados por cuota/tope")
avisos_ia_1 = pushes_de("Alerta IA — Cam 1")
comprobar("Cam 1", "Aviso push de la IA, sin repetir en 10 min", len(avisos_ia_1) == 1, f"{len(avisos_ia_1)} avisos")

# --- Cámara 2: IA revisa pero no detecta --------------------------------------
ev2 = list(eventos(2))
analizados_2 = [e for e in ev2 if e.ia_analizado_en and not e.ia_error]
comprobar("Cam 2", "Persona en zona → eventos con alerta",
          len(ev2) >= 3 and all(e.disparo_alerta for e in ev2), f"{len(ev2)} eventos")
comprobar("Cam 2", "La IA revisa y no marca nada (no aplica)",
          len(analizados_2) >= 1 and all(not e.tipos_ia.exists() for e in analizados_2),
          f"{len(analizados_2)} revisados por la IA")
comprobar("Cam 2", "Sin aviso de IA", not pushes_de("Alerta IA — Cam 2"), "")

# --- Aislamiento de alertas IA por cámara --------------------------------------
catalogos_validos = {(ids["tipos_ia"]["1"],), (ids["tipos_ia"]["2"],), (ids["tipos_ia"]["8"],)}
catalogos = {tuple(sorted(llamada["catalogo"])) for llamada in llamadas_claude}
comprobar("IA por cámara", "Cada llamada a Claude lleva solo las alertas de su cámara, con la foto",
          bool(llamadas_claude) and catalogos <= catalogos_validos and all(ll["con_imagen"] for ll in llamadas_claude),
          f"{len(llamadas_claude)} llamadas")
camaras_sin_ia = [3, 4, 5, 9, 10]
consumo_sin_ia = ConsumoIA.objects.filter(camara_id__in=[ids["camaras"][str(n)] for n in camaras_sin_ia]).count()
comprobar("IA por cámara", "Cámaras sin alertas de IA no gastan", consumo_sin_ia == 0, f"{consumo_sin_ia} llamadas")

# --- Cámara 3: zona sin nadie, después zona creada en el equipo local ----------
ev3 = list(eventos(3))
antes_3 = [e for e in ev3 if e.timestamp < hora_zona_local]
despues_3 = [e for e in ev3 if e.timestamp >= hora_zona_local]
comprobar("Cam 3", "Zona dibujada donde no hay nadie → sin eventos", not antes_3, f"{len(antes_3)} eventos")
zona_local = ZonaRestringida.objects.filter(camara_id=ids["camaras"]["3"], nombre="Zona creada en el equipo local").first()
comprobar("Cam 3", "Zona creada en el visor del equipo local aparece en el dashboard",
          zona_local is not None and zona_local.reglas.exists(), "")
comprobar("Cam 3", "Y desde ahí genera alertas",
          len(despues_3) >= 1 and all(e.disparo_alerta for e in despues_3), f"{len(despues_3)} eventos")

# --- Cámara 4: fuera de horario ------------------------------------------------
ev4 = list(eventos(4))
comprobar("Cam 4", f"Persona en zona fuera de horario ({ids['fuera_de_horario']}) → evento sin alerta",
          len(ev4) >= 1 and not any(e.disparo_alerta for e in ev4), f"{len(ev4)} eventos, ninguno con alerta")
comprobar("Cam 4", "Sin aviso push", not pushes_de("Cam 4"), "")

# --- Cámaras 5, 6, 7 ----------------------------------------------------------
comprobar("Cam 5", "Cámara sin personas → sin eventos", conectada("Cam 5 Vacía") and not eventos(5).exists(),
          f"conectada={conectada('Cam 5 Vacía')}, {eventos(5).count()} eventos")
comprobar("Cam 6", "Cámara desactivada en el dashboard → no se conecta",
          not conectada("Cam 6 Inactiva") and not eventos(6).exists(), "")
comprobar("Cam 7", "Cámara sin red → reintenta sola, sin afectar a las demás",
          "No se pudo conectar a Cam 7 Sin red" in log_equipo and not eventos(7).exists(), "")

# --- Cámara 8: Claude lento ----------------------------------------------------
ev8 = list(eventos(8))
timeouts_8 = log_equipo.count("No se pudo reportar el evento de Cam 8 IA lenta")
comprobar("Cam 8", "Claude lento (13 s): el evento igual queda con alerta y revisado por la IA",
          len(ev8) >= 1 and all(e.disparo_alerta for e in ev8)
          and any(e.tipos_ia.filter(pk=ids["tipos_ia"]["8"]).exists() for e in ev8),
          f"{len(ev8)} eventos")
comprobar("Cam 8", "El equipo local no se queda esperando a Claude (la IA termina en segundo plano)",
          timeouts_8 == 0, f"{timeouts_8} reportes cortados por tiempo")

# --- Cámara 9: retraso de la detección -----------------------------------------
aparicion = carpeta / "aparecio.txt"
ev9 = list(eventos(9))
if aparicion.exists() and ev9:
    aparecio = datetime.fromtimestamp(float(aparicion.read_text()), tz=tz.utc)
    primero = next((e for e in ev9 if e.timestamp >= aparecio), None)
    retraso = (primero.timestamp - aparecio).total_seconds() if primero else None
    comprobar("Cam 9", "Persona que aparece de golpe → alerta en menos de 15 s",
              retraso is not None and retraso < 15, f"{retraso:.1f} s" if retraso is not None else "sin evento")
    comprobar("Cam 9", "Ningún evento mientras la cámara estaba vacía",
              not [e for e in ev9 if e.timestamp < aparecio], "")
else:
    comprobar("Cam 9", "Persona que aparece de golpe → alerta", False, "sin aparición o sin eventos")

# --- Cámara 10: primer plano (informativo) --------------------------------------
ev10 = eventos(10).count()
comprobar("Cam 10", "Personas cortadas por el borde de abajo, zona hasta el borde → eventos",
          ev10 >= 1, f"{ev10} eventos", obligatorio=False)

# --- Avisos push de alertas de zona ----------------------------------------------
avisos_zona = len(pushes_de("Se detectó una persona"))
comprobar("Avisos", "Un aviso push por cada evento con alerta de zona", avisos_zona >= 1,
          f"{avisos_zona} avisos", obligatorio=True)

# --- API del dashboard (lo que ve la pantalla) -----------------------------------
base = "http://127.0.0.1:8000"
token = requests.post(f"{base}/api/auth/login/", json={"username": "admin", "password": "clave-prueba-integral"},
                      timeout=10).json()["token"]
cabeceras = {"Authorization": f"Token {token}"}
consumo = requests.get(f"{base}/api/camaras-ia/dashboard/consumo-ia/", headers=cabeceras, timeout=10)
equipos = requests.get(f"{base}/api/camaras-ia/dashboard/equipos-locales/", headers=cabeceras, timeout=10)
lista = requests.get(f"{base}/api/camaras-ia/dashboard/eventos/", headers=cabeceras, timeout=10)
datos_consumo = consumo.json() if consumo.ok else {}
comprobar("Dashboard", "Sistema → Consumo de Claude muestra el gasto y el reparto por cámara",
          consumo.ok and len(datos_consumo.get("por_camara", [])) >= 3,
          f"gasto USD {datos_consumo.get('gastado_usd')} de {datos_consumo.get('tope_usd')}")
comprobar("Dashboard", "Sistema → Equipo local en verde (Conectado)",
          equipos.ok and any(e.get("conectado") for e in equipos.json()), "")
comprobar("Dashboard", "Lista de eventos responde", lista.ok, f"HTTP {lista.status_code}")

# --- Resumen por cámara ------------------------------------------------------------
resumen = ["", "| Cámara | Eventos | Con alerta | Revisados por IA | Llamadas a Claude |", "|---|---|---|---|---|"]
for numero in range(1, 11):
    ev = eventos(numero)
    resumen.append(
        f"| {numero} | {ev.count()} | {ev.filter(disparo_alerta=True).count()} | "
        f"{ev.exclude(ia_analizado_en=None).filter(ia_error='').count()} | "
        f"{ConsumoIA.objects.filter(camara_id=ids['camaras'][str(numero)]).count()} |"
    )

informe = "\n".join(
    ["## Prueba integral: cámaras y alertas", "", "| Escenario | Qué se comprueba | Resultado | Detalle |",
     "|---|---|---|---|", *filas, *resumen, ""]
)
print(informe)
(carpeta / "informe.md").write_text(informe, encoding="utf-8")
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as resumen_gh:
        resumen_gh.write(informe + "\n")
if fallas:
    print("\nFALLAS:\n- " + "\n- ".join(fallas))
    sys.exit(1)
