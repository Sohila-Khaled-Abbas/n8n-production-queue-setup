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
# Check runner health endpoints
curl http://localhost:5681/healthz   # JS runner
curl http://localhost:5682/healthz   # Python runner
```

**Fix:**
```bash
docker compose restart n8n-python-runner
docker compose logs -f n8n-python-runner
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

PostgreSQL defaults are conservative. For large workloads, tune `shared_buffers` and `work_mem` via environment variables or a mounted `postgresql.conf`.

### High Redis memory usage

If execution history grows large, configure n8n to prune old executions:
```dotenv
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168   # hours (7 days)
```

---

## Getting Help

1. **Check the logs first:** `docker compose logs -f`
2. **Search the n8n community forum:** [community.n8n.io](https://community.n8n.io)
3. **File a GitHub issue:** [github.com/n8n-io/n8n/issues](https://github.com/n8n-io/n8n/issues)
4. **Open an issue on this repo** for deployment-config-specific problems.
