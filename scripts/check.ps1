# Проверки проекта перед коммитом/PR.
# Запуск: pwsh -File scripts/check.ps1

[CmdletBinding()]
param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    if (-not $Quiet) { Write-Host "== $Name" -ForegroundColor Cyan }
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Шаг «$Name» завершился с кодом $LASTEXITCODE" }
}

Invoke-Step "ruff check" {
    python -m ruff check msfs_gateway tests scripts
}

Invoke-Step "ruff format --check" {
    python -m ruff format --check msfs_gateway tests scripts
}

Invoke-Step "compileall" {
    python -m compileall -q msfs_gateway tests
}

Invoke-Step "python unittest" {
    python -m unittest discover -s tests
}

if (Get-Command node -ErrorAction SilentlyContinue) {
    Invoke-Step "node --test" {
        node --test "tests/web/*.test.mjs"
    }
} elseif (-not $Quiet) {
    Write-Host "== node --test: пропущено (Node.js не найден)" -ForegroundColor DarkYellow
}

if (-not $Quiet) { Write-Host "Все проверки пройдены." -ForegroundColor Green }
