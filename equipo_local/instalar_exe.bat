@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

REM ============================================================
REM  Instalador de la version COMPILADA del Equipo local de
REM  camaras (Windows) - para el PC final de la planta.
REM
REM  A diferencia de instalar.bat, este NO necesita tener Python
REM  instalado en este PC: usa equipo_local.exe, que ya trae todo
REM  adentro. Ese .exe se genera una sola vez en otro PC (de
REM  armado) con compilar.bat, y viaja junto con esta carpeta.
REM
REM  Uso: doble clic (pide permisos de Administrador solo) o,
REM  desde una terminal parado en esta carpeta:
REM    instalar_exe.bat
REM ============================================================

REM --- Pedir permisos de Administrador si hace falta (los necesita
REM     la Tarea Programada) - "fsutil dirty query" no depende de
REM     ningun servicio de Windows, a diferencia de "net session".
fsutil dirty query %systemdrive% >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Pidiendo permisos de Administrador...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo.
echo === Instalador del Equipo local de camaras GuardIA (version compilada) ===
echo Carpeta: %cd%
echo.

if not exist "equipo_local.exe" (
    echo ERROR: No se encontro equipo_local.exe en esta carpeta.
    echo.
    echo Este instalador es para la version compilada del programa - genera
    echo equipo_local.exe con compilar.bat en otro PC y copialo a esta
    echo misma carpeta antes de volver a correr este instalador.
    echo.
    echo Si preferis la version normal, que si necesita Python instalado
    echo en este PC, usa instalar.bat en su lugar.
    pause
    exit /b 1
)

if not exist ".env" (
    echo ERROR: No se encontro el archivo .env en esta carpeta.
    echo.
    echo Descargalo desde el dashboard: Sistema -^> Equipo local -^> boton
    echo "Descargar equipo_local .zip" de la fila del equipo, y copia el
    echo archivo .env de ahi a esta misma carpeta.
    pause
    exit /b 1
)

echo [1/2] Registrando el programa para que arranque solo con el PC...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\windows\instalar_tarea_programada_exe.ps1"
if errorlevel 1 (
    echo.
    echo ERROR registrando la tarea programada - revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo [2/2] Iniciando ahora...
powershell -NoProfile -Command "Start-ScheduledTask -TaskName GuardIA-EquipoLocalCamaras"

echo.
echo ================================================================
echo  LISTO. El equipo local ya esta instalado y corriendo.
echo  Arrancara solo cada vez que se prenda este PC, sin que nadie
echo  tenga que abrir nada ni tener Python instalado.
echo.
echo  Para ver las camaras en vivo y las grabaciones desde un
echo  navegador (en la misma red de la planta):
echo    http://guardia-camaras.local:8090
echo ================================================================
echo.
pause
