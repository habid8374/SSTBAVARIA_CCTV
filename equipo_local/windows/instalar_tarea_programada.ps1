# Registra el equipo local de camaras como una Tarea Programada de Windows
# que arranca sola con el PC y corre en segundo plano (sin ventana visible).
#
# Uso (PowerShell como Administrador, parado en la carpeta equipo_local/):
#   .\windows\instalar_tarea_programada.ps1
#
# Requiere haber creado antes el entorno virtual e instalado dependencias:
#   python -m venv venv
#   .\venv\Scripts\pip install -r requirements.txt
# y haber configurado el archivo .env (ver README.md) en esta misma carpeta.

$ErrorActionPreference = "Stop"

$carpeta = Split-Path -Parent $PSScriptRoot
$carpeta_padre = Split-Path -Parent $carpeta
$python = Join-Path $carpeta "venv\Scripts\pythonw.exe"

if (-not (Test-Path $python)) {
    Write-Error "No se encontro $python - crea antes el entorno virtual (ver README.md)."
    exit 1
}

# La carpeta de trabajo tiene que ser la carpeta *padre* de equipo_local
# (no equipo_local mismo) para que "-m equipo_local.main" encuentre el
# paquete — Python solo busca "equipo_local" como subcarpeta de la carpeta
# de trabajo. El .env y demas rutas relativas del programa no dependen de
# esto (ver main.py: el .env se carga con ruta explicita).
$accion = New-ScheduledTaskAction -Execute $python -Argument "-m equipo_local.main" -WorkingDirectory $carpeta_padre
$disparador = New-ScheduledTaskTrigger -AtStartup
# MultipleInstances: el Programador de tareas de Windows solo admite
# Parallel, Queue o IgnoreNew (no existe un valor "matar la vieja y arrancar
# limpia" en la API real, aunque asi lo sugiera algun ejemplo viejo). Se deja
# en IgnoreNew (el default) para no correr dos veces el programa a la vez.
# Para que "Ejecutar" nunca quede sin hacer nada porque Windows cree que ya
# hay una instancia corriendo (por ejemplo colgada de un intento anterior),
# se hace explicito el "matar antes de arrancar": cada vez que este script
# se corre (instalar.bat), se detiene cualquier instancia vieja de la tarea
# antes de que instalar.bat la vuelva a iniciar.
$configuracion = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask `
    -TaskName "SSTBavaria-EquipoLocalCamaras" `
    -Action $accion `
    -Trigger $disparador `
    -Settings $configuracion `
    -Principal $principal `
    -Description "Equipo local de camaras IA de SST Bavaria - detecta personas en zonas restringidas y reporta al dashboard." `
    -Force

# Register-ScheduledTask solo actualiza la definicion de la tarea, no mata
# una instancia que ya este corriendo con la configuracion anterior — se
# detiene aca para que instalar.bat siempre arranque una limpia despues.
Stop-ScheduledTask -TaskName "SSTBavaria-EquipoLocalCamaras" -ErrorAction SilentlyContinue

# Activa el historial de tareas de Windows (viene deshabilitado por
# defecto) — asi la pestana "Historial" del Programador de tareas muestra
# los intentos reales y sus errores, en vez de aparecer vacia.
wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true 2>$null

Write-Host "Tarea programada registrada. Se puede iniciar ahora con:"
Write-Host "  Start-ScheduledTask -TaskName SSTBavaria-EquipoLocalCamaras"
