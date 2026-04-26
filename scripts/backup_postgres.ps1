param(
    [string]$OutputDir = "C:\Users\00506686\RakeshMed\backups"
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$file = Join-Path $OutputDir "postgres-$timestamp.dump"

if (-not $env:POSTGRES_DB) { $env:POSTGRES_DB = "rakeshmed" }
if (-not $env:POSTGRES_USER) { $env:POSTGRES_USER = "rakeshmed" }
if (-not $env:POSTGRES_HOST) { $env:POSTGRES_HOST = "localhost" }
if (-not $env:POSTGRES_PORT) { $env:POSTGRES_PORT = "5433" }

pg_dump `
  --format=custom `
  --file=$file `
  --host=$env:POSTGRES_HOST `
  --port=$env:POSTGRES_PORT `
  --username=$env:POSTGRES_USER `
  $env:POSTGRES_DB

Write-Output $file
