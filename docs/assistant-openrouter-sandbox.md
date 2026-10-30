# n8n Assistant + OpenRouter + sandbox v1.13.0 — automated PowerShell setup

**For the existing Windows 11 + Docker Desktop queue-mode deployment.** This is an additive installation for **local development only**. It preserves PostgreSQL, Redis, ngrok port 80, workers, existing task runners, and all existing volumes.

## Confirmed release

The published **service/v1.13.0** release (October 30, 2026) uses these three stable Docker Hub images (all exactly `1.13.0`):

- `docker.io/n8nio/n8n-sandbox-service-api:1.13.0`
- `docker.io/n8nio/n8n-sandbox-service-runner-dind:1.13.0`
- `docker.io/n8nio/n8n-sandbox-service-sandbox:1.13.0`

**Release:** https://github.com/n8n-io/n8n-sandbox-service/releases/tag/service/v1.13.0 . The optional Firecracker runner is not used on Docker Desktop.

## Prerequisites: do these before installing

1. **Revoke the OpenRouter API key previously pasted in chat** and create a new key: https://openrouter.ai/settings/keys . The script prompts for the new key *without echoing it*; no hand-editing of files is needed. Never publish the key.
2. If Redis still has a corrupt AOF, finish [Redis recovery](redis-windows-recovery.md). Do not erase the Redis volume, pending queue jobs, or PostgreSQL data.
3. If the installation is still running n8n 2.25.7, finish the [two-stage in-place version migration](n8n-v3-beta-in-place.md). The installer **refuses to recreate n8n below 2.39.0**, or if the running n8n version differs from `N8N_VERSION` in your private `.env`.
4. Keep a complete verified database and n8n-data backup before any version migration. The installer backs up **only the local .env** automatically and does **not** replace full database backups.
5. Docker Desktop must be running. Use the existing repository checkout containing your existing ignored `.env`; do not create a second instance or overwrite it with `.env.example`.

## PowerShell: fetch the opt-in feature branch (existing checkout)

Open PowerShell **inside your existing repository directory**. You can do this without editing any files: in Windows File Explorer open the repository folder, click its address bar, type `powershell` and press Enter.

```powershell
# Read-only discovery: the path must end in n8n-production-queue-setup
(Get-Location).Path
git status --short --branch
docker compose ps -a

# Do not switch branches when there are tracked local changes.
if (@(git status --porcelain --untracked-files=no).Count -gt 0) {
    throw 'Tracked local changes found. Stop and preserve them before switching branches.'
}
$branch = 'feat/opt-in-n8n-assistant-openrouter-sandbox'
git fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
git show-ref --verify --quiet "refs/heads/$branch"
if ($LASTEXITCODE -eq 0) {
    git switch $branch
} else {
    git switch --track "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw 'Cannot switch to the feature branch' }
```

## Phase A: automatically update local .env (no manual editing)

```powershell
.\scripts\install-assistant.ps1 -Mode Configure
```

Enter the **new** OpenRouter key when prompted, without pasting it into chat. This command:

- Preserves `N8N_VERSION`, `N8N_ENCRYPTION_KEY`, existing database passwords and worker tokens.
- Backs up the existing private `.env` **outside** the Git checkout in sibling folder `n8n-env-private-backups` (this backup also contains secrets; keep it private).
- Adds/replaces `N8N_SANDBOX_VERSION=1.13.0`, `N8N_INSTANCE_AI_MODEL=openrouter/openrouter/free`, `N8N_INSTANCE_AI_MODEL_API_KEY`.
- Appends `instance-ai` to any existing `N8N_ENABLED_MODULES` instead of discarding other module names.
- Creates unique 32-byte random secrets for `SANDBOX_API_KEYS`, `SANDBOX_API_RUNNER_REGISTRATION_TOKEN`, `SANDBOX_API_RUNNER_API_KEY`, and `SEARXNG_SECRET`, preserving valid existing values on subsequent runs.
- Makes `N8N_SANDBOX_SERVICE_API_KEY` match `SANDBOX_API_KEYS`.
- Validates the merged Compose configuration with `docker compose config --quiet`; rolls back `.env` on failure.

