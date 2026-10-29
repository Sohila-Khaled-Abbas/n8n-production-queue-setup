# Upgrade your EXISTING Docker + ngrok n8n stack to pinned v3 beta

**Scope:** Same local checkout, same `docker-compose.yml`, same project
`n8n`, same port **80**, same PostgreSQL/Redis volumes, same n8n workflow
and credential store, and same ngrok forwarding command. **No new
environment is created.** The upgrade can modify the existing database.
Do not treat it as reversible by changing an image tag.

Updated October 29, 2026. Official n8n 3.0.0 beta announcement:
https://blog.n8n.io/introducing-n8n-v3/
The 3.0.1 pre-release is available as an explicit Docker image; Docker
`:latest` still follows **stable 2.x**, not 3.x. Your Docker Desktop
Images screen showing "updated" does not prove the running service uses
v3: this repository runs **custom-built** n8n and runner images.
The repo now pins matching `N8N_VERSION=3.0.1` through both Dockerfiles.

## Mandatory intermediate update for existing n8n 2.25.7

The running version of this installation was confirmed to be **2.25.7**.
The **Settings → Migration Report** UI does not exist in that version;
n8n's official minimum is **2.39**. Do not skip directly to
`N8N_VERSION=3.0.1` before viewing the report on a recent 2.x build.
As of October 29, 2026, **2.45.6** is the published stable 2.x version.

**Use the same Docker Compose project, ports, credentials, PostgreSQL and
Redis volumes. No staging deployment or second instance is required.**
Do NOT run `docker compose down -v` or replace `.env` with
`.env.example`. This is a two-stage *in-place* migration:

1. Restore the original Redis queue service to healthy and confirm
   PostgreSQL is healthy. Verify the running version is 2.25.7.
2. Make a complete pre-upgrade backup of the current data and secrets
   **before** upgrading even within 2.x. The script under
   `scripts/backup-pre-v3.ps1` works on 2.x while both database services
   and the n8n main container are healthy and intentionally stops the
   stack after export. Check backup files and keep a separate copy.
3. Check that both versioned images exist (this tests the registries without
   modifying running services):
   ```powershell
   docker manifest inspect docker.n8n.io/n8nio/n8n:2.45.6 > $null
   if ($LASTEXITCODE -ne 0) { throw "n8n 2.45.6 image unavailable" }
   docker manifest inspect n8nio/runners:2.45.6 > $null
   if ($LASTEXITCODE -ne 0) { throw "Matching runner image unavailable" }
   ```
