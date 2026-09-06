# Registra la version COMPILADA (equipo_local.exe, ver ..\compilar.bat) del
# equipo local de camaras como una Tarea Programada de Windows que arranca
# sola con el PC y corre en segundo plano (sin ventana visible).
#
# A diferencia de instalar_tarea_programada.ps1 (version con Python +
# venv), esta version no necesita resolver ninguna carpeta de trabajo
# especial: el .exe ya trae Python y las dependencias adentro, y
# equipo_local\rutas.py ubica el .env/log/grabaciones junto al .exe real
# usando sys.executable (no __file__, que en un .exe "onefile" apunta a una
# carpeta temporal que se borra al cerrar el programa).
#
# Uso (PowerShell como Administrador, parado en la carpeta equipo_local/):
#   .\windows\instalar_tarea_programada_exe.ps1

$ErrorActionPreference = "Stop"

$carpeta = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $carpeta "equipo_local.exe"

if (-not (Test-Path $exe)) {
    Write-Error "No se encontro $exe - compila primero con compilar.bat (en un PC con Python instalado) y copia equipo_local.exe a esta carpeta."
    exit 1
}

$accion = New-ScheduledTaskAction -Execute $exe -WorkingDirectory $carpeta
$disparador = New-ScheduledTaskTrigger -AtStartup
# MultipleInstances: el Programador de tareas de Windows solo admite
# Parallel, Queue o IgnoreNew - se deja en IgnoreNew (el default) para no
# correr dos veces el programa a la vez. Para que "Ejecutar" nunca quede
# sin hacer nada porque Windows cree que ya hay una instancia corriendo, se
# detiene explicitamente cualquier instancia vieja despues de registrar.
$configuracion = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask `
    -TaskName "SSTBavaria-EquipoLocalCamaras" `
    -Action $accion `
    -Trigger $disparador `
    -Settings $configuracion `
    -Principal $principal `
    -Description "Equipo local de camaras IA de SST Bavaria (version compilada) - detecta personas en zonas restringidas y reporta al dashboard." `
    -Force

Stop-ScheduledTask -TaskName "SSTBavaria-EquipoLocalCamaras" -ErrorAction SilentlyContinue

# Activa el historial de tareas de Windows (viene deshabilitado por
# defecto) — asi la pestana "Historial" del Programador de tareas muestra
# los intentos reales y sus errores, en vez de aparecer vacia.
wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true 2>$null

Write-Host "Tarea programada registrada. Se puede iniciar ahora con:"
Write-Host "  Start-ScheduledTask -TaskName SSTBavaria-EquipoLocalCamaras"
