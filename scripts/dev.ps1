param(
    [switch]$SeedDemo
)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Create the virtual environment first: python -m venv .venv'
}

$env:DATABASE_URL = 'sqlite:///./signalgraph-dev.db'
$env:SECRET_KEY = 'local-development-secret-change-before-production'
$env:AUTO_CREATE_TABLES = 'true'
$env:CELERY_TASK_ALWAYS_EAGER = 'true'
$env:ENVIRONMENT = 'development'

if ($SeedDemo) {
    Push-Location $backendRoot
    try { & $python -m app.cli seed-demo } finally { Pop-Location }
}

Start-Process -FilePath $python -ArgumentList '-m','uvicorn','app.main:app','--reload','--port','8000' -WorkingDirectory $backendRoot -WindowStyle Hidden
Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev' -WorkingDirectory $frontendRoot -WindowStyle Hidden
Write-Host 'SignalGraph development services started:'
Write-Host '  Web: http://localhost:5173'
Write-Host '  API: http://localhost:8000/api/docs'
