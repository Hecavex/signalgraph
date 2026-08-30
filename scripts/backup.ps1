param(
    [Parameter(Mandatory = $true)]
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$destination = [System.IO.Path]::GetFullPath($Output)
if (-not $destination.StartsWith([System.IO.Path]::GetPathRoot($destination), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Backup path could not be resolved.'
}
$parent = Split-Path -Parent $destination
if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }

Push-Location $projectRoot
try {
    $containerPath = '/tmp/signalgraph-backup.dump'
    docker compose exec -T postgres pg_dump -U signalgraph -d signalgraph -Fc --file $containerPath
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed' }
    docker compose cp "postgres:$containerPath" $destination
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy backup from the PostgreSQL container' }
    docker compose exec -T postgres rm -f -- $containerPath
} finally { Pop-Location }
Write-Host "Backup created: $destination"
