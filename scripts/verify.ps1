$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

Push-Location $projectRoot
try {
    & $python -m pytest backend\tests
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
    & $python -m ruff check backend
    if ($LASTEXITCODE -ne 0) { throw 'Backend lint failed' }
    Push-Location frontend
    try {
        npm test
        if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    } finally { Pop-Location }
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed' }
} finally { Pop-Location }

Write-Host 'SignalGraph verification passed.'
