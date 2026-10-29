# Upgrade your EXISTING Docker + ngrok n8n stack to pinned v3 beta

**Scope:** Same local checkout, same \`docker-compose.yml\`, same project
\`n8n\`, same port **80**, same PostgreSQL/Redis volumes, same n8n workflow
and credential store, and same ngrok forwarding command. **No new
environment is created.** The upgrade can modify the existing database.
Do not treat it as reversible by changing an image tag.

Updated October 29, 2026. Official n8n 3.0.0 beta announcement:
https://blog.n8n.io/introducing-n8n-v3/
The 3.0.1 pre-release is available as an explicit Docker image; Docker
\`:latest\` still follows **stable 2.x**, not 3.x. Your Docker Desktop
Images screen showing "updated" does not prove the running service uses
v3: this repository runs **custom-built** n8n and runner images.
The repo now pins matching \`N8N_VERSION=3.0.1\` through both Dockerfiles.

## Before touching the current instance

1. **Finish the original Redis AOF recovery** from
   [Redis recovery](redis-windows-recovery.md). The scratch-volume test
   did not repair \`n8n_redis_data\`. The actual Redis container must show
   \`healthy\` and \`redis-cli ping\` must return \`PONG\`.
2. Determine the **running** n8n version with:
   \`\`\`powershell
   docker exec n8n-main-server n8n --version
   docker compose ps
   docker compose config --quiet
   docker compose images
   \`\`\`
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

\`\`\`powershell
Set-Location 'D:\courses\Data Science\Data Engineering\n8n'
git status --short --branch
git fetch origin
git switch --track origin/feat/n8n-v3-beta-in-place-upgrade
\`\`\`

**Stop if you have uncommitted changes** before switching. The branch is
proposed through a PR; it is not merged into main. Never overwrite
\`.env\` by copying \`.env.example\`: existing
\`DB_POSTGRESDB_PASSWORD\`, \`N8N_ENCRYPTION_KEY\`, and runner token must
stay exactly the same. Preserve \`N8N_DATA_DIR\` if configured.

## 2. Back up the whole existing instance

If the CLI still reports v2 and Redis/PG are healthy, inspect and run:

\`\`\`powershell
Get-Content .\scripts\backup-pre-v3.ps1
.\scripts\backup-pre-v3.ps1
\`\`\`

If scripts are blocked by local policy, use a scoped PowerShell
\`-ExecutionPolicy Bypass -File\` only after reviewing the script.

The backup script produces a dated folder **outside** the Git checkout
containing: \`.env.pre-v3\` (SECRET), a PostgreSQL
\`pg_dump -Fc\`, a stopped PostgreSQL volume tar archive, a Redis volume
tar archive, an n8n-home copy, and a version / image-ID manifest. It
checks that the tar archives are readable and intentionally **stops**
the stack. Keep this backup and a separate/off-PC copy. A lone
\`redis-data-before-repair.tar.gz\` is **not** sufficient rollback for a
PostgreSQL schema migration.

If n8n CLI already reports v3, take an **equivalent full backup of the
current v3 data** instead; do not use the pre-v3 script, which deliberately
rejects v3 to avoid destructive or misleading restore expectations.

## 3. Configure the SAME ngrok tunnel

Get the active HTTPS forwarding URL from an existing agent session, or
launch in a separate PowerShell terminal:

\`\`\`powershell
ngrok http 80
\`\`\`

Edit your existing \`.env\`, adding/updating only these lines while
retaining all existing secrets:

\`\`\`dotenv
N8N_VERSION=3.0.1
N8N_EDITOR_BASE_URL=https://YOUR-ACTUAL-DOMAIN.ngrok-free.app
N8N_WEBHOOK_URL=https://YOUR-ACTUAL-DOMAIN.ngrok-free.app/
N8N_PROXY_HOPS=1
N8N_SECURE_COOKIE=true
N8N_RUNNERS_TASK_TIMEOUT=120
N8N_RUNNERS_TASK_REQUEST_TIMEOUT=120
N8N_DEFAULT_BINARY_DATA_MODE=database
\`\`\`

**Replace the URL example with your real ngrok HTTPS address.**
The webhook variable is \`N8N_WEBHOOK_URL\` (n8n 2.35+
replacement for deprecated \`WEBHOOK_URL\`).
The Compose file falls back to \`WEBHOOK_URL\` if you have not migrated
the setting. Keep only one canonical URL value in \`.env\`.
Public ngrok forwards HTTPS to the **unchanged host port 80**; the
Docker port binding is restricted to \`127.0.0.1:80:5678\`, not
\`0.0.0.0\`. Avoid opening a router port or exposing Redis/PostgreSQL.

Changing the ngrok URL may require updating OAuth redirect URLs and
registered external webhooks. \`N8N_PROXY_HOPS=1\` assumes one reverse
proxy (ngrok) and trusted \`X-Forwarded-*\` headers.

For binary files, confirm any existing workflows that depend on
\`filesystem\` mode before switching to \`database\` mode; queue-mode
workers should use shared binary storage. Do not blindly change storage
if old binary attachments must remain accessible.

## 4. Validate Compose and the images BEFORE starting migrations

\`\`\`powershell
docker compose config --quiet
docker compose build n8n n8n-runner n8n-worker n8n-worker-runner
docker compose images
\`\`\`

Building these services alone does **not** migrate PostgreSQL.
\`docker compose pull n8n\` is **not** enough because the repo defines
custom \`build:\` entries. Check the build logs for failure in the
Alpine/Chromium/Python runner layers, and **do not deploy partial builds**.

The first run temporarily leaves \`n8n-init\` and the autoscaler disabled
with Compose profiles; this avoids an automatic credential import and
scaling while migrations/runner connectivity are being checked. WAHA
and Qdrant are optional profiles, but their existing volumes are
preserved. This does not create another Docker project.

## 5. Start the existing services in order

\`\`\`powershell
docker compose up -d --no-build postgres redis
docker compose ps postgres redis
docker exec n8n-redis redis-cli ping
\`\`\`

**Stop** if Redis or PostgreSQL is not healthy.

\`\`\`powershell
docker compose up -d --no-build n8n
docker compose logs --tail=100 n8n
docker exec n8n-main-server n8n --version
docker compose ps n8n
\`\`\`

Verify n8n CLI now reports \`3.0.1\` and migrations/credentials have
no errors. Do not continue if the main container is unhealthy.
Then add the runners, a single worker and the webhook processor:

\`\`\`powershell
docker compose up -d --no-build n8n-runner n8n-worker n8n-worker-runner n8n-webhook
docker compose ps
docker compose logs --tail=120 n8n n8n-runner n8n-worker n8n-worker-runner n8n-webhook
\`\`\`

Open \`http://127.0.0.1/\` and test the same existing ngrok HTTPS URL.
The UI showing healthy is **not proof** queue processing works: run a
non-destructive manual workflow that executes a JavaScript/Python Code
node and check webhook execution in the worker logs. Test credentials,
community nodes, WAHA, Qdrant, custom PDF/browser tasks one by one.

## 6. Restore optional services after passing checks

\`\`\`powershell
docker compose --profile monitoring up -d redis-monitor
docker compose --profile integrations up -d qdrant waha
\`\`\`

WAHA and Qdrant use their original named volumes; their exposed host
ports are now restricted to loopback. ngrok is for **n8n only**, and
does not automatically proxy those ports. Confirm their real API keys
and workflow settings; do not use the insecure example \`admin\` token.
The autoscaler requires **Docker socket** access and can churn your
16-GB Windows host; leave it off until you see stable queue processing.

If you explicitly accept that risk:

\`\`\`powershell
docker compose --profile autoscaling up -d n8n-autoscaler
\`\`\`

Do not start \`n8n-init\` without reviewing \`scripts/provision.js\`;
it automatically creates or updates some credentials. The prior code
contains an exception that always processes Microsoft SQL Server
credentials, even when one exists.

## 7. Health check / diagnostics to share after running

\`\`\`powershell
docker compose config --quiet
docker compose ps -a
docker exec n8n-main-server n8n --version
docker exec n8n-redis redis-cli ping
docker compose logs --no-color --tail=80 n8n n8n-worker n8n-runner n8n-worker-runner redis
curl.exe -I http://127.0.0.1/
\`\`\`

**Never paste \`.env\`, exported credentials, bearer tokens or API keys.**
If an image build fails, share only the specific build error. If the
editor works but webhook calls fail, inspect the ngrok agent and
\`N8N_EDITOR_BASE_URL\` / \`N8N_WEBHOOK_URL\` redacted output.

## Rollback if v3 migrations already ran

**Not:** \`N8N_VERSION=2.x; docker compose up -d\` — that's not a rollback.
Reverting to v2 means stopping all workers and restoring the consistent
**pre-v3 PostgreSQL, Redis, and n8n-home data** from the saved backup,
together with the original image version and \`N8N_ENCRYPTION_KEY\`.
Do not overwrite existing volumes before verifying the archive sizes
and practicing restoration; seek a scoped restore procedure if needed.