**No Compose containers are launched by Configure.** Only `.env` changes on your PC; no secret is pushed to GitHub.

## Phase B: verify and install the sandbox

Run only after the existing n8n migration is complete and **Redis/PostgreSQL are healthy**:

```powershell
.\scripts\install-assistant.ps1 -Mode Install
```

This checks that both database services are healthy, that the running n8n version is at least 2.39 and exactly equals the existing pinned `N8N_VERSION`, and that all secrets match. It then:

1. Pulls sandbox API and DIND runner images `1.13.0`, plus SearXNG (these downloads require free disk space).
2. Starts only `sandbox-certs`, `sandbox-api`, `sandbox-runner-1` and `searxng`.
3. Checks sandbox API health.
4. Recreates **only** the existing main `n8n` container, with `--no-build --no-deps`, to activate the Assistant. The task runner / worker services are not rebuilt.

If any prerequisite is not met, the script stops **without updating your existing n8n version or dropping any volumes**.

## Phase C: verify

```powershell
.\scripts\install-assistant.ps1 -Mode Status
$files = @('-f','docker-compose.yml','-f','compose.assistant.yml')
docker compose @files logs --tail 60 sandbox-certs sandbox-api sandbox-runner-1
docker compose @files exec -T n8n wget -qO- http://sandbox-api:8080/healthz
```

The health endpoint should return `{"status":"ok"}`. The one-shot `sandbox-certs` service exiting **0** is normal. Inspect the logs for successful runner registration.

Open your existing local editor on **http://localhost** (the original port 80, not a new 5678 port), then check **Settings → Assistant** and try a disposable, non-sensitive task. OpenRouter `openrouter/free` automatically selects a free model, but limits and tool-calling compatibility vary by model.

## Recovery: Docker refuses to recreate a running n8n main container

Symptom after a successful sandbox pull/start:

```
cannot remove container "...": container is running: stop the container before removing or force remove
```

The sandbox API may already be healthy; the only failed step is applying
the new Assistant environment variables to the existing n8n main process.
Do **not** rerun Configure, reset Docker Desktop, remove volumes, or use
`docker rm -f`. Restarting the container alone cannot apply new
Compose environment variables.

In Windows PowerShell from the original checkout:

```powershell
$files = @('-f','docker-compose.yml','-f','compose.assistant.yml')
docker compose @files ps -a
docker inspect n8n-main-server --format 'Name={{.Name}} Status={{.State.Status}} Restart={{.HostConfig.RestartPolicy.Name}}'
docker compose @files config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Stop: invalid Compose config' }
```

Check that n8n main is the failing container and that your existing
PostgreSQL/Redis are healthy, as verified earlier. If it is running, schedule
a brief editor interruption and perform a **single-service graceful stop**:

```powershell
docker compose @files stop --timeout 300 n8n
if ($LASTEXITCODE -ne 0) { throw 'Stop failed: inspect Docker status before continuing' }

$state = (docker inspect n8n-main-server --format '{{.State.Status}}').Trim()
if ($LASTEXITCODE -ne 0 -or $state -ne 'exited') {
    throw "Not safely stopped ($state). No removal attempted."
}

docker compose @files up -d --no-build --no-deps n8n
if ($LASTEXITCODE -ne 0) { throw 'Recreate failed; inspect docker compose ps -a; do not force-remove.' }

docker compose @files ps -a n8n sandbox-api sandbox-runner-1 searxng
```

This stops **only** the n8n editor/main service, preserving the PostgreSQL,
Redis, queues, workers and named volumes. The 300-second timeout gives n8n
time to shut down gracefully. If it cannot stop, stop here and diagnose the
Docker daemon and possible external restarts before attempting removal.

From the latest version of the installer, `-Mode Install` now performs
the graceful stop automatically after the sandbox API is healthy. Image
downloads are cached and do not have to be manually repeated.

## Weather Log / sandbox dependency-install cancellation

If Assistant reports:

```text
SandboxWorkspaceSetupError: Sandbox workspace setup failed during install-dependencies: canceled
```

