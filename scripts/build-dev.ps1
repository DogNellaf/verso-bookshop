# Bootstraps and runs the bookshop project (Django REST backend + Vue frontend)
# in development mode on Windows.
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "==> Setting up backend"
if (-not (Test-Path $VenvDir)) {
    python -m venv $VenvDir
}
& $VenvPython -m pip install -q --upgrade pip
& $VenvPython -m pip install -q -r (Join-Path $BackendDir "requirements.txt")
& $VenvPython (Join-Path $BackendDir "manage.py") migrate

Write-Host "==> Installing frontend dependencies"
Push-Location $FrontendDir
try {
    if (Get-Command pnpm -ErrorAction SilentlyContinue) {
        pnpm install
    } else {
        npm install
    }
} finally {
    Pop-Location
}

Write-Host "==> Starting backend (http://127.0.0.1:8000)"
$backendProcess = Start-Process -FilePath $VenvPython `
    -ArgumentList @((Join-Path $BackendDir "manage.py"), "runserver", "0.0.0.0:8000") `
    -NoNewWindow -PassThru

Write-Host "==> Starting frontend (http://127.0.0.1:5173)"
$devCommand = if (Get-Command pnpm -ErrorAction SilentlyContinue) { "pnpm" } else { "npm" }
$frontendProcess = Start-Process -FilePath $devCommand -ArgumentList @("run", "dev") `
    -WorkingDirectory $FrontendDir -NoNewWindow -PassThru

try {
    Wait-Process -Id $backendProcess.Id, $frontendProcess.Id
} finally {
    Write-Host "==> Shutting down"
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
}
