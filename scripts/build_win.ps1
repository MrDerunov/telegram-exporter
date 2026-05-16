# Windows build: PyInstaller --onefile --console → zip.
# Консольное приложение tg-exporter (Click CLI), entry point: tg_exporter_cli/main.py.

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root "..")

# Версия для вшивания в бинарник
$version = $env:TG_EXPORTER_VERSION
if (!$version) { $version = "0.0.0" }
"VERSION = `"$version`"" | Out-File -Encoding utf8 -FilePath tg_exporter_cli\_version.py
Write-Host "Build version: $version"

# Установка PyInstaller и зависимостей проекта
python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install pyinstaller failed" }
python -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "pip install -e . failed" }

# Генерация .ico иконки (опционально, если есть assets/app_icon.png)
$iconPng = Join-Path (Get-Location) "assets\app_icon.png"
$iconIco = Join-Path (Get-Location) "icons\app.ico"

$pyinstallerArgs = @(
    "--onefile", "--console", "--name", "tg-exporter",
    "--exclude-module", "customtkinter",
    "--exclude-module", "app_legacy",
    "--exclude-module", "app",
    "--collect-all", "telethon",
    "--collect-all", "faster_whisper",
    "--collect-all", "ctranslate2",
    "--collect-all", "tokenizers",
    "--collect-all", "imageio_ffmpeg",
    "--collect-all", "tg_exporter",
    "--hidden-import", "tg_exporter.services.transcription.factory",
    "tg_exporter_cli/main.py"
)

if (Test-Path $iconPng) {
    python -m pip install pillow
    if ($LASTEXITCODE -ne 0) { throw "pip install pillow failed" }
    python scripts\make_icons.py --in $iconPng --out $iconIco
    $pyinstallerArgs = @("--icon", "$iconIco") + $pyinstallerArgs
    Write-Host "Icon generated: $iconIco"
}

pyinstaller @pyinstallerArgs

$exePath = "dist\tg-exporter.exe"
if (!(Test-Path $exePath)) {
    throw "PyInstaller did not create $exePath"
}

# Sanity check: консольный бинарник должен быть разумного размера (~25 MB+)
$exeSizeMB = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
Write-Host "EXE size: $exeSizeMB MB"
if ($exeSizeMB -lt 20) {
    Write-Warning "EXE size is suspiciously small ($exeSizeMB MB). Something may be missing."
}

# Упаковка в zip
$archiveName = "tg-exporter-windows-x86_64.zip"
$archivePath = "dist\$archiveName"
if (Test-Path $archivePath) { Remove-Item $archivePath -Force }
Compress-Archive -Path $exePath -DestinationPath $archivePath

Write-Host "Archive ready: $archivePath"
