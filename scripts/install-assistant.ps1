#requires -Version 5.1
<#
.SYNOPSIS
  Configure and install n8n Assistant + OpenRouter sandbox in the EXISTING stack.
.DESCRIPTION
  Configure: backs up and surgically edits the already-existing private .env;
             prompts for a NEW OpenRouter key without displaying it;
             generates independent secrets; validates the Compose config.
  Install:   verifies local Docker, database/Redis health, n8n version and
             Compose syntax, then launches only the opt-in sandbox services
             and recreates only the n8n main service (without rebuilding).
  Status:    prints non-secret service state.
  Never changes N8N_VERSION, N8N_ENCRYPTION_KEY, the base Compose file,
  existing volumes, or any database.
.EXAMPLE
  .\scripts\install-assistant.ps1 -Mode Configure
  .\scripts\install-assistant.ps1 -Mode Install
#>
[CmdletBinding()]
param([ValidateSet('Configure', 'Install', 'Status')]
      [string] $Mode = 'Configure')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $Root '.env'
$OverlayPath = Join-Path $Root 'compose.assistant.yml'
$BasePath = Join-Path $Root 'docker-compose.yml'
$Overlay = @('-f', $BasePath, '-f', $OverlayPath)

function Stop-IfFailed([string] $Stage) {
  if ($LASTEXITCODE -ne 0) {
    throw "$Stage failed (exit code $LASTEXITCODE). Existing data was not intentionally removed."
  }
}

function New-RandomSecret {
  $random = New-Object byte[] 32
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($random) }
  finally { $rng.Dispose() }
  return ([BitConverter]::ToString($random)).Replace('-', '').ToLowerInvariant()
}

