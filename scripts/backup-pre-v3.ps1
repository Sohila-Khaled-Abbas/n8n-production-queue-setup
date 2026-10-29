#Requires -Version 5.1
<#
Back up the existing n8n Docker Compose project before a v3 migration.
The script does NOT delete or replace volumes. Its backups contain secrets.
Existing n8n services are stopped only after a successful logical DB export.
#>
[CmdletBinding()]
param([string]$ProjectRoot=(Get-Location).Path)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $ProjectRoot
if (!(Test-Path -LiteralPath '.\docker-compose.yml') -or !(Test-Path -LiteralPath '.\.env')) {
    throw 'Run this from the n8n repository root; docker-compose.yml and .env are required.'
}
function Invoke-Docker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker operation failed: $($Arguments[0]) (exit code $LASTEXITCODE)." }
}
function Get-Volume([string]$Container,[string]$Destination) {
    $raw = & docker inspect $Container --format '{{json .Mounts}}'
    if ($LASTEXITCODE -ne 0) { throw "Cannot inspect $Container." }
    $matches = @($raw | ConvertFrom-Json | Where-Object { $_.Type -eq 'volume' -and $_.Destination -eq $Destination })
    if ($matches.Count -ne 1) { throw "Expected exactly one named volume for $Container at $Destination." }
    return ([string]$matches[0].Name).Trim()
}
function Save-Volume([string]$Volume,[string]$Name) {
    if ([string]::IsNullOrWhiteSpace($Volume)) { throw 'Empty volume name.' }
    Invoke-Docker @('run','--rm','--mount',"type=volume,source=$Volume,target=/data,readonly",
        '--mount',"type=bind,source=$BackupDir,target=/backup",
        '--entrypoint','sh','redis:7-alpine','-c',"cd /data && tar -czf /backup/$Name .")
    Invoke-Docker @('run','--rm','--mount',"type=bind,source=$BackupDir,target=/backup,readonly",
        '--entrypoint','sh','redis:7-alpine','-c',"tar -tzf /backup/$Name >/dev/null")
    $out = Join-Path $BackupDir $Name
    if (!(Test-Path -LiteralPath $out) -or (Get-Item -LiteralPath $out).Length -le 0) {
        throw "Failed to verify volume archive $Name."
    }
}
$redisHealth = & docker inspect n8n-redis --format '{{.State.Health.Status}}'
if ($LASTEXITCODE -ne 0 -or "$redisHealth".Trim() -ne 'healthy') {
    throw 'Redis is not healthy. Finish original-volume AOF recovery first.'
}
$pgHealth = & docker inspect n8n-postgres --format '{{.State.Health.Status}}'
if ($LASTEXITCODE -ne 0 -or "$pgHealth".Trim() -ne 'healthy') {
    throw 'Postgres is not healthy.'
}
$version = & docker exec n8n-main-server n8n --version
if ($LASTEXITCODE -ne 0) { throw 'Existing n8n server is not running.' }
$version = ([string]$version).Trim()
Write-Host "Running n8n version: $version"
if ($version -notmatch '^2\.\d+\.\d+') {
    throw 'For n8n v3 already in use, do not run the v2-to-v3 script. For older versions, upgrade to v2 first.'
}
$pgVolume = Get-Volume 'n8n-postgres' '/var/lib/postgresql/data'
$redisVolume = Get-Volume 'n8n-redis' '/data'
$BackupDir = Join-Path (Split-Path -Parent (Resolve-Path .).Path) ("n8n-pre-v3-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $BackupDir | Out-Null
Copy-Item -LiteralPath .\.env -Destination (Join-Path $BackupDir '.env.pre-v3')
$info = [ordered]@{
    version=$version; exported_at=(Get-Date).ToString('o');
    postgres_volume=$pgVolume; redis_volume=$redisVolume;
    n8n_image_id=((& docker inspect n8n-main-server --format '{{.Image}}') | Out-String).Trim();
    runner_image_id=((& docker inspect n8n-runner --format '{{.Image}}') | Out-String).Trim()
}
$info | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $BackupDir 'metadata.json')
# Export a binary Postgres dump *inside* the Linux container, then copy it out.
# This avoids Windows PowerShell corrupting binary output via redirection.
Invoke-Docker @('exec','n8n-postgres','sh','-c',
    'pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/n8n-pre-v3.pgdump')
Invoke-Docker @('cp','n8n-postgres:/tmp/n8n-pre-v3.pgdump',(Join-Path $BackupDir 'n8n-pre-v3.pgdump'))
Invoke-Docker @('exec','n8n-postgres','rm','-f','/tmp/n8n-pre-v3.pgdump')
$dump = Join-Path $BackupDir 'n8n-pre-v3.pgdump'
if (!(Test-Path -LiteralPath $dump) -or (Get-Item -LiteralPath $dump).Length -le 0) {
    throw 'Database dump missing or empty. Stack left running.'
}
Write-Host 'PostgreSQL logical dump captured. Stopping stack for consistent volume snapshot.'
Invoke-Docker @('compose','stop','n8n-autoscaler','redis-monitor','n8n-webhook',
    'n8n-worker','n8n-worker-runner','n8n','n8n-runner','redis','postgres')
Invoke-Docker @('cp','n8n-main-server:/home/node/.n8n',(Join-Path $BackupDir 'n8n-home'))
if (!(Test-Path -LiteralPath (Join-Path $BackupDir 'n8n-home'))) {
    throw 'n8n user-data copy missing. Do not upgrade.'
}
Save-Volume $pgVolume 'postgres-volume.tar.gz'
Save-Volume $redisVolume 'redis-volume.tar.gz'
Write-Host "BACKUP VERIFIED: $BackupDir" -ForegroundColor Green
Write-Host 'Stack deliberately left stopped. Protect this directory and make an off-PC copy.'
