# Bootstraps and runs the bookshop project (Django REST backend + Vue frontend)
# in development mode on Windows.
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "==> Setting up backend"
if (-not (Test-Path $VenvPython)) {
    $pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" }
                 elseif (Get-Command py -ErrorAction SilentlyContinue) { "py" }
                 else { throw "Python not found on PATH. Install Python 3.10+ and try again." }
    & $pythonCmd -m venv $VenvDir
    if (-not (Test-Path $VenvPython)) {
        throw "Failed to create the virtual environment at $VenvDir"
    }
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
    -ArgumentList @((Join-Path $BackendDir "manage.py"), "runserver", "127.0.0.1:8000") `
    -NoNewWindow -PassThru

Write-Host "==> Starting frontend (http://127.0.0.1:5173)"
$devCommand = if (Get-Command pnpm -ErrorAction SilentlyContinue) { "pnpm" } else { "npm" }
# pnpm/npm resolve to .cmd shims on Windows; Start-Process can't launch those
# directly ("%1 is not a valid Win32 application"), so route through cmd.exe.
$frontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $devCommand, "run", "dev") `
    -WorkingDirectory $FrontendDir -NoNewWindow -PassThru

try {
    Wait-Process -Id $backendProcess.Id, $frontendProcess.Id
} finally {
    Write-Host "==> Shutting down"
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    # $frontendProcess is cmd.exe; kill its whole tree so the underlying
    # node/vite dev server doesn't keep running after cmd.exe exits.
    taskkill /PID $frontendProcess.Id /T /F 2>$null | Out-Null
}