4. In the **existing** `.env`, set `N8N_VERSION=2.45.6` (do **not**
   use the branch's v3 default for this intermediate stage). Keep all
   prior PostgreSQL credentials, encryption key, task runner token,
   `N8N_DATA_DIR`, binary-data mode and ngrok URLs as they were.
   Use the branch's `build.args.N8N_VERSION` to keep both image bases
   aligned, but only build if the CI build is passing. Build does not
   change database data; running the upgraded image does.
5. First validate Compose and rebuild **without deploying**:
   ```powershell
   docker compose config --quiet
   docker compose build n8n n8n-runner n8n-worker n8n-worker-runner
   if ($LASTEXITCODE -ne 0) { throw "Stop: custom image build failed" }
   ```
   If the n8n 2.45.6 custom runner build fails, **do not launch** a
   partially updated stack: preserve backups and inspect the CI/build
   logs first.
6. Bring up the existing DB/Redis services, then the n8n server:
   ```powershell
   docker compose up -d postgres redis
   docker compose ps postgres redis
   docker compose up -d --no-build n8n
   docker exec n8n-main-server n8n --version
   ```
   The runtime must report `2.45.6`, and Redis/Postgres must be healthy.
   Start the aligned runner/worker services only after that succeeds.
7. In the existing editor, open **Settings → Migration Report**. Review
   **Workflow issues** and **Instance issues**, apply/verify any proposed
   fixes, and publish only the workflow versions you intend.
8. Take **another full backup** once the migration report is resolved.
   Only then change `N8N_VERSION=3.0.1` and follow the v3 steps below.

Caution: the custom runner image and community nodes need a working
CI build and on-host checks on *each* version. Passing `docker compose
config` by itself is insufficient. Do not assume updating Docker
Desktop's downloaded `:latest` image changes this Compose project's
custom-built containers.

## v3 additional breaking changes: Compression, community packages, Chat Hub, importing

These apply to the **same** Docker/ngrok instance on the in-place
upgrade branch. They are migration checks, not reasons to create a
second Compose project.

### 1. Compression node limits (smaller by default)

v3 changes the maximum decompressed size from **2 GiB** to **256 MiB**
and the maximum number of ZIP entries from **5,000** to **1,000**.

The shared n8n environment in `docker-compose.yml` explicitly sets
the safer defaults:

```dotenv
N8N_COMPRESSION_NODE_MAX_DECOMPRESSED_SIZE_BYTES=268435456
N8N_COMPRESSION_NODE_MAX_ZIP_ENTRIES=1000
```

If an existing workflow really requires the old limits and the source
archives are trusted, set these in the **existing** `.env` instead:

```dotenv
N8N_COMPRESSION_NODE_MAX_DECOMPRESSED_SIZE_BYTES=2147483648
N8N_COMPRESSION_NODE_MAX_ZIP_ENTRIES=5000
```

A 2-GiB decompression limit is **not** an appropriate default for a
16-GB host with memory-limited Docker/WSL and task runners. It is a
maximum accepted input, not a promise that the worker has enough RAM.
Prefer splitting archives or processing in smaller batches when possible.
These explicit Compose defaults also apply during the intermediate v2
upgrade; set old limits in `.env` beforehand if an active v2 workflow
depends on them.

### 2. Unverified community packages, including WAHA

v3 defaults `N8N_UNVERIFIED_PACKAGES_ENABLED` to **false**, even if
`N8N_COMMUNITY_PACKAGES_ENABLED=true`. Previously installed
*unverified* packages can stop loading; that could impact workflows
using `@devlikeapro/n8n-nodes-waha` if it is unverified for the version
you are running. **Do not assume WAHA is verified or unverified.**

The Compose default remains **false** for security. Inspect
**Settings → Community Nodes**, your installed package list,
community-package verification status and workflow dependencies
before upgrading. To preserve an unverified package that you have
explicitly evaluated and trust, set:

```dotenv
N8N_UNVERIFIED_PACKAGES_ENABLED=true
```

in your **existing** `.env` and recreate the n8n processes after
the version upgrade. This also changes the behavior during the
intermediate 2.x upgrade, so explicitly set it before restarting if
your current workflows depend on unverified nodes. It does not
automatically repair incompatible community node versions. Consider
replacing an unverified package with a verified integration or an
HTTP Request node when possible. Do not enable broadly on publicly
reachable instances without understanding the added code-execution
risk.

### 3. Chat Hub temporary opt-in, only if actually used

Chat Hub disappears from the navigation by default in v3, and will be
removed in v4. Nothing in this repository establishes that you use
Chat Hub, so it is **not enabled automatically**.

If you need it only while migrating off it, set the following **inside
the `x-n8n` shared environment mapping** in `docker-compose.yml`
(uncomment the example next to Compression), and add to `.env`:

```yaml
N8N_ENABLED_MODULES: ${N8N_ENABLED_MODULES}
```

```dotenv
N8N_ENABLED_MODULES=agents,chat-hub
```

**Preserve every module name you already enable**; the example is not
a universal default. Back up existing chat sessions/agent workflows and
plan their replacement before v4. Restart n8n and webhook processes
only after the configuration passes `docker compose config --quiet`.
Enabling the UI may not restore unsupported node versions.

### 4. Editor "Import from URL" is removed

Use **Import from File**, clipboard paste, CLI, or the n8n API. If
your workflow JSON is on GitHub or another trusted HTTPS source,
download it locally, inspect it, then import the downloaded JSON file:

```powershell
$WorkflowUrl = "https://YOUR-TRUSTED-SOURCE/workflow.json"
$Target = Join-Path $env:TEMP "n8n-workflow-import.json"
Invoke-WebRequest -Uri $WorkflowUrl -OutFile $Target
Get-Content -LiteralPath $Target -TotalCount 10
```

Use the n8n editor's **Import from File** on `$Target`, without
pasting API keys or credentials into GitHub. This import feature removal
does not affect ngrok webhook URLs or the ability to use an HTTP
Request node for external URLs.

### Validate the four changes on the existing stack

```powershell
docker compose config --quiet
docker compose ps -a
docker exec n8n-main-server n8n --version
docker compose logs --no-color --tail=80 n8n n8n-worker n8n-webhook
```

Test one ZIP archive under the new default caps, verify that existing
community nodes appear in the editor and that a WAHA workflow executes,
and import a trusted workflow through **Import from File**.
Run these checks only **after the v2 Migration Report and full backups**.

Official reference:
https://docs.n8n.io/changelog/v30-breaking-changes/

## Before touching the current instance

1. **Finish the original Redis AOF recovery** from
   [Redis recovery](redis-windows-recovery.md). The scratch-volume test
   did not repair `n8n_redis_data`. The actual Redis container must show
   `healthy` and `redis-cli ping` must return `PONG`.
2. Determine the **running** n8n version with:
   ```powershell
   docker exec n8n-main-server n8n --version
   docker compose ps
   docker compose config --quiet
   docker compose images
   ```
   If the CLI already reports **3.x**, **do not run v2-to-v3 migrations
   again or run the pre-v3 script**. Use the same-version rebuild and
   service checks below, after backing up the **current** v3 database.
3. If it reports **2.x**, use **Settings → Migration Report** (n8n 2.39+)
   to review **Workflow issues** and **Instance issues**, resolve removed
   Function/Cron/Interval and legacy AI nodes, and republish migrated
   workflows. n8n explicitly requires a full backup to return to 2.x:
   https://support.n8n.io/article/how-do-i-prepare-for-n-8-n-3-0
4. Ensure C: has enough free SSD space for Docker's VM and build cache;
   D: needs room for database and volume archives. Shut down heavy Ollama
   models during rebuild.

## 1. Use the in-place upgrade branch

PowerShell at your current directory:

```powershell
Set-Location 'D:\courses\Data Science\Data Engineering\n8n'
git status --short --branch
git fetch origin
git switch --track origin/feat/n8n-v3-beta-in-place-upgrade
```

**Stop if you have uncommitted changes** before switching. The branch is
proposed through a PR; it is not merged into main. Never overwrite
`.env` by copying `.env.example`: existing
`DB_POSTGRESDB_PASSWORD`, `N8N_ENCRYPTION_KEY`, and runner token must
stay exactly the same. Preserve `N8N_DATA_DIR` if configured.

## 2. Back up the whole existing instance

If the CLI still reports v2 and Redis/PG are healthy, inspect and run:

```powershell
Get-Content .\scripts\backup-pre-v3.ps1
.\scripts\backup-pre-v3.ps1
```

If scripts are blocked by local policy, use a scoped PowerShell
`-ExecutionPolicy Bypass -File` only after reviewing the script.

The backup script produces a dated folder **outside** the Git checkout
containing: `.env.pre-v3` (SECRET), a PostgreSQL
`pg_dump -Fc`, a stopped PostgreSQL volume tar archive, a Redis volume
tar archive, an n8n-home copy, and a version / image-ID manifest. It
checks that the tar archives are readable and intentionally **stops**
the stack. Keep this backup and a separate/off-PC copy. A lone
`redis-data-before-repair.tar.gz` is **not** sufficient rollback for a
PostgreSQL schema migration.

If n8n CLI already reports v3, take an **equivalent full backup of the
current v3 data** instead; do not use the pre-v3 script, which deliberately
rejects v3 to avoid destructive or misleading restore expectations.

## 3. Configure the SAME ngrok tunnel

Get the active HTTPS forwarding URL from an existing agent session, or
launch in a separate PowerShell terminal:

```powershell
ngrok http 80
```

Edit your existing `.env`, adding/updating only these lines while
retaining all existing secrets:

```dotenv
N8N_VERSION=3.0.1
N8N_EDITOR_BASE_URL=https://YOUR-ACTUAL-DOMAIN.ngrok-free.app
N8N_WEBHOOK_URL=https://YOUR-ACTUAL-DOMAIN.ngrok-free.app/
N8N_PROXY_HOPS=1
N8N_SECURE_COOKIE=true
N8N_RUNNERS_TASK_TIMEOUT=120
N8N_RUNNERS_TASK_REQUEST_TIMEOUT=120
N8N_DEFAULT_BINARY_DATA_MODE=database
```

**Replace the URL example with your real ngrok HTTPS address.**
The webhook variable is `N8N_WEBHOOK_URL` (n8n 2.35+
replacement for deprecated `WEBHOOK_URL`).
The Compose file falls back to `WEBHOOK_URL` if you have not migrated
the setting. Keep only one canonical URL value in `.env`.
Public ngrok forwards HTTPS to the **unchanged host port 80**; the
Docker port binding is restricted to `127.0.0.1:80:5678`, not
`0.0.0.0`. Avoid opening a router port or exposing Redis/PostgreSQL.

Changing the ngrok URL may require updating OAuth redirect URLs and
registered external webhooks. `N8N_PROXY_HOPS=1` assumes one reverse
proxy (ngrok) and trusted `X-Forwarded-*` headers.

For binary files, confirm any existing workflows that depend on
`filesystem` mode before switching to `database` mode; queue-mode
workers should use shared binary storage. Do not blindly change storage
if old binary attachments must remain accessible.

## 4. Validate Compose and the images BEFORE starting migrations

```powershell
docker compose config --quiet
docker compose build n8n n8n-runner n8n-worker n8n-worker-runner
docker compose images
```

Building these services alone does **not** migrate PostgreSQL.
`docker compose pull n8n` is **not** enough because the repo defines
custom `build:` entries. Check the build logs for failure in the
Alpine/Chromium/Python runner layers, and **do not deploy partial builds**.

The first run temporarily leaves `n8n-init` and the autoscaler disabled
with Compose profiles; this avoids an automatic credential import and
scaling while migrations/runner connectivity are being checked. WAHA
and Qdrant are optional profiles, but their existing volumes are
preserved. This does not create another Docker project.

## 5. Start the existing services in order

```powershell
docker compose up -d --no-build postgres redis
docker compose ps postgres redis
docker exec n8n-redis redis-cli ping
```

**Stop** if Redis or PostgreSQL is not healthy.

```powershell
docker compose up -d --no-build n8n
docker compose logs --tail=100 n8n
docker exec n8n-main-server n8n --version
docker compose ps n8n
```

Verify n8n CLI now reports `3.0.1` and migrations/credentials have
no errors. Do not continue if the main container is unhealthy.
Then add the runners, a single worker and the webhook processor:

```powershell
docker compose up -d --no-build n8n-runner n8n-worker n8n-worker-runner n8n-webhook
docker compose ps
docker compose logs --tail=120 n8n n8n-runner n8n-worker n8n-worker-runner n8n-webhook
```

Open `http://127.0.0.1/` and test the same existing ngrok HTTPS URL.
The UI showing healthy is **not proof** queue processing works: run a
non-destructive manual workflow that executes a JavaScript/Python Code
node and check webhook execution in the worker logs. Test credentials,
community nodes, WAHA, Qdrant, custom PDF/browser tasks one by one.

## 6. Restore optional services after passing checks

```powershell
docker compose --profile monitoring up -d redis-monitor
docker compose --profile integrations up -d qdrant waha
```

WAHA and Qdrant use their original named volumes; their exposed host
ports are now restricted to loopback. ngrok is for **n8n only**, and
does not automatically proxy those ports. Confirm their real API keys
and workflow settings; do not use the insecure example `admin` token.
The autoscaler requires **Docker socket** access and can churn your
16-GB Windows host; leave it off until you see stable queue processing.

If you explicitly accept that risk:

```powershell
docker compose --profile autoscaling up -d n8n-autoscaler
```

Do not start `n8n-init` without reviewing `scripts/provision.js`;
it automatically creates or updates some credentials. The prior code
contains an exception that always processes Microsoft SQL Server
credentials, even when one exists.

## 7. Health check / diagnostics to share after running

```powershell
docker compose config --quiet
docker compose ps -a
docker exec n8n-main-server n8n --version
docker exec n8n-redis redis-cli ping
docker compose logs --no-color --tail=80 n8n n8n-worker n8n-runner n8n-worker-runner redis
curl.exe -I http://127.0.0.1/
```

**Never paste `.env`, exported credentials, bearer tokens or API keys.**
If an image build fails, share only the specific build error. If the
editor works but webhook calls fail, inspect the ngrok agent and
`N8N_EDITOR_BASE_URL` / `N8N_WEBHOOK_URL` redacted output.

## Rollback if v3 migrations already ran

**Not:** `N8N_VERSION=2.x; docker compose up -d` — that's not a rollback.
Reverting to v2 means stopping all workers and restoring the consistent
**pre-v3 PostgreSQL, Redis, and n8n-home data** from the saved backup,
together with the original image version and `N8N_ENCRYPTION_KEY`.
Do not overwrite existing volumes before verifying the archive sizes
and practicing restoration; seek a scoped restore procedure if needed.
