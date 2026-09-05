@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

REM ============================================================
REM  Instalador de un clic del Equipo local de camaras (Windows)
REM
REM  Que hace: crea el entorno, instala las dependencias, registra
REM  el programa como Tarea Programada (arranca solo con el PC) y
REM  lo deja corriendo ya mismo. Es seguro correrlo varias veces
REM  (por ejemplo despues de una actualizacion) - no duplica nada.
REM
REM  Requisito unico, de una sola vez en este PC: tener Python
REM  instalado (ver mensaje de error abajo si falta). Todo lo demas
REM  lo hace este script solo.
REM ============================================================

REM --- Pedir permisos de Administrador si hace falta (los necesita
REM     la Tarea Programada) - vuelve a abrirse solo, pidiendo el
REM     permiso de Windows. Se usa "fsutil dirty query" en vez de
REM     "net session" para detectar el permiso: "net session" depende
REM     de un servicio de Windows (Servidor) que en algunos PCs esta
REM     apagado, y ahi falla siempre aunque ya seas Administrador -
REM     "fsutil dirty query" no depende de ningun servicio.
fsutil dirty query %systemdrive% >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Pidiendo permisos de Administrador...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo.
echo === Instalador del Equipo local de camaras SST Bavaria ===
echo Carpeta: %cd%
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: No se encontro Python instalado en este PC.
    echo.
    echo Instalalo una sola vez desde: https://www.python.org/downloads/
    echo IMPORTANTE: en el instalador, marca la casilla "Add python.exe to PATH"
    echo antes de darle a Instalar.
    echo.
    echo Despues de instalar Python, vuelve a hacer doble clic en este archivo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo ERROR: No se encontro el archivo .env en esta carpeta.
    echo.
    echo Descargalo desde el dashboard: Sistema -^> Equipo local -^> boton
    echo "Descargar .env", y colocalo en esta misma carpeta (junto a este
    echo instalador) antes de volver a correrlo.
    pause
    exit /b 1
)

if not exist "venv" (
    echo [1/4] Creando el entorno del programa...
    python -m venv venv
) else (
    echo [1/4] El entorno ya existia, se reutiliza.
)

echo [2/4] Instalando dependencias - la primera vez puede tardar varios
echo       minutos, es normal. No cierres esta ventana.
".\venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".\venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR instalando las dependencias - revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo [3/4] Registrando el programa para que arranque solo con el PC...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\windows\instalar_tarea_programada.ps1"
if errorlevel 1 (
    echo.
    echo ERROR registrando la tarea programada - revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo [4/4] Iniciando ahora...
powershell -NoProfile -Command "Start-ScheduledTask -TaskName SSTBavaria-EquipoLocalCamaras"

echo.
echo ================================================================
echo  LISTO. El equipo local ya esta instalado y corriendo.
echo  Arrancara solo cada vez que se prenda este PC, sin que nadie
echo  tenga que abrir nada.
echo.
echo  Para ver las camaras en vivo y las grabaciones desde un
echo  navegador (en la misma red de la planta):
echo    http://sstbavaria-camaras.local:8090
echo ================================================================
echo.
pause
