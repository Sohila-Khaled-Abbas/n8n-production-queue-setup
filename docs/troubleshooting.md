# Troubleshooting — n8n Production Stack

Extended troubleshooting guide. For a quick reference, see the [README](../README.md#troubleshooting).

---

## Diagnostic Checklist

Run these commands first whenever something is broken:

```bash
# 1. Check which containers are running and their health status
docker compose ps

# 2. Tail all logs simultaneously
docker compose logs -f --tail=50

# 3. Check resource usage
docker stats --no-stream
```

---

## Credentials & Encryption Issues

### "Credentials could not be decrypted" / `error:1C800064:Provider routines::bad decrypt`

**This is the most important issue to prevent.** It means n8n is trying to decrypt credentials with a different key than what was used to encrypt them.

**Root cause — look for this line in `docker compose logs n8n`:**
```
No encryption key found - Auto-generating and saving to: /home/node/.n8n/config
```

If you see this, n8n generated a new random key because `N8N_ENCRYPTION_KEY` was not set in `.env`. Any credentials already stored in PostgreSQL from a previous session are now unreadable.

**Fix — two parts:**

**Part 1: Pin the key permanently in `.env`**

Read the current key that n8n auto-generated:
```bash
# On Windows
type n8n-data\config

# On Linux/macOS
cat n8n-data/config
```

This outputs something like:
```json
{
    "encryptionKey": "MP81UEDl6uFA2UGE1oB/6XEz/iHmW7DL"
}
```

Add that exact value to `.env`:
```dotenv
N8N_ENCRYPTION_KEY=MP81UEDl6uFA2UGE1oB/6XEz/iHmW7DL
```

Then recreate the n8n containers (not the DB):
```bash
docker compose up -d --force-recreate n8n n8n-worker
```

**Part 2: Re-enter your credentials in the UI**

Credentials encrypted with an old/lost key cannot be recovered. You must:
1. Open the n8n editor
2. Go to **Credentials**
3. Delete the broken credentials (they will show a decryption error)
4. Re-create them from scratch by entering your API keys again

> ⚠️ **Prevention:** Always set `N8N_ENCRYPTION_KEY` in `.env` *before* first launch. Generate with: `openssl rand -base64 24`. See `.env.example` for the required variable.

---

## Reverse Proxy Issues

### "ValidationError: The 'X-Forwarded-For' header is set but the Express 'trust proxy' setting is false"

**Cause:** n8n's rate-limiting middleware is receiving proxy headers (e.g., from ngrok, Nginx, or Traefik) but n8n is not configured to trust them.

**Fix:** Tell n8n how many reverse proxy layers are in front of it. Add the following to `.env`:
```dotenv
N8N_PROXY_HOPS=1
```
(Increase the number if you have a multi-tier proxy, e.g., Cloudflare -> Nginx -> n8n).

Restart the stack after changing the configuration:
```bash
docker compose down
docker compose up -d
```

### "Error connecting to n8n. Could not connect to server. Refresh to try again"

**Cause:** The frontend lost its WebSocket / Push connection to the backend. This frequently occurs when you restart the n8n Docker containers in the background while the browser tab is still open.

**Fix:** A simple browser hard-refresh (Ctrl+F5 or Cmd+Shift+R) will reconnect the frontend. If it persists across hard refreshes, ensure your reverse proxy properly supports WebSocket connections and that `N8N_EDITOR_BASE_URL` matches your access URL perfectly.

---

## Runner Issues

### "contains no task runners"

**Symptom:** `n8n-python-runner` exits immediately with a message like:
```
ERR  launcher    Config file contains no task runners
```

**Cause:** The container is reading a malformed or empty `n8n-task-runners.json`, or the file mount failed.

**Fix:**

1. Verify the file is valid JSON:
   ```bash
   cat n8n-task-runners.json | python -m json.tool
   ```
2. Confirm the bind mount is active:
   ```bash
   docker compose exec n8n-python-runner cat /etc/n8n-task-runners.json
   ```
3. If the file looks correct, recreate the container:
   ```bash
   docker compose up -d --force-recreate n8n-python-runner
   ```

---

### "missing required value: N8N_RUNNERS_AUTH_TOKEN"

**Cause:** The `N8N_RUNNERS_AUTH_TOKEN` variable is not set or not being passed to the container.

**Diagnosis:**
```bash
# Check the variable is in .env
grep N8N_RUNNERS_AUTH_TOKEN .env

# Verify the container sees it
docker compose run --rm n8n-python-runner env | grep N8N_RUNNERS_AUTH_TOKEN
```

**Fix:** Generate a token and add it to `.env`:
```bash
# On Linux/macOS
openssl rand -hex 32

# On Windows (PowerShell)
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Then set the same value in `.env`:
```dotenv
N8N_RUNNERS_AUTH_TOKEN=<generated token>
```

Restart the stack: `docker compose up -d`

---

### Runner connects but tasks timeout

**Cause:** Network latency between worker and runner, or the runner subprocess crashed silently.

**Diagnosis:**
```bash
# Check runner health endpoints (from inside another container)
docker compose exec n8n wget -qO- http://n8n-python-runner:5680/healthz
```

**Fix:**
```bash
docker compose restart n8n-python-runner
docker compose logs -f n8n-python-runner
```

---

### Runner WebSocket `i/o timeout` handshake error

```
ERROR [launcher:py] Failed to execute `launch` command:
handshake failed: failed to read ws message: write tcp ...:5679: i/o timeout
```

**Cause:** The runner was idle too long and its WebSocket connection to the broker timed out. This is mitigated by `N8N_RUNNERS_AUTO_SHUTDOWN_TIMEOUT=0` in `docker-compose.yml`, which keeps the runner alive indefinitely. If you still see it, the runner container was restarted while the broker was unavailable.

**Fix:** Docker's `restart: unless-stopped` handles this automatically. If it persists:
```bash
docker compose restart n8n-python-runner
```

---

### Worker: "Failed to start Python task runner in internal mode"

```
Failed to start Python task runner in internal mode. because Python 3 is missing
```

**Cause:** The worker is trying to start Python internally instead of using the external runner sidecar. This means `N8N_RUNNERS_MODE=external` is missing from the worker's environment.

**Fix:** Verify `docker-compose.yml` has this in `n8n-worker`'s environment:
```yaml
- N8N_RUNNERS_MODE=external
- N8N_RUNNERS_BROKER_LISTEN_ADDRESS=0.0.0.0
```

Also verify that `n8n-python-runner` points to the worker:
```yaml
- N8N_RUNNERS_TASK_BROKER_URI=http://n8n-worker:5679
```

---

## Deprecation Warnings on Startup

### `N8N_RUNNERS_ENABLED -> Remove this environment variable`

Remove `N8N_RUNNERS_ENABLED` from `.env`. It is no longer recognized in n8n v2.25+.

### `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS`

This is already set to `true` in `docker-compose.yml`. Do not set it in `.env`.

---

## MCP Registry Timeout

```
Error fetching from Strapi API (https://api.n8n.io/api/mcp-servers): timeout of 6000ms exceeded
Failed to refresh MCP registry
```

**Cause:** n8n tries to reach `api.n8n.io` on startup. In restricted network environments this times out after 6 seconds.

**Fix:** Already suppressed in this stack by `N8N_DIAGNOSTICS_ENABLED=false` in `docker-compose.yml`. If you see this again, verify the variable is present:
```bash
docker compose exec n8n env | grep N8N_DIAGNOSTICS_ENABLED
```

---

## Database Issues

### n8n-main never becomes healthy

**Symptom:** `docker compose ps` shows `n8n-main` stuck in `starting` or `unhealthy`.

**Cause:** PostgreSQL or Redis is not ready.

**Diagnosis:**
```bash
docker compose ps          # check all health statuses
docker compose logs postgres
docker compose logs redis
```

**Common fixes:**

| Problem | Fix |
|---|---|
| `postgres` unhealthy | Check `DB_POSTGRESDB_PASSWORD` matches what Postgres was initialized with. If not, destroy the volume: `docker compose down -v` and restart |
| `redis` unhealthy | Redis rarely fails. Check disk space: `df -h` |
| Port conflict | Another Postgres/Redis is already running on the host. Change `DB_POSTGRESDB_PORT` / redis port in `docker-compose.yml` |

---

### PostgreSQL: "database system was not properly shut down"

```
database system was not properly shut down; automatic recovery in progress
```

**Cause:** Docker killed the container before PostgreSQL finished writing its shutdown checkpoint. Docker's default stop timeout is 10 seconds — not long enough.

**This is fixed in `docker-compose.yml`** by `stop_grace_period: 60s` on the `postgres` service, which gives it up to 60 seconds to flush WAL and write the shutdown record cleanly.

If you still see this after the fix, it means the host was restarted abruptly (power loss, SIGKILL). PostgreSQL's WAL recovery is automatic and safe — just wait for `database system is ready to accept connections`.

> Never investigate this message unless Postgres *fails to reach the ready state* afterwards.

---

### Slow COMMIT warnings (`duration: Nms  statement: COMMIT`)

```
2026-06-11 11:50:25 UTC [248] LOG:  duration: 1153.883 ms  statement: COMMIT
```

**Cause:** On Docker Desktop for Windows, the virtualised disk layer adds significant fsync latency. By default, PostgreSQL waits for the OS to confirm the WAL was physically written to disk before returning from `COMMIT` — on Windows + Docker this can take 1–3 seconds.

**Fixed by `synchronous_commit=local`** in `docker-compose.yml`. This setting tells Postgres to flush WAL to the OS page cache (protecting against process crashes) but not wait for the physical disk write confirmation. The result is sub-millisecond COMMIT responses while maintaining full protection against n8n crashes.

**Durability trade-off:** With `synchronous_commit=local`, in the event of a *complete OS/hardware crash* (not just a process crash), the last ~1 second of committed transactions could theoretically be lost. For n8n workflow execution metadata this is an acceptable trade-off; for financial transactions it would not be.

The `log_min_duration_statement` threshold is set to `2000ms` (2 seconds) so only genuinely slow queries (not fsync waits) appear in logs.

---



### "password authentication failed for user"

**Cause:** The `postgres_data` volume was created with a different password than what's in `.env`.

**Fix (destructive — deletes all data):**
```bash
docker compose down -v
docker compose up -d
```

> ⚠️ This wipes all workflow definitions and execution history. Back up first if needed.

---

### Database migration fails on startup

**Symptom:** n8n logs show `ERROR Migration … failed`.

**Fix:**
```bash
# Check full migration output
docker compose logs n8n | grep -i migrat

# If a migration is stuck, force-recreate n8n-main
docker compose up -d --force-recreate n8n
```

If the issue persists, open an issue at [n8n's GitHub](https://github.com/n8n-io/n8n/issues) with the migration error message.

---

## Workflow Execution Issues

### Workflows not executing (stuck in queue)

**Cause:** No worker is running, or the worker lost its Redis connection.

**Diagnosis:**
```bash
docker compose ps n8n-worker
docker compose logs n8n-worker | tail -30
```

**Fix:**
```bash
docker compose up -d n8n-worker
```

---

### Execution history shows "Error" but no useful message

1. Enable verbose logging:
   ```dotenv
   # Add to .env
   N8N_LOG_LEVEL=debug
   ```
2. Restart: `docker compose up -d`
3. Re-run the workflow and check `docker compose logs -f n8n`

---

### Webhook not reachable from the internet

**Cause:** `WEBHOOK_URL` is not set to the correct public URL, or the host firewall blocks port 80.

**Fix:**
1. Set `WEBHOOK_URL=https://your-actual-public-domain.com` in `.env`.
2. Ensure port 80 (or your reverse-proxy port) is open in your firewall / cloud security group.
3. Restart: `docker compose up -d`

---

## AI Services

### Python Code nodes run out of memory (OOM)

**Cause:** Processing large datasets (e.g. hundreds of megabytes of CSVs or Parquet files) using `pandas` or `pyarrow` inside the Python runner exceeds the container's memory limits.

**Fix:** 
1. **Streaming Data:** Instead of loading full files into memory, use `pandas` chunking (`chunksize` in `read_csv`) or `pyarrow.dataset` to stream data.
2. **Pushdown to Data Warehouse:** If connected to BigQuery or Snowflake, perform joins and aggregations directly in the warehouse using SQL queries instead of downloading data to process in Python locally.
3. **Increase limits:** If you have free RAM, consider explicitly assigning more memory to the `n8n-python-runner` in `docker-compose.yml`.

---

### n8n cannot connect to Qdrant

**Cause:** The internal Docker network addresses are incorrect or the container crashed.

**Fix:**
1. In n8n credentials, ensure you are using `http://qdrant:6333` for Qdrant. Do not use `localhost` (which resolves to the n8n container itself).
2. Check container health:
   ```bash
   docker compose ps qdrant
   ```

---

## Scaling Issues

### "Cannot start service n8n-worker: container name … is already in use"

**Cause:** `container_name: n8n-worker-1` is set in `docker-compose.yml`, which prevents `--scale` from creating multiple containers.

**Fix:** Remove (or comment out) the `container_name` line for `n8n-worker` and `n8n-python-runner` before scaling:
```yaml
# container_name: n8n-worker-1   ← remove this line
```

Then:
```bash
docker compose up -d --scale n8n-worker=3
```

---

## Performance

### High memory usage by PostgreSQL

PostgreSQL is already tuned via command-line flags in `docker-compose.yml` (`shared_buffers=256MB`, `work_mem=16MB`). For heavier workloads, increase these values and redeploy:

```bash
docker compose up -d --force-recreate postgres
```

### High Redis memory usage

If execution history grows large, configure n8n to prune old executions:
```dotenv
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168   # hours (7 days)
```

Redis also has a hard memory cap (`maxmemory 256mb` in `redis.conf`). Raise this if needed and restart Redis:
```bash
docker compose restart redis
```

---

## Getting Help

1. **Check the logs first:** `docker compose logs -f`
2. **Search the n8n community forum:** [community.n8n.io](https://community.n8n.io)
3. **File a GitHub issue:** [github.com/n8n-io/n8n/issues](https://github.com/n8n-io/n8n/issues)
4. **Open an issue on this repo** for deployment-config-specific problems.