function Read-PrivateKey {
  $secure = Read-Host 'Enter your NEW rotated OpenRouter API key (input hidden)' -AsSecureString
  $ptr = [IntPtr]::Zero
  try {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    if ($plain -notmatch '^sk-or-' -or $plain.Length -lt 25) {
      throw 'OpenRouter key does not look valid. Revoke the compromised key and enter a newly created key.'
    }
    if ($plain.Contains([Environment]::NewLine) -or $plain.Contains('"')) {
      throw 'Key contains unexpected characters.'
    }
    return $plain
  }
  finally {
    if ($ptr -ne [IntPtr]::Zero) {
      [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
    $secure.Dispose()
  }
}

function Read-EnvLines {
  if (-not (Test-Path -LiteralPath $EnvPath -PathType Leaf)) {
    throw "Missing local .env: $EnvPath. This installer only updates your existing stack and will not generate fresh database credentials."
  }
  $raw = [IO.File]::ReadAllText($EnvPath)
  $result = New-Object 'System.Collections.Generic.List[string]'
  foreach ($line in ($raw -split '\r?\n')) {
    [void] $result.Add($line)
  }
  return $result
}

function Get-EnvValue([System.Collections.Generic.List[string]] $Lines, [string] $Key) {
  $pattern = '^\s*(?:export\s+)?' + [Regex]::Escape($Key) + '\s*=(.*)$'
  $matches = @($Lines | Where-Object { $_ -match $pattern })
  if ($matches.Count -gt 1) { throw "Duplicate .env variable: $Key. Resolve duplicates before continuing." }
  if ($matches.Count -eq 0) { return '' }
  $value = ([regex]::Match($matches[0], $pattern)).Groups[1].Value.Trim()
  if ($value.Length -ge 2 -and
      (($value.StartsWith('"') -and $value.EndsWith('"')) -or
       ($value.StartsWith("'") -and $value.EndsWith("'")))) {
    $value = $value.Substring(1, $value.Length - 2)
  }
  return $value
}

function Set-EnvValue([System.Collections.Generic.List[string]] $Lines,
                      [string] $Key, [string] $Value) {
  if ([string]::IsNullOrWhiteSpace($Value) -or $Value -match '[\r\n]') {
    throw "Missing/invalid value for $Key."
  }
  $pattern = '^\s*(?:export\s+)?' + [Regex]::Escape($Key) + '\s*='
  $indexes = @()
  for ($i = 0; $i -lt $Lines.Count; $i++) {
    if ($Lines[$i] -match $pattern) { $indexes += $i }
  }
  if ($indexes.Count -gt 1) { throw "Duplicate .env variable: $Key" }
  if ($indexes.Count -eq 1) { $Lines[$indexes[0]] = "$Key=$Value" }
  else { [void] $Lines.Add("$Key=$Value") }
}

function Assert-Docker {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'docker was not found. Start Docker Desktop with WSL2 integration.'
  }
  & docker info --format '{{.ServerVersion}}' | Out-Null
  Stop-IfFailed 'Docker engine readiness'
  & docker compose version | Out-Null
  Stop-IfFailed 'Docker Compose readiness'
}

function Assert-ExistingStack([System.Collections.Generic.List[string]] $Lines) {
  foreach ($key in @('N8N_ENCRYPTION_KEY','N8N_RUNNERS_AUTH_TOKEN',
                     'DB_POSTGRESDB_PASSWORD','DB_POSTGRESDB_DATABASE',
                     'DB_POSTGRESDB_USER','N8N_VERSION')) {
    if ([string]::IsNullOrWhiteSpace((Get-EnvValue $Lines $key))) {
      throw "Existing required setting $key is missing. Do not guess or re-generate it."
    }
  }
}

function Assert-ServiceHealthy([string] $Service) {
  $idOutput = @(& docker compose -f $BasePath ps -q $Service)
  Stop-IfFailed "Find $Service container"
  $id = ($idOutput -join '').Trim()
  if (-not $id) { throw "$Service is not running. Repair the existing service first." }
  $status = @(& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' $id)
  Stop-IfFailed "Inspect $Service"
  if (($status -join '').Trim() -ne 'healthy') {
    throw "$Service is not healthy (status: $($status -join '')). Do not install yet."
  }
}

function Assert-N8nVersion([System.Collections.Generic.List[string]] $Lines) {
  $declared = (Get-EnvValue $Lines 'N8N_VERSION')
  if ($declared -notmatch '^\d+\.\d+\.\d+$') {
    throw 'N8N_VERSION in .env must be a pinned x.y.z release; do not silently upgrade.'
  }
  $runningOutput = @(& docker compose -f $BasePath exec -T n8n n8n --version)
  Stop-IfFailed 'Read running n8n version'
  $running = (($runningOutput -join ' ') | Select-String -Pattern '\d+\.\d+\.\d+' -AllMatches).Matches[0].Value
  if ([version] $running -lt [version] '2.39.0') {
    throw "Running n8n $running is too old for the documented Assistant setup. Follow docs/n8n-v3-beta-in-place.md first."
  }
  if ($declared -ne $running) {
    throw "Running n8n $running differs from .env N8N_VERSION=$declared. Refusing to recreate and potentially migrate your database."
  }
  Write-Host "n8n version matches existing pin: $running" -ForegroundColor Green
}

if (-not (Test-Path -LiteralPath $OverlayPath -PathType Leaf)) {
  throw "Missing opt-in overlay: $OverlayPath. Switch to the Assistant PR branch first."
}
if (-not (Test-Path -LiteralPath $BasePath -PathType Leaf)) {
  throw "Missing existing Compose file: $BasePath."
}
Push-Location $Root
try {
  if ($Mode -eq 'Status') {
    Assert-Docker
    & docker compose -f $BasePath ps -a
    & docker compose @Overlay ps -a sandbox-api sandbox-runner-1 searxng
    exit 0
  }

  $lines = Read-EnvLines
  Assert-ExistingStack $lines
  Assert-Docker

  if ($Mode -eq 'Configure') {
    & git check-ignore -q -- .env
    if ($LASTEXITCODE -ne 0) {
      throw 'The .env file is not ignored by Git. Refusing to store secrets until .gitignore is correct.'
    }

    $newKey = Read-PrivateKey
    $sandboxApiKey = Get-EnvValue $lines 'SANDBOX_API_KEYS'
    if ($sandboxApiKey -notmatch '^[a-f0-9]{64}$') { $sandboxApiKey = New-RandomSecret }

    $secrets = @(
      'SANDBOX_API_RUNNER_REGISTRATION_TOKEN',
      'SANDBOX_API_RUNNER_API_KEY',
      'SEARXNG_SECRET'
    )
    $newValues = @{}
    foreach ($secret in $secrets) {
      $existing = Get-EnvValue $lines $secret
      if ($existing -match '^[a-f0-9]{64}$') {
        $newValues[$secret] = $existing
      }
      else { $newValues[$secret] = New-RandomSecret }
    }

    $modules = Get-EnvValue $lines 'N8N_ENABLED_MODULES'
    $moduleList = @($modules.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($moduleList -notcontains 'instance-ai') { $moduleList += 'instance-ai' }

    Set-EnvValue $lines 'N8N_SANDBOX_VERSION' '1.13.0'
    Set-EnvValue $lines 'N8N_INSTANCE_AI_MODEL' 'openrouter/openrouter/free'
    Set-EnvValue $lines 'N8N_INSTANCE_AI_MODEL_API_KEY' $newKey
    Set-EnvValue $lines 'N8N_ENABLED_MODULES' ($moduleList -join ',')
    Set-EnvValue $lines 'SANDBOX_API_KEYS' $sandboxApiKey
    Set-EnvValue $lines 'N8N_SANDBOX_SERVICE_API_KEY' $sandboxApiKey
    foreach ($secret in $secrets) {
      Set-EnvValue $lines $secret $newValues[$secret]
    }
    Set-EnvValue $lines 'N8N_INSTANCE_AI_SEARXNG_URL' 'http://searxng:8080'

    # Put the backup OUTSIDE the public repository; it contains PRIVATE secrets.
    $parent = Split-Path -Parent $Root
    $backupDir = Join-Path $parent 'n8n-env-private-backups'
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    $backup = Join-Path $backupDir ('.env.' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak')
    Copy-Item -LiteralPath $EnvPath -Destination $backup -ErrorAction Stop
    $newText = [string]::Join([Environment]::NewLine, $lines)
    try {
      [IO.File]::WriteAllText($EnvPath, $newText, (New-Object System.Text.UTF8Encoding $false))
      & docker compose @Overlay config --quiet
      Stop-IfFailed 'Combined Docker Compose syntax validation'
    }
    catch {
      Copy-Item -LiteralPath $backup -Destination $EnvPath -Force
      throw "Validation failed and original .env was restored. Cause: $($_.Exception.Message)"
    }
    finally {
      $newKey = $null
      $newText = $null
    }

    Write-Host 'Private .env updated and combined Compose validated.' -ForegroundColor Green
    Write-Host "Backup saved OUTSIDE the repo: $backup (contains secrets; protect it)"
    Write-Host 'N8N_SANDBOX_VERSION=1.13.0; N8N_INSTANCE_AI_MODEL=openrouter/openrouter/free'
    Write-Host 'The existing n8n version, encryption key, Redis and database settings were preserved.'
    Write-Host 'Next: run the same script with -Mode Install, after existing n8n migration and Redis recovery are complete.'
    exit 0
  }

  # -Mode Install is intentionally a separate operation after -Mode Configure.
  if ((Get-EnvValue $lines 'N8N_SANDBOX_VERSION') -ne '1.13.0') {
    throw 'Run -Mode Configure first to pin the sandbox version to 1.13.0.'
  }
  foreach ($key in @('N8N_INSTANCE_AI_MODEL_API_KEY','SANDBOX_API_KEYS',
      'SANDBOX_API_RUNNER_REGISTRATION_TOKEN','SANDBOX_API_RUNNER_API_KEY',
      'N8N_SANDBOX_SERVICE_API_KEY','SEARXNG_SECRET')) {
    $value = Get-EnvValue $lines $key
    if ([string]::IsNullOrWhiteSpace($value) -or $value -match '^(REPLACE_|CHANGE_ME|YOUR_)') {
      throw "Missing sandbox secret: $key. Run -Mode Configure first."
    }
  }
  if ((Get-EnvValue $lines 'SANDBOX_API_KEYS') -ne (Get-EnvValue $lines 'N8N_SANDBOX_SERVICE_API_KEY')) {
    throw 'Sandbox API key mismatch. Run -Mode Configure first.'
  }
  Assert-ServiceHealthy 'postgres'
  Assert-ServiceHealthy 'redis'
  Assert-N8nVersion $lines
  & docker compose @Overlay config --quiet
  Stop-IfFailed 'Compose validation'

  Write-Host 'Pulling sandbox v1.13.0 and SearXNG images (may require substantial download)...'
  & docker compose @Overlay pull sandbox-certs sandbox-api sandbox-runner-1 searxng
  Stop-IfFailed 'Sandbox image pull'

  Write-Host 'Starting only the new local sandbox services...'
  & docker compose @Overlay up -d sandbox-certs sandbox-api sandbox-runner-1 searxng
  Stop-IfFailed 'Sandbox startup'

  $apiID = ((@(& docker compose @Overlay ps -q sandbox-api)) -join '').Trim()
  if (-not $apiID) { throw 'No sandbox-api container. Check docker compose logs sandbox-api.' }
  $health = ((@(& docker inspect --format '{{.State.Health.Status}}' $apiID)) -join '').Trim()
  if ($health -ne 'healthy') {
    Write-Warning "Sandbox API not healthy yet (status $health). Recheck status and logs, then rerun -Mode Install."
    & docker compose @Overlay ps -a sandbox-certs sandbox-api sandbox-runner-1 searxng
    exit 1
  }

  Write-Host 'Enabling Assistant in the existing n8n main server without rebuilding or touching dependencies...'
  & docker compose @Overlay up -d --no-build --no-deps n8n
  Stop-IfFailed 'n8n main server recreation'
  & docker compose @Overlay ps n8n sandbox-api sandbox-runner-1 searxng
  & docker compose @Overlay logs --tail 25 sandbox-api sandbox-runner-1
  Write-Host 'Verify in the n8n Editor -> Settings -> Assistant and test a disposable workflow.' -ForegroundColor Green
  Write-Host 'No existing Compose volumes were deleted.'
}
finally {
  Pop-Location
}
