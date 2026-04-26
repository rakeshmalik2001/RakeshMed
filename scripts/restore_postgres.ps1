param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

if (-not $env:POSTGRES_DB) { $env:POSTGRES_DB = "rakeshmed" }
if (-not $env:POSTGRES_USER) { $env:POSTGRES_USER = "rakeshmed" }
if (-not $env:POSTGRES_HOST) { $env:POSTGRES_HOST = "localhost" }
if (-not $env:POSTGRES_PORT) { $env:POSTGRES_PORT = "5433" }

pg_restore `
  --clean `
  --if-exists `
  --no-owner `
  --host=$env:POSTGRES_HOST `
  --port=$env:POSTGRES_PORT `
  --username=$env:POSTGRES_USER `
  --dbname=$env:POSTGRES_DB `
  $BackupFile