this happens while the Assistant prepares its isolated development workspace, **before** the Weather Log nodes run. The message by itself does not prove that Redis, PostgreSQL, the weather endpoint, or the workflow are defective. The sandbox API can be healthy even while the Docker-in-Docker runner is not yet ready or its nested sandbox image is still downloading.

From the **existing repository checkout**, run these read-only checks. Redact API keys, credentials, and private workflow data before sharing any logs:

```powershell
$files = @('-f', 'docker-compose.yml', '-f', 'compose.assistant.yml')
docker compose @files ps -a n8n postgres redis sandbox-certs sandbox-api sandbox-runner-1
docker compose @files logs --since 30m --tail 150 sandbox-api sandbox-runner-1 n8n
docker compose @files exec -T n8n wget -qO- http://sandbox-api:8080/healthz
docker compose @files exec -T sandbox-runner-1 docker info --format '{{.ServerVersion}}'
docker system df
Get-PSDrive C,D | Select-Object Name,@{Name='FreeGB';Expression={[math]::Round($_.Free / 1GB, 1)}}
```

- API healthy and runner starting/unhealthy: inspect runner registration, mTLS, Docker-in-Docker and nested image-pull logs. The installer now waits for runner `/readyz` health before recreating n8n main.
- `no space left on device` or `ENOSPC`: free space safely after reviewing `docker system df`; never use `docker compose down -v`, indiscriminate `docker system prune --volumes`, or remove PostgreSQL/Redis/n8n volumes.
- `ECONNRESET`, DNS errors, npm registry timeout, or image-pull errors: check outbound connectivity from Docker Desktop and the runner. The sandbox must download dependencies and sometimes its nested image on first use.
- Request/session cancelled while the runner stays healthy: retry once with a new Assistant chat. Preserve and inspect logs if it repeats.
- `sandbox-runner-1` not registered: verify the registration token, runner key, and certificate setup **without printing secret values**.

Don't confuse the Assistant's development sandbox with the existing n8n Code-node task-runner sidecar: restarting `n8n-worker-runner` won't repair a failed `sandbox-runner-1` workspace.

**Weather Log fallback:** n8n's [official first-workflow guide](https://docs.n8n.io/build-your-first-workflow/) uses the Mockingbird fields `city`, `temp_c`, and `condition`. The report expression is `The temperature in {{ $json.city }} is {{ $json.temp_c }}°C. It's currently {{ $json.condition }}.` (don't use `$json.temperature` or `$json.conditions`). You can create a Data Table from the project UI or the row-insertion node while the Assistant is unavailable.

See also the [self-hosted Assistant setup](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-n8n-assistant/) and upstream [sandbox Compose guide](https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose/).

## Troubleshooting and safety

- **Redis unhealthy**: read the existing Redis recovery runbook, don't run `docker compose down -v`.
- **n8n version mismatch**: finish the migration guide first. Do not change `N8N_VERSION` automatically.
- **Sandbox API unhealthy**: inspect `docker compose @files logs sandbox-certs sandbox-api`; don't publish secret-bearing config.
- **Runner crash loops**: verify registration/API key variables and mTLS certificate mounts. Don't publish sandbox API ports.
- **Insufficient disk space**: the DIND runner downloads a nested sandbox image too.
- **Stop optional components**: `docker compose @files stop sandbox-runner-1 sandbox-api searxng`; disable the Assistant with a deliberate main-container recreation using only the base Compose configuration after checking versions.

**Security:** This bundled sandbox uses `privileged: true` Docker-in-Docker. It is for trusted local testing, **not a hardened production deployment**. n8n recommends [Daytona](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-n8n-assistant/) for production. The current upstream `bootstrap-mtls.sh --world-readable` example exposes wider certificate readability than a hardened system should; review certificate file ownership/permissions before production use.

## References

- https://github.com/n8n-io/n8n-sandbox-service/releases/tag/service/v1.13.0
- https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-n8n-assistant/
- https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose/
- https://github.com/n8n-io/n8n/blob/master/docker/get-n8n-compose.yml
