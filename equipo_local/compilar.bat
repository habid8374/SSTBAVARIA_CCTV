@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

REM ============================================================
REM  Compila equipo_local en un .exe standalone (equipo_local.exe)
REM  que ya trae Python y todas las dependencias adentro - el PC
REM  final de la planta no necesita tener Python instalado.
REM
REM  Se corre UNA VEZ en un PC de "armado" (por ejemplo tu PC de
REM  casa) que ya tenga el entorno de instalar.bat funcionando -
REM  no en el PC final de la planta. El resultado (equipo_local.exe,
REM  en esta misma carpeta) se copia junto con instalar_exe.bat y
REM  el .env al PC final - ver instalar_exe.bat.
REM
REM  Requisito: haber corrido antes instalar.bat en este PC (para
REM  tener el entorno "venv" con las dependencias ya instaladas).
REM
REM  Uso: doble clic, o desde una terminal parado en esta carpeta:
REM    compilar.bat
REM ============================================================

cd /d "%~dp0"
echo.
echo === Compilando equipo_local.exe ===
echo Carpeta: %cd%
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERROR: No se encontro el entorno "venv" en esta carpeta.
    echo.
    echo Corre primero instalar.bat una vez en este PC - eso crea el
    echo entorno e instala las dependencias que compilar.bat necesita.
    pause
    exit /b 1
)

echo [1/2] Instalando PyInstaller en el entorno...
".\venv\Scripts\pip.exe" install -r requirements-build.txt
if errorlevel 1 (
    echo.
    echo ERROR instalando PyInstaller - revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo [2/2] Compilando - la primera vez puede tardar varios minutos,
echo       es normal. No cierres esta ventana.
".\venv\Scripts\pyinstaller.exe" --noconfirm --onefile --console ^
    --name equipo_local ^
    --paths ".." ^
    --collect-all ultralytics ^
    --collect-all torch ^
    --collect-all torchvision ^
    --collect-all cv2 ^
    --hidden-import zeroconf ^
    entry_point.py
if errorlevel 1 (
    echo.
    echo ERROR compilando - revisa el mensaje de arriba.
    pause
    exit /b 1
)

copy /y "dist\equipo_local.exe" "equipo_local.exe" >nul

echo.
echo ================================================================
echo  LISTO. Se genero equipo_local.exe en esta carpeta.
echo.
echo  Para instalar en el PC final de la planta: copia a ese PC
echo  equipo_local.exe, instalar_exe.bat y el archivo .env (los tres
echo  juntos en una carpeta), y corre instalar_exe.bat ahi - ese PC
echo  final NO necesita tener Python instalado.
echo ================================================================
echo.
pause
