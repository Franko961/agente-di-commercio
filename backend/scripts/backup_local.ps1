<#
.SYNOPSIS
  Backup manuale locale del database MongoDB, con mongodump.

.DESCRIZIONE
  Pensato per un cluster Atlas M0 (piano gratuito): M0 non include i backup
  automatici di Atlas (disponibili solo da M10 in su) — questo script è un
  compromesso a costo zero, da lanciare a mano ogni tanto, non un sostituto
  di un vero backup automatico gestito. Se in futuro si passa a M10+, i
  backup nativi di Atlas restano comunque la soluzione da preferire.

  Legge MONGO_URL e DB_NAME da backend\.env (lo stesso file usato
  dall'app) se non passati esplicitamente — un solo posto da tenere
  aggiornato, invece di duplicare la connection string qui.

.PARAMETRO Uri
  Connection string MongoDB. Default: legge MONGO_URL da .env.

.PARAMETRO Database
  Nome del database da esportare. Default: legge DB_NAME da .env.

.PARAMETRO KeepDays
  Backup più vecchi di questo numero di giorni vengono cancellati dopo un
  backup riuscito, per non far crescere la cartella backups/ senza limite.
  Default: 14. Passa 0 per non cancellare mai automaticamente.

.ESEMPIO
  .\backup_local.ps1
  Backup del database configurato in .env, nella cartella backups\ accanto
  a backend\.

.ESEMPIO
  .\backup_local.ps1 -Uri "mongodb+srv://user:pass@cluster.mongodb.net" -Database salesfly_prod
  Backup esplicito, senza leggere .env (utile per un backup una tantum
  contro Atlas invece che contro l'ambiente locale).
#>
param(
  [string]$Uri,
  [string]$Database,
  [int]$KeepDays = 14
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptDir
$EnvFile = Join-Path $BackendDir ".env"
$BackupsRoot = Join-Path (Split-Path -Parent $BackendDir) "backups"

function Read-EnvValue([string]$Key) {
  if (-not (Test-Path $EnvFile)) { return $null }
  $line = Get-Content $EnvFile | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
  if (-not $line) { return $null }
  return ($line -split "=", 2)[1].Trim()
}

if (-not $Uri) { $Uri = Read-EnvValue "MONGO_URL" }
if (-not $Database) { $Database = Read-EnvValue "DB_NAME" }

if (-not $Uri -or -not $Database) {
  Write-Error "MONGO_URL e/o DB_NAME non trovati (né come parametro, né in backend\.env). Passa -Uri e -Database esplicitamente."
  exit 1
}

if (-not (Get-Command mongodump -ErrorAction SilentlyContinue)) {
  Write-Error "mongodump non è installato. Scarica 'MongoDB Database Tools' da https://www.mongodb.com/try/download/database-tools e assicurati che sia nel PATH."
  exit 1
}

$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$OutDir = Join-Path $BackupsRoot $Timestamp

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Output "Backup di '$Database' in corso -> $OutDir"
& mongodump --uri="$Uri" --db="$Database" --out="$OutDir"

if ($LASTEXITCODE -ne 0) {
  Write-Error "mongodump ha restituito un errore (exit code $LASTEXITCODE) — controlla l'output sopra."
  exit $LASTEXITCODE
}

Write-Output "Backup completato: $OutDir"

if ($KeepDays -gt 0 -and (Test-Path $BackupsRoot)) {
  $Cutoff = (Get-Date).AddDays(-$KeepDays)
  $Old = Get-ChildItem $BackupsRoot -Directory | Where-Object { $_.CreationTime -lt $Cutoff }
  foreach ($dir in $Old) {
    Write-Output "Rimuovo backup più vecchio di $KeepDays giorni: $($dir.FullName)"
    Remove-Item -Recurse -Force $dir.FullName
  }
}
