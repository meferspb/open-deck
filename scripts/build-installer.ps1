# Builds the Windows installer for Open Deck for MSFS.
#
#   1. regenerates the integrity manifest
#   2. runs the test suite (unless -SkipTests)
#   3. freezes the gateway into build/pyinstaller/dist/OpenDeck
#   4. copies web/, profiles/, config/, integrity/ next to the exe
#   5. compiles the NSIS installer into dist/
#
# Requirements (build machine only):
#   * Python 3.11+ with PyInstaller (`python -m pip install pyinstaller`)
#   * NSIS 3.x: set NSIS_HOME or pass -NsisPath, or put makensis.exe in PATH
#
# Example:
#   pwsh -File scripts/build-installer.ps1 -Version 0.1.0

[CmdletBinding()]
param(
    [string]$Version = "0.1.0",
    [string]$Python = "python",
    [string]$NsisPath = "",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

$buildRoot = Join-Path $repo "build\pyinstaller"
$distRoot = Join-Path $repo "dist"
$appDist = Join-Path $buildRoot "dist\OpenDeck"

Write-Host "== Open Deck for MSFS :: сборка установщика $Version ==" -ForegroundColor Cyan

# --- 1. Манифест целостности ------------------------------------------
Write-Host "[1/6] Манифест целостности" -ForegroundColor Yellow
& $Python -m msfs_gateway.integrity --write
if ($LASTEXITCODE -ne 0) { throw "integrity --write failed" }

# --- 2. Тесты ----------------------------------------------------------
if (-not $SkipTests) {
    Write-Host "[2/6] Тесты" -ForegroundColor Yellow
    & $Python -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw "тесты упали — сборка остановлена" }
} else {
    Write-Host "[2/6] Тесты пропущены (-SkipTests)" -ForegroundColor DarkYellow
}

# --- 3. PyInstaller ----------------------------------------------------
Write-Host "[3/6] PyInstaller (onedir)" -ForegroundColor Yellow
if (Test-Path $buildRoot) { Remove-Item $buildRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null

& $Python -m PyInstaller `
    --noconfirm --clean --onedir --console `
    --name OpenDeck `
    --icon (Join-Path $repo "packaging\windows\open-deck.ico") `
    --paths $repo `
    --collect-submodules msfs_gateway `
    --distpath (Join-Path $buildRoot "dist") `
    --workpath (Join-Path $buildRoot "work") `
    --specpath $buildRoot `
    (Join-Path $repo "packaging\launcher.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# --- 4. Данные рядом с exe --------------------------------------------
Write-Host "[4/6] Копирование web/profiles/config/integrity" -ForegroundColor Yellow
foreach ($dir in @("web", "profiles", "config", "integrity")) {
    Copy-Item (Join-Path $repo $dir) (Join-Path $appDist $dir) -Recurse -Force
}
Copy-Item (Join-Path $repo "LICENSE") $appDist -Force
Copy-Item (Join-Path $repo "README.md") $appDist -Force

# --- 5. Проверка exe ---------------------------------------------------
Write-Host "[5/6] Проверка собранного exe" -ForegroundColor Yellow
$exe = Join-Path $appDist "OpenDeck.exe"
if (-not (Test-Path $exe)) { throw "exe не найден: $exe" }
& $exe --help | Out-Null
if ($LASTEXITCODE -ne 0) { throw "exe не запускается (--help вернул $LASTEXITCODE)" }

# --- 6. NSIS -----------------------------------------------------------
Write-Host "[6/6] NSIS-установщик" -ForegroundColor Yellow
$makensis = $null
if ($NsisPath) {
    $candidate = Get-ChildItem -Path $NsisPath -Recurse -Filter makensis.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate) { $makensis = $candidate.FullName }
}
if (-not $makensis -and $env:NSIS_HOME) {
    $candidate = Get-ChildItem -Path $env:NSIS_HOME -Recurse -Filter makensis.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate) { $makensis = $candidate.FullName }
}
if (-not $makensis) {
    $candidate = Get-Command makensis.exe -ErrorAction SilentlyContinue
    if ($candidate) { $makensis = $candidate.Source }
}
if (-not $makensis) {
    throw "makensis.exe не найден. Укажите -NsisPath <папка NSIS> или NSIS_HOME."
}

New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
Push-Location (Join-Path $repo "packaging\windows")
try {
    & $makensis "/DPRODUCT_VERSION=$Version" "installer.nsi"
    if ($LASTEXITCODE -ne 0) { throw "NSIS failed" }
} finally {
    Pop-Location
}

$installer = Join-Path $distRoot "OpenDeck-Setup-$Version.exe"
if (-not (Test-Path $installer)) { throw "установщик не создан: $installer" }
$sizeMb = [math]::Round((Get-Item $installer).Length / 1MB, 1)
Write-Host ""
Write-Host "Готово: $installer ($sizeMb МБ)" -ForegroundColor Green
