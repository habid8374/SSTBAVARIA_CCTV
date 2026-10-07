@echo off
setlocal

REM ============================================================
REM  Instalador del Equipo local de camaras GuardIA (Windows).
REM
REM  Lo genera el dashboard (Sistema -> Equipo local -> boton
REM  "Instalador Windows (.exe)") para UN equipo en particular: ya
REM  trae su configuracion (.env) adentro. Doble clic y listo:
REM    1. descarga el programa ya compilado (equipo_local.exe,
REM       no hace falta Python),
REM    2. lo deja en C:\GuardIA\equipo_local,
REM    3. lo registra como Tarea Programada (arranca solo con el PC)
REM       y lo inicia, esperando a confirmar que arranco.
REM
REM  Sirve tambien para actualizar o reinstalar: volver a correrlo
REM  reemplaza el programa y conserva grabaciones y zonas.
REM
REM  Sin internet hacia GitHub: dejar equipo_local-windows.zip
REM  (enlace "programa por separado" en Sistema -> Equipo local)
REM  junto a este archivo y
REM  se usa ese en vez de descargarlo.
REM
REM  No compartir este archivo: trae la API key del equipo.
REM ============================================================

REM Pedir permisos de Administrador si hace falta (los necesita la
REM Tarea Programada) - igual que instalar_exe.bat.
fsutil dirty query %systemdrive% >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Pidiendo permisos de Administrador...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "GUARDIA_ARCHIVO=%~f0"
set "GUARDIA_INSTALADOR=%~dp0"
set "GUARDIA_CARPETA=C:\GuardIA\equipo_local"
set "GUARDIA_URL=__URL_PAQUETE__"
set "GUARDIA_ENV=__ENV_BASE64__"

REM El resto lo hace PowerShell: el script esta al final de este mismo
REM archivo, despues de la marca de dos numerales + PS.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s = [IO.File]::ReadAllText($env:GUARDIA_ARCHIVO); iex $s.Substring($s.LastIndexOf('#' + '#PS'))"
set "RESULTADO=%errorlevel%"
echo.
pause
exit /b %RESULTADO%

##PS
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$tarea = 'GuardIA-EquipoLocalCamaras'
$carpeta = $env:GUARDIA_CARPETA

Write-Host ''
Write-Host '=== Instalador del Equipo local de camaras GuardIA ==='
Write-Host "Carpeta: $carpeta"
Write-Host ''

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    New-Item -ItemType Directory -Force -Path $carpeta | Out-Null

    # Reinstalacion o actualizacion: se detiene la version que este
    # corriendo para poder reemplazar equipo_local.exe.
    if (Get-ScheduledTask -TaskName $tarea -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $tarea -ErrorAction SilentlyContinue
    }
    Get-Process -Name equipo_local -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2

    $zip = Join-Path $env:GUARDIA_INSTALADOR 'equipo_local-windows.zip'
    $descargado = $false
    if (Test-Path -LiteralPath $zip) {
        Write-Host '[1/4] Usando equipo_local-windows.zip de esta carpeta (no se descarga).'
    } else {
        Write-Host '[1/4] Descargando el programa (unos 300 MB, puede tardar varios minutos)...'
        $zip = Join-Path $env:TEMP 'guardia-equipo_local-windows.zip'
        Invoke-WebRequest -Uri $env:GUARDIA_URL -OutFile $zip -UseBasicParsing
        $descargado = $true
    }

    Write-Host '[2/4] Copiando el programa a la carpeta...'
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $archivo = [IO.Compression.ZipFile]::OpenRead($zip)
    try {
        foreach ($entrada in $archivo.Entries) {
            if (-not $entrada.Name) { continue }
            # El paquete trae todo dentro de una carpeta equipo_local/: se
            # saca ese primer nivel para que quede directo en $carpeta.
            $relativa = $entrada.FullName -replace '^[^/\\]+[/\\]', ''
            $destino = Join-Path $carpeta $relativa
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destino) | Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entrada, $destino, $true)
        }
    } finally {
        $archivo.Dispose()
    }
    if ($descargado) { Remove-Item -LiteralPath $zip -ErrorAction SilentlyContinue }
    [IO.File]::WriteAllBytes((Join-Path $carpeta '.env'), [Convert]::FromBase64String($env:GUARDIA_ENV))

    Write-Host '[3/4] Registrando el programa para que arranque solo con el PC...'
    & (Join-Path $carpeta 'windows\instalar_tarea_programada_exe.ps1')

    Write-Host '[4/4] Iniciando y esperando a que arranque (hasta 5 minutos)...'
    $log = Join-Path $carpeta 'equipo_local.log'
    # Lee el log aunque el programa lo tenga abierto escribiendo; si no se
    # puede leer en ese instante, devuelve vacio y se reintenta en 5 s.
    function Leer-Log {
        try {
            $flujo = [IO.File]::Open($log, 'Open', 'Read', 'ReadWrite, Delete')
            $lector = New-Object IO.StreamReader($flujo)
            $contenido = $lector.ReadToEnd()
            $lector.Close()
            return [string]$contenido
        } catch {
            return ''
        }
    }
    $previo = (Leer-Log).Length
    Start-ScheduledTask -TaskName $tarea
    $iniciado = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 5
        $texto = Leer-Log
        if ($texto.Length -lt $previo) { $previo = 0 }  # el log se roto
        $nuevo = $texto.Substring($previo)
        if ($nuevo -match 'Error fatal|Error importando') { break }
        if ($nuevo -match 'Equipo local iniciado') { $iniciado = $true; break }
    }

    if (-not $iniciado) {
        Write-Host ''
        Write-Host 'ATENCION: el programa quedo instalado pero no confirmo que arranco.' -ForegroundColor Yellow
        Write-Host "Ultimas lineas de $log :" -ForegroundColor Yellow
        if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Tail 20 }
        exit 1
    }

    Write-Host ''
    Write-Host '================================================================' -ForegroundColor Green
    Write-Host ' LISTO. El equipo local ya esta instalado y corriendo.' -ForegroundColor Green
    Write-Host ' Arranca solo cada vez que se prenda este PC (Tarea Programada'
    Write-Host " $tarea), sin que nadie tenga que abrir nada."
    Write-Host ''
    Write-Host ' En el dashboard (Sistema -> Equipo local) el equipo debe pasar'
    Write-Host ' a "Conectado" en un par de minutos.'
    Write-Host ''
    Write-Host ' Camaras en vivo y grabaciones, desde la red de la planta:'
    Write-Host '   http://guardia-camaras.local:8090'
    Write-Host '================================================================' -ForegroundColor Green
    exit 0
} catch {
    Write-Host ''
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
