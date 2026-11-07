# Публикация репозитория по SSH.
#
#   pwsh -File scripts/publish-ssh.ps1 -Remote git@github.com:meferspb/open-deck.git
#
# Скрипт проверяет чистоту дерева и доступ по ключу, затем делает push в main.
# Ключ по умолчанию — ~/.ssh/id_ed25519_github (ssh-keygen -t ed25519).

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Remote,

    [string]$Key = (Join-Path $HOME ".ssh" "id_ed25519_github"),

    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

if (-not (Test-Path $Key)) {
    throw "Не найден SSH-ключ: $Key. Создайте: ssh-keygen -t ed25519 -C open-deck -f `"$Key`""
}

$status = git status --porcelain
if ($status) {
    throw "Рабочее дерево не чистое — сначала закоммитьте изменения:`n$status"
}

if (-not (git rev-parse --verify $Branch 2>$null)) {
    throw "Ветка '$Branch' не найдена"
}

$sshCommand = "ssh -i `"$Key`" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
$env:GIT_SSH_COMMAND = $sshCommand

Write-Host "== Проверка доступа к GitHub по ключу $Key" -ForegroundColor Cyan
$test = (& ssh -i $Key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1) -join "`n"
if ($test -match "successfully authenticated") {
    Write-Host $test
} else {
    throw "GitHub не принял ключ. Добавьте публичный ключ в GitHub → Settings → SSH and GPG keys.`n$test"
}

$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin $Remote
} elseif ($existing -ne $Remote) {
    git remote set-url origin $Remote
}
Write-Host "== origin: $Remote"

Write-Host "== Push $Branch" -ForegroundColor Cyan
git push -u origin $Branch
if ($LASTEXITCODE -ne 0) {
    throw "git push завершился с кодом $LASTEXITCODE"
}

Write-Host "Готово: $Remote ($Branch)" -ForegroundColor Green
