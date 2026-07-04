# Troubleshooting — n8n Autoscaling Production Stack

Extended troubleshooting guide. For a quick reference, see the [README](../README.md#-troubleshooting).

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

# 4. Check autoscaler decisions
docker compose logs -f n8n-autoscaler

# 5. Check queue depth
docker compose exec redis redis-cli LLEN bull:jobs:wait

# 6. Check WAHA WhatsApp gateway status
docker compose ps waha
docker compose logs waha --tail=50
docker compose logs n8n-init --tail=50
```

---

## Autoscaler Issues

### Autoscaler not scaling / stuck

**Symptoms:** Workers not scaling up even with long queue, or not scaling down when idle.

**Step 1 — Check the autoscaler logs:**
```bash
docker compose logs -f n8n-autoscaler
```

**Step 2 — Verify `COMPOSE_PROJECT_NAME`:**

This is the most common cause. The autoscaler uses this to filter Docker containers by label. It must exactly match your Docker Compose project name.

```bash
# See what project name Docker Compose is using
docker compose ps --format "table {{.Project}}\t{{.Service}}\t{{.Status}}"

# Verify it matches .env
grep COMPOSE_PROJECT_NAME .env
```

If they don't match, update `.env`:
```dotenv
COMPOSE_PROJECT_NAME=n8n   # ← must match the prefix shown in docker compose ps
```

Then restart the autoscaler:
```bash
docker compose up -d --force-recreate n8n-autoscaler
```

**Step 3 — Check Docker socket access:**
```bash
docker compose exec n8n-autoscaler docker ps
```

If this fails, the autoscaler container cannot reach the Docker daemon. Verify the socket mount in `docker-compose.yml`:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```


---

### Autoscaler loops or makes Docker unresponsive

**Symptoms:** The host system's CPU/I/O climbs to 100%, and Docker commands (`docker ps`, `docker compose`) time out or fail. Database connections from n8n to Postgres begin timing out.

**Cause:** A bug in the replica check mechanism under high load/temporary Docker daemon timeouts. If `docker_client.containers.list()` threw an exception (e.g. timeout), the function defaulted to returning `MAX_REPLICAS + 1` (e.g. `6`). This triggered a false `SCALE DOWN` condition, leading to repeated `docker compose scale` executions that congested the host's resources.

**Fix:** The autoscaler code was corrected to return `None` on Docker API exceptions and skip the scaling logic for that iteration. Apply the fix by rebuilding the container:
```bash
docker compose up -d --build n8n-autoscaler
```

---

### Autoscaler exits immediately

**Cause:** One of the required environment variables (`REDIS_HOST`, `REDIS_PORT`, `MIN_REPLICAS`, etc.) is not set.

**Fix:** Check the logs for which variable is missing:
```bash
docker compose logs n8n-autoscaler | head -30
```

Verify all autoscaler variables are in `.env`:
```bash
grep -E "MIN_REPLICAS|MAX_REPLICAS|COMPOSE_PROJECT_NAME|QUEUE_NAME" .env
```

---

### Autoscaler scales but workers don't start

**Cause:** The `docker compose up --scale` command runs inside the autoscaler container and references the mounted `docker-compose.yml`. If the compose file has build errors or missing images, the scale command will fail silently.

**Fix:**
```bash
# Test the compose file from the host
docker compose config --quiet && echo "Config OK"

# Try a manual scale to see the error
docker compose up -d --scale n8n-worker=2 --scale n8n-worker-runner=2
```

---

## Runner Issues

### "contains no task runners"

**Symptom:** `n8n-worker-runner` exits with:
```
ERR  launcher    Config file contains no task runners
```

**Fix:**
1. Verify the config file is valid JSON:
   ```bash
   cat n8n-task-runners.json | python -m json.tool
   ```
2. Confirm the file is baked into the image (Dockerfile.runner copies it):
   ```bash
   docker compose exec n8n-worker-runner cat /etc/n8n-task-runners.json
   ```
3. Rebuild if needed:
   ```bash
   docker compose build --no-cache n8n-worker-runner
   docker compose up -d
   ```

---

### "missing required value: N8N_RUNNERS_AUTH_TOKEN"

```bash
# Verify the variable is in .env
grep N8N_RUNNERS_AUTH_TOKEN .env

# Verify the container sees it
docker compose run --rm n8n-worker-runner env | grep N8N_RUNNERS_AUTH_TOKEN
```

Generate a token if missing:
```bash
# Linux/macOS
openssl rand -hex 32

# Windows PowerShell
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

---

### Puppeteer / Playwright crashes in Code node

**Symptom:** Error like `Failed to launch the browser process` or `spawn /usr/bin/chromium-browser ENOENT`.

**Fix 1 — Always pass required flags:**
```javascript
const browser = await puppeteer.launch({
  executablePath: '/usr/bin/chromium-browser',
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
});
```

**Fix 2 — Verify Chromium is in the image:**
```bash
docker compose exec n8n-worker-runner which chromium-browser
docker compose exec n8n-worker-runner chromium-browser --version
```

If missing, the runner image needs to be rebuilt:
```bash
docker compose build --no-cache n8n-worker-runner
docker compose up -d
```

---

### Runner WebSocket `i/o timeout`

```
ERROR [launcher:py] Failed to execute `launch` command:
handshake failed: failed to read ws message: write tcp ...:5679: i/o timeout
```

**Cause:** The runner was idle too long. Mitigated by `N8N_RUNNERS_AUTO_SHUTDOWN_TIMEOUT=0`. If it persists:

```bash
docker compose restart n8n-worker-runner
```

---

### Worker: "Failed to start Python task runner in internal mode"

```
Failed to start Python task runner in internal mode. because Python 3 is missing
```

**Cause:** Worker is trying to start Python internally instead of using the external sidecar. The `N8N_RUNNERS_MODE=external` environment variable is missing from the worker.

**Fix:** Verify in `docker-compose.yml` that `n8n-worker` inherits from `x-n8n` which sets:
```yaml
- N8N_RUNNERS_MODE=external
- N8N_RUNNERS_BROKER_LISTEN_ADDRESS=0.0.0.0
```

---

### Task runner fails: "Task request timed out after 60 seconds"

```
Your Code node task was not matched to a runner within the timeout period. This indicates that the task runner is currently down, or not ready, or at capacity, so it cannot service your task.
```

**Cause:** The broker timed out waiting for a task runner to request and execute the node's code. This occurs when runners are under high resource load, are at concurrency limits, or have crashed.

**Fix:**
1. **Check task runner logs:** Ensure the runner containers are running and not crashing:
   ```bash
   docker compose logs n8n-runner
   docker compose logs n8n-worker-runner
   ```
2. **Increase request timeout:** In `.env`, increase `N8N_RUNNERS_TASK_REQUEST_TIMEOUT` to `120` or `180` (seconds) to give tasks more time to wait for a runner to become free:
   ```properties
   N8N_RUNNERS_TASK_REQUEST_TIMEOUT=120
   ```
3. **Increase runner concurrency:** If the runners are healthy but at capacity, raise the concurrent task limit in `.env`:
   ```properties
   N8N_RUNNERS_MAX_CONCURRENCY=10
   ```
4. Apply the changes:
   ```bash
   docker compose up -d
   ```

---

## Credentials & Encryption

### "Credentials could not be decrypted" / `bad decrypt`

**This is the most critical issue to prevent.**

**Cause:** n8n is using a different `N8N_ENCRYPTION_KEY` than what was used to encrypt the credentials.

**Fix:**
```bash
# Read the auto-generated key (Windows)
type n8n-data\config

# Read the auto-generated key (Linux/macOS)
cat n8n-data/config
```

Copy the `encryptionKey` value and set it in `.env`:
```dotenv
N8N_ENCRYPTION_KEY=<exact value from config file>
```

Then recreate n8n containers:
```bash
docker compose up -d --force-recreate n8n n8n-worker n8n-webhook
```

> ⚠️ **Prevention:** Always set `N8N_ENCRYPTION_KEY` in `.env` before first launch. Never change it after credentials are stored.

---

## Reverse Proxy Issues

### "ValidationError: The 'X-Forwarded-For' header is set but Express 'trust proxy' is false"

**Fix:** Add to `.env`:
```dotenv
N8N_PROXY_HOPS=1
```
Increase if you have multiple proxy layers (e.g., Cloudflare → Nginx → n8n).

---

### "ERR_NGROK_3004" or corrupted UI assets

**Cause:** IPv6 resolution conflict on Windows + Docker Desktop.

**Fix:**
```bash
ngrok http 127.0.0.1:80 --host-header=rewrite
```
Then do a hard refresh: Ctrl+F5, or DevTools → right-click refresh → **Empty Cache and Hard Reload**.

---

## Database Issues

### n8n never becomes healthy

```bash
docker compose ps
docker compose logs postgres
docker compose logs redis
```

| Problem | Fix |
|---|---|
| `postgres` unhealthy | Check `DB_POSTGRESDB_PASSWORD` matches volume initialization. If wrong, destroy volume: `docker compose down -v` |
| `redis` unhealthy | Check disk space: `df -h` |
| Port conflict | Another service using port 5432 or 6379 on the host |

---

### "database system was not properly shut down"

**This is normal after an unclean shutdown.** PostgreSQL's WAL recovery is automatic. Wait for:
```
database system is ready to accept connections
```

The `stop_grace_period: 60s` on the postgres service prevents this on clean shutdowns.

---

### Slow COMMIT warnings (`duration: Nms statement: COMMIT`)

**Cause:** Docker Desktop for Windows virtualized disk I/O latency.

**Already fixed** in `docker-compose.yml` with `synchronous_commit=off`. If you still see it, verify the postgres command flags are applied:
```bash
docker compose exec postgres psql -U n8n_user -c "SHOW synchronous_commit;"
```

---

### "password authentication failed for user"

The `postgres_data` volume was initialized with a different password.

```bash
# ⚠️ Destructive — deletes all data
docker compose down -v
docker compose up -d
```

Back up first: `docker compose exec postgres pg_dump -U n8n_user n8n > backup.sql`

---

## Workflow Execution

### Workflows stuck in queue / not executing

```bash
# Verify at least one worker is running
docker compose ps n8n-worker

# Check worker logs
docker compose logs n8n-worker | tail -30

# Check queue depth
docker compose exec redis redis-cli LLEN bull:jobs:wait

# Manually start a worker
docker compose up -d n8n-worker
```

---

### Webhook not reachable from internet

1. Set `WEBHOOK_URL=https://your-actual-public-domain.com` in `.env`
2. Ensure port 80 is open in your firewall
3. Restart: `docker compose up -d`

In n8n, webhook URLs are `https://your-domain.com/webhook/<id>` — ensure this matches `WEBHOOK_URL`.

---

### Execution shows "Error" but no useful message

Enable debug logging:
```dotenv
# Add to .env
N8N_LOG_LEVEL=debug
```
Restart and re-run: `docker compose up -d`
Then watch: `docker compose logs -f n8n n8n-worker`

---

## MCP Registry Timeout

```
Error fetching from Strapi API (https://api.n8n.io/api/mcp-servers): timeout of 6000ms exceeded
```

Non-critical. Already suppressed by `N8N_DIAGNOSTICS_ENABLED=false`. If you still see it:
```bash
docker compose exec n8n env | grep N8N_DIAGNOSTICS_ENABLED
```

---

## Performance

### High Redis memory usage

Check the current queue depths:
```bash
docker compose exec redis redis-cli INFO memory
docker compose exec redis redis-cli LLEN bull:jobs:wait
docker compose exec redis redis-cli LLEN bull:jobs:active
```

Configure execution pruning in `.env`:
```dotenv
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168    # 7 days in hours
EXECUTIONS_DATA_PRUNE_MAX_COUNT=5000
```

Raise Redis memory cap if needed — edit `redis.conf` and restart:
```bash
docker compose restart redis
```

---

### High PostgreSQL memory usage

Tune in `docker-compose.yml` postgres `command:` block and redeploy:
```bash
docker compose up -d --force-recreate postgres
```

---

### Workers not scaling down fast enough

Adjust in `.env`:
```dotenv
SCALE_DOWN_QUEUE_THRESHOLD=1   # scale down when queue < 1
COOLDOWN_PERIOD_SECONDS=10     # minimum seconds between scaling actions
```

## Container Networking & Node.js Issues

### Outbound HTTP/API requests hang or fail (IPv6 Blackhole / Happy Eyeballs)

**Symptom:** API calls to external services (like Google Gemini, OpenAI, or Strapi community node registries) hang for 30–42 seconds and fail with `fetch failed` or connection timeouts.

**Cause:** Node.js (v18+) uses the `undici` HTTP client, which implements the "Happy Eyeballs" algorithm. It attempts to connect to the IPv6 address of the destination host first. If your Docker daemon has IPv6 network routing misconfigured (or if your host machine silently drops IPv6 packets), Node.js will wait for the IPv6 TCP handshake to time out before falling back to IPv4, causing significant latency or connection drops.

**Fix:** Force all n8n Node.js containers to resolve IPv4 addresses first. This is implemented in `docker-compose.yml` under the shared template:
```yaml
environment:
  - NODE_OPTIONS=--dns-result-order=ipv4first
```
If you run manual scripts or debug node processes outside compose, be sure to pass the `NODE_OPTIONS="--dns-result-order=ipv4first"` environment variable.

---

### Outbound requests fail only on large payloads (MTU Packet Fragmentation)

**Symptom:** Tiny API test calls (e.g. pings) work instantly, but large payloads (e.g. sending 20 reviews or heavy text contexts to an AI model) hang for 60 seconds and fail with a network error.

**Cause:** Maximum Transmission Unit (MTU) mismatch. Docker's default virtual bridge network interface (`docker0`) is hardcoded to an MTU of `1500` bytes. If your host server is behind a WAN router or PPPoE connection with a lower MTU (e.g. `1492` or `1450`), Docker will send packets that exceed the router's limit. If the router drops them and firewalls block the incoming ICMP `Fragmentation Needed` packets, n8n will sit waiting for TCP handshakes until it times out.

**Fix:**
1. Test MTU size by executing a large, unfragmented ping from inside the container:
   ```bash
   docker exec -it n8n-main-server ping -c 3 -M do -s 1472 generativelanguage.googleapis.com
   ```
2. If this fails with `Frag needed` or 100% packet loss, configure Docker to clamp its MTU size down to match your network. Edit `/etc/docker/daemon.json` on the host:
   ```json
   {
     "mtu": 1450
   }
   ```
3. Restart the Docker daemon on the host:
   ```bash
   sudo systemctl restart docker
   ```

---

### AI agent/inference node times out under batch execution (Event Loop Lag)

**Symptom:** The AI node times out or throws connection closed errors when running multiple executions concurrently.

**Cause:** Batching multiple heavy API calls asynchronously without limits. Node.js is single-threaded. Firing 20 concurrent TLS handshakes to external APIs concurrently places high load on the Node event loop and network stack, causing sockets to time out before they are dispatched.

**Fix:** Force n8n nodes to execute the batches serially or with structured rate limits.
1. Open the failing node's settings in n8n.
2. Under **Batch Options** / **Batch Processing**:
   * Set **Batch Size** to `1` (serial execution).
   * Set **Delay Between Batches** to `2000` (ms) to give the network connection time to breathe.

---

## WhatsApp Integration (WAHA) Issues

### WAHA Community Node missing in n8n editor

**Symptom:** You cannot find the WhatsApp node in the n8n editor when searching for "WAHA" or "WhatsApp".

**Fix:**
1. Check the logs of the `n8n-init` one-shot provisioning container:
   ```bash
   docker compose logs n8n-init
   ```
2. If the npm installation failed due to temporary network issues, restart the installer:
   ```bash
   docker compose start n8n-init
   ```
3. Verify that the file `package.json` inside `n8n-data/nodes` lists `@devlikeapro/n8n-nodes-waha` in its dependencies.

---

### "Connection Refused" / WAHA API connection timeout in n8n

**Symptom:** Webhooks or HTTP requests to WAHA fail with connection errors.

**Fix:**
1. Verify the `waha` container is running and healthy:
   ```bash
   docker compose ps waha
   ```
2. Confirm the internal API URL in n8n matches `http://waha:3000`. Inside the Docker network `n8n-net`, services resolve each other by container service name (`waha`), not `localhost` or host IPs.
3. If connecting from outside the Docker network, ensure port `3000` is open on your host.

---

### Mismatched API Key / Authentication Errors

**Symptom:** WAHA API responds with `401 Unauthorized` or `403 Forbidden`.

**Fix:**
1. Check `WAHA_API_KEY` in `.env` matches the token n8n is sending.
2. If you changed the environment variable, restart the waha container to pick it up:
   ```bash
   docker compose up -d --force-recreate waha
   ```

---

### WhatsApp Session disconnected or stuck

**Symptom:** WhatsApp messages are not sending, or the session is marked as disconnected.

**Fix:**
1. Access the WAHA Swagger UI by navigating to `http://localhost:3000` in your web browser.
2. Query the session status via the `/api/sessions` endpoints.
3. Obtain a new QR code scan sequence or check the browser screenshot to see if WhatsApp is prompting for multi-device login:
   ```bash
   # View a live screenshot of the WAHA Chromium instance
   curl -o waha_screen.png http://localhost:3000/api/screenshot
   ```

## Ollama & AI Services Issues

### Ollama fails to run on GPU / falling back to CPU

**Symptoms:** Ollama queries are extremely slow (taking 30+ seconds for a short response), and GPU utilization (checked via `nvidia-smi`) remains at 0%.

**Cause:** 
1. Ollama may fail to initialize CUDA and default to CPU if your system's GPU driver is outdated, or if it runs into conflicts trying to select an integrated GPU over the dedicated card.
2. In virtualized environments or under high CPU load, Ollama's GPU discovery watchdog may time out (e.g., `llama-server GPU discovery watchdog timed out`), which cancels GPU initialization.

**Fix:**
Set the following environment variables globally in your User or System profile to force CUDA prioritizing and skip integrated graphics checks:
*   `OLLAMA_VULKAN=off` (forces prioritising CUDA over Vulkan)
*   `CUDA_VISIBLE_DEVICES=0` (explicitly binds to your dedicated GPU)
*   `OLLAMA_IGPU_ENABLE=0` (disables integrated GPU discovery)
*   `OLLAMA_FLASH_ATTENTION=1` (enables Flash Attention for faster evaluation)

After setting these, stop and restart Ollama.

---

### Ollama crashes or reports Out-Of-Memory (OOM) during startup

**Symptoms:** The Ollama log shows `ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate buffer of size X` and `llama-server terminated with exit status 0xc0000005`. The server crashes and doesn't respond on port 11434.

**Cause:** This happens when n8n requests a massive context window (e.g. `131,072` or `262,144` tokens) via its workflow settings. For a 3B model, a context window of 131k requires ~13.9 GB of RAM just for the KV cache. This will crash systems with standard RAM sizes (like 16GB) or GPU VRAM limits.

**Fix:**
Open your workflow in the n8n editor, click on the Ollama Chat Model node, and ensure that the **Context Window** (or `num_ctx`) parameter is set to a reasonable size (such as `4096` or `8192` at most). Never set it to very high values unless your machine has matching system RAM/VRAM capacity.

---

### n8n Main Server crashes with `JavaScript heap out of memory`

**Symptoms:** The n8n main container starts but exits soon after, or the logs show `FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory`.

**Cause:** The container's memory limit (configured via Docker Compose limits) is set too low (e.g. `512M`). n8n requires at least `1024M` (1GB) of memory to boot, load schemas, workflows, and initialize dependencies.

**Fix:**
Open `docker-compose.yml`, locate the `n8n` (and `n8n-worker`) service limits under `deploy.resources.limits`, and increase the limit:
```yaml
    deploy:
      resources:
        limits:
          memory: 1024M
```

---

### Ollama workflow execution takes several minutes (Model Swapping / HDD loading)

**Symptoms:** Requests to Ollama nodes inside n8n take 40+ seconds to finish, even for simple generation or embedding tasks. The Ollama logs show long `load_duration` times (e.g. `42000ms`) and mention loading models on every call.

**Cause:** By default, Ollama is configured to hold only `1` model in memory. If your workflow uses both an LLM (e.g., `llama3.2`) and an embedding model (e.g., `nomic-embed-text`), Ollama constantly unloads one to load the other, especially when reading from a slow hard drive (like a `D:` drive).

**Fix:**
Set the following environment variables in your Windows User profile (or system environment) and restart the Ollama process:
- `OLLAMA_MAX_LOADED_MODELS=2`: Allows both the LLM and the embedding model to reside in VRAM/RAM simultaneously.
- `OLLAMA_NUM_PARALLEL=2`: Enables parallel processing of requests.
- `OLLAMA_KEEP_ALIVE=1h`: Keeps the models loaded in memory for 1 hour of inactivity, eliminating load time overhead on subsequent runs.
- `OLLAMA_IGPU_ENABLE=0`: Ignores integrated GPUs (like Intel UHD) to prevent GPU discovery timeouts.

---

### Supabase Vector Store searches fail with `PGRST202 Could not find the function public.match_kb`

**Symptoms:** The Supabase Vector Store node fails with `Error searching for documents: PGRST202 Could not find the function public.match_kb(filter, match_count, query_embedding) in the schema cache`.

**Cause:** The Supabase node in n8n uses PostgREST RPC to call a database function named `match_kb` to match query embeddings against your vector store table. If the database function has not been created or has a different signature, PostgREST returns a `404 Not Found (PGRST202)` error.

**Fix:**
Run the following SQL in your Supabase SQL Editor to create the required vector matching function:
```sql
create or replace function match_kb (
  query_embedding vector(1536), -- 1536 matches nomic-embed-text/openai dimensions
  match_count int,
  filter jsonb default '{}'
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_variable
begin
  return query
  select
    kb.id,
    kb.content,
    kb.metadata,
    1 - (kb.embedding <=> query_embedding) as similarity
  from public.documents kb -- Replace with your actual table name if different
  where (filter = '{}'::jsonb or kb.metadata @> filter)
  order by kb.embedding <=> query_embedding
  limit match_count;
end;
$$;
```

---

## Redis Queue Reference

```bash
# Check all Bull queue states
docker compose exec redis redis-cli LLEN bull:jobs:wait      # waiting
docker compose exec redis redis-cli LLEN bull:jobs:active    # running
docker compose exec redis redis-cli LLEN bull:jobs:failed    # failed
docker compose exec redis redis-cli ZCARD bull:jobs:delayed  # delayed
docker compose exec redis redis-cli ZCARD bull:jobs:completed # completed

# Ping Redis
docker compose exec redis redis-cli ping

# List all Bull-related keys
docker compose exec redis redis-cli KEYS "bull:*"
```

---

## Getting Help

1. **Check logs first:** `docker compose logs -f`
2. **Check autoscaler:** `docker compose logs -f n8n-autoscaler`
3. **n8n community forum:** [community.n8n.io](https://community.n8n.io)
4. **n8n GitHub issues:** [github.com/n8n-io/n8n/issues](https://github.com/n8n-io/n8n/issues)
5. **Upstream autoscaling repo:** [conor-is-my-name/n8n-autoscaling](https://github.com/conor-is-my-name/n8n-autoscaling)
