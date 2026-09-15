#!/bin/bash
# ============================================================
#  Instalador de un clic (o "un comando") del Equipo local de
#  camaras (Linux/Mac).
#
#  Que hace: crea el entorno, instala las dependencias, registra
#  el programa como servicio del sistema (arranca solo con el PC)
#  y lo deja corriendo ya mismo. Es seguro correrlo varias veces
#  (por ejemplo despues de una actualizacion) — no duplica nada.
#
#  Requisito unico, de una sola vez en este PC: tener Python 3.10+
#  instalado (viene de fabrica en la mayoria de Linux/Mac).
#
#  Uso: doble clic (si el gestor de archivos lo permite) o, desde
#  una terminal parado en esta carpeta:
#    ./instalar.sh
# ============================================================
set -e
cd "$(dirname "$0")"

echo ""
echo "=== Instalador del Equipo local de camaras SST Bavaria ==="
echo "Carpeta: $(pwd)"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: No se encontro Python 3 instalado en este PC."
    echo ""
    echo "Instalalo una sola vez con el gestor de paquetes del sistema, ej:"
    echo "  Ubuntu/Debian:  sudo apt install python3 python3-venv"
    echo ""
    echo "Despues de instalarlo, vuelve a correr este instalador."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "ERROR: No se encontro el archivo .env en esta carpeta."
    echo ""
    echo "Descargalo desde el dashboard: Sistema -> Equipo local -> boton"
    echo "\"Descargar .env\", y colocalo en esta misma carpeta (junto a este"
    echo "instalador) antes de volver a correrlo."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[1/4] Creando el entorno del programa..."
    python3 -m venv venv
else
    echo "[1/4] El entorno ya existia, se reutiliza."
fi

echo "[2/4] Instalando dependencias — la primera vez puede tardar varios"
echo "      minutos, es normal."
./venv/bin/pip install --upgrade pip >/dev/null
./venv/bin/pip install -r requirements.txt

echo "[3/4] Registrando el programa como servicio del sistema (puede pedir"
echo "      la contraseña de este usuario para instalar el servicio)..."
CARPETA_ACTUAL="$(pwd)"
CARPETA_PADRE="$(dirname "$CARPETA_ACTUAL")"
USUARIO_ACTUAL="$(whoami)"
# WorkingDirectory = la carpeta padre de esta (equipo_local), no esta misma
# — necesario para que "-m equipo_local.main" encuentre el paquete (ver
# systemd/equipo-local-camaras.service).
sed \
    -e "s#WorkingDirectory=/opt/sstbavaria-camaras#WorkingDirectory=${CARPETA_PADRE}#" \
    -e "s#EnvironmentFile=/opt/sstbavaria-camaras/equipo_local/.env#EnvironmentFile=${CARPETA_ACTUAL}/.env#" \
    -e "s#ExecStart=/opt/sstbavaria-camaras/equipo_local/venv/bin/python#ExecStart=${CARPETA_ACTUAL}/venv/bin/python#" \
    -e "s#User=camaras#User=${USUARIO_ACTUAL}#" \
    systemd/equipo-local-camaras.service | sudo tee /etc/systemd/system/equipo-local-camaras.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now equipo-local-camaras

echo "[4/4] Listo, verificando que haya arrancado..."
sleep 2
sudo systemctl --no-pager status equipo-local-camaras || true

echo ""
echo "================================================================"
echo " LISTO. El equipo local ya esta instalado y corriendo."
echo " Arrancara solo cada vez que se prenda este PC, sin que nadie"
echo " tenga que abrir nada."
echo ""
echo " Para ver las camaras en vivo y las grabaciones desde un"
echo " navegador (en la misma red de la planta):"
echo "   http://sstbavaria-camaras.local:8090"
echo "================================================================"
echo ""
