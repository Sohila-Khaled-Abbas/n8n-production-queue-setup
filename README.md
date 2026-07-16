<div align="center">

<img src="https://n8n.io/n8n-logo.png" alt="n8n Logo" width="120" />

# n8n Production Autoscaling Stack

**A production-grade, self-hosted n8n deployment with dynamic worker autoscaling, Puppeteer/Playwright browser automation, queue-mode execution, PostgreSQL persistence, and automated Redis queue monitoring.**

[![n8n Version](https://img.shields.io/badge/n8n-2.28.6-FF6D5A?logo=n8n&logoColor=white)](https://hub.docker.com/r/n8nio/n8n)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://hub.docker.com/_/postgres)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://hub.docker.com/_/redis)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-v2-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Configuration](#-configuration) · [Autoscaling](#-autoscaling) · [Puppeteer & Playwright](#-puppeteer--playwright) · [Troubleshooting](#-troubleshooting) · [Operations Guide](docs/production_guide.md) · [SE Standards](docs/software_engineering_standards.md) · [Scripts Reference](docs/scripts.md) · [Portfolio Showcase](PORTFOLIO.md) · [Changelog](CHANGELOG.md) · [Contributing Guide](CONTRIBUTING.md)

</div>

> 💼 **Looking for the Workflow Portfolio?** Check out our dedicated [Portfolio Showcase](PORTFOLIO.md) detailing 31 production-grade automation workflows with complete business cases and ready-to-import JSON files.


---

## ✨ Features

| Feature | Detail |
|---|---|
| **Dynamic Autoscaling** | Python autoscaler monitors Redis queue depth and scales workers + runners automatically |
| **n8n 2.0 External Task Runners** | Each worker has its own task runner sidecar (scaled 1:1) |
| **Puppeteer & Playwright** | Full Chromium browser automation with stealth plugins — ready in Code nodes |
| **Queue-Mode Execution** | Workflows execute via Bull/Redis queues — no single point of failure |
| **Dedicated Webhook Processor** | Separate `n8n-webhook` service handles inbound webhooks independently |
| **Redis Queue Monitor** | Continuous queue depth logging for observability |
| **PostgreSQL Backend** | Durable workflow, credential, and execution history storage |
| **Scheduled Backups** | Optional backup service: pg_dump + Redis + n8n volume → cloud via rclone |
| **WhatsApp HTTP API** | Local WAHA gateway integrated + `@devlikeapro/n8n-nodes-waha` node auto-installed |
| **HuggingFace & OpenRouter APIs** | Auto-provisioned auth for calling HF/OpenRouter models (e.g. `openai/gpt-oss-20b`) via standard and OpenAI-compatible v1 router endpoints, with built-in retry logic. |
| **Data-Engineering Ready** | `pandas`, `numpy`, `pillow`, `requests` pre-installed in Python runner |
| **Qdrant Vector DB** | Included for high-performance RAG and embeddings |
| **Production-Tuned PostgreSQL** | `shared_buffers`, `wal_buffers`, `checkpoint_completion_target` pre-configured |
| **Health Checks** | All dependencies are health-checked before n8n starts |
| **Centralized Log Rotation** | Configurable via `.env` — `LOG_DRIVER`, `LOG_MAX_SIZE`, `LOG_MAX_FILE` |
| **MCP Workflow Generator** | A standalone FastMCP AI tool hosted via SSE that autonomously generates n8n JSON workflows from text prompts using HuggingFace/Ollama/OpenRouter APIs |
| **Intelligently Tagged Portfolio** | Includes 45 production-ready workflows structurally parsed and tagged (`RAG`, `Data Pipeline`, `Orchestration`) with software engineering best practices |

---

## 📐 Architecture

```
                           ┌─────────────────────────────────────────────────────┐
                           │               n8n-net (bridge network)              │
                           │                                                      │
  Browser ───────────────►│  n8n (port 80)                                       │
                           │    ├── Editor UI & REST API                         │
                           │    ├── Task Broker (port 5679, internal)            │
                           │    └── Enqueues executions → Redis                  │
                           │                                                      │
  Webhooks ──────────────►│  n8n-webhook                                         │
                           │    └── Dedicated webhook processor                  │
                           │                                                      │
                           │  n8n-worker (autoscaled 1–N) ──────────────────────│
                           │    └── Dequeues & runs workflows                    │
                           │                                                      │
                           │  n8n-worker-runner (autoscaled 1:1 with worker) ───│
                           │    ├── JS runner  (Puppeteer, Playwright, AJV)      │
                           │    └── Python runner (pandas, numpy, pillow)        │
                           │                                                      │
                           │  n8n-autoscaler ─────────────────────────────────── │
                           │    └── Polls Redis → scales worker + runner         │
                           │                                                      │
                           │  redis-monitor ──────────────────────────────────── │
                           │    └── Logs queue depth continuously                │
                           │                                                      │
                           │  waha (port 3000) ───────────────────────────────── │
                           │    └── WhatsApp HTTP API gateway                    │
                           │                                                      │
                           │  n8n-init (One-Shot) ────────────────────────────── │
                           │    └── Seeds DB credentials & WAHA community node   │
                           │                                                      │
                           │  PostgreSQL (internal)  Redis (internal)            │
                           │  Qdrant (ports 6333/6334)                           │
                           └─────────────────────────────────────────────────────┘
```

### Services

| Container | Image | Role |
|---|---|---|
| `n8n` | Custom (`Dockerfile` based on `2.28.6`) | Editor UI, REST API, task broker |
| `n8n-webhook` | Custom (`Dockerfile` based on `2.28.6`) | Dedicated webhook processor |
| `n8n-worker` | Custom (`Dockerfile` based on `2.28.6`) | Queue worker — **autoscaled** |
| `n8n-worker-runner` | Custom (`Dockerfile.runner` based on `2.28.6`) | Task runner sidecar — **autoscaled 1:1 with worker** |
| `n8n-autoscaler` | Custom (`autoscaler/Dockerfile`) | Redis queue monitor + Docker Compose scaler |
| `redis-monitor` | Custom (`monitor/monitor.Dockerfile`) | Queue depth logger |
| `n8n-init` | `docker.n8n.io/n8nio/n8n:2.28.6` | One-shot credential provisioner |
| `n8n-postgres` | `postgres:16-alpine` | Persistent data store |
| `qdrant` | `qdrant/qdrant:latest` | Vector database |
| `waha` | `devlikeapro/waha:latest` | WhatsApp HTTP API gateway |
| `n8n-backup` | Custom (`backup/Dockerfile`) | Scheduled backups *(optional profile)* |

---

## ⚡ Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 4.x (Windows/macOS) or Docker Engine ≥ 24 + Docker Compose plugin (Linux)
- Git

### 1 · Clone

```bash
git clone https://github.com/Sohila-Khaled-Abbas/n8n-production-queue-setup.git
cd n8n-production-queue-setup
```

### 2 · Configure

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```dotenv
N8N_EDITOR_BASE_URL=https://your-public-url.example.com
WEBHOOK_URL=https://your-public-url.example.com
N8N_ENCRYPTION_KEY=<output of: openssl rand -base64 24>
N8N_RUNNERS_AUTH_TOKEN=<output of: openssl rand -hex 32>
DB_POSTGRESDB_PASSWORD=<strong password>
COMPOSE_PROJECT_NAME=n8n
```

> **`N8N_ENCRYPTION_KEY` Warning:** Generate this **once** and never change it. All credentials stored in PostgreSQL are AES-256-CBC encrypted with this key. Changing it makes all existing credentials permanently unreadable.

> **`COMPOSE_PROJECT_NAME`:** Must match the Docker Compose project name (defaults to the directory name). The autoscaler uses this to identify containers.

### 3 · Build & Launch

```bash
# Build all custom images
docker compose build

# Start the full stack in the background
docker compose up -d

# Watch logs
docker compose logs -f
```

### 4 · Open n8n

Navigate to `http://localhost` (or your public URL). Create your owner account on first launch.

---

## ⚙️ Configuration

### Environment Variables

All variables live in `.env` (never committed to git).

#### Access & Identity

| Variable | Required | Example | Description |
|---|---|---|---|
| `N8N_EDITOR_BASE_URL` | ✅ | `https://n8n.example.com` | Public URL of the n8n editor |
| `WEBHOOK_URL` | ✅ | `https://n8n.example.com` | Base URL for inbound webhooks |
| `N8N_PROXY_HOPS` | — | `1` | Number of reverse proxies (e.g. ngrok, nginx) in front of n8n |
| `N8N_LOG_LEVEL` | — | `info` | Log verbosity: `error`, `warn`, `info`, `debug` |
| `N8N_DIAGNOSTICS_ENABLED` | — | `false` | Disable telemetry & external API calls on startup |
| `COMPOSE_PROJECT_NAME` | ✅ | `n8n` | Docker Compose project name (used by autoscaler) |

#### Security

| Variable | Required | Description |
|---|---|---|
| `N8N_ENCRYPTION_KEY` | ✅ | AES-256-CBC key for credential encryption. Generate once, never change. |
| `N8N_RUNNERS_AUTH_TOKEN` | ✅ | Shared secret between n8n and task runners. |

#### Task Runners

| Variable | Required | Default | Description |
|---|---|---|---|
| `N8N_RUNNERS_MAX_CONCURRENCY` | — | `5` | Maximum number of concurrent tasks per task runner instance. |
| `N8N_RUNNERS_AUTO_SHUTDOWN_TIMEOUT` | — | `0` | Auto-shutdown timeout in ms for idle task runners (set to `0` to keep alive). |
| `N8N_RUNNERS_TASK_REQUEST_TIMEOUT` | — | `60` | Timeout (in seconds) for matching a task request to a runner before failing with a timeout error. |

#### Database

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_TYPE` | ✅ | `postgresdb` | Database engine |
| `DB_POSTGRESDB_HOST` | ✅ | `postgres` | Service name (Docker network) |
| `DB_POSTGRESDB_DATABASE` | ✅ | `n8n` | Database name |
| `DB_POSTGRESDB_USER` | ✅ | `n8n_user` | Database user |
| `DB_POSTGRESDB_PASSWORD` | ✅ | — | Database password |
| `DB_POSTGRESDB_POOL_SIZE` | — | `10` | Concurrency connection pool size for PostgreSQL |
| `DB_POSTGRESDB_CONNECTION_TIMEOUT` | — | `60000` | Database connection timeout in milliseconds |

#### Autoscaling

| Variable | Default | Description |
|---|---|---|
| `MIN_REPLICAS` | `1` | Minimum number of worker containers |
| `MAX_REPLICAS` | `5` | Maximum number of worker containers |
| `SCALE_UP_QUEUE_THRESHOLD` | `5` | Scale up when queue length exceeds this |
| `SCALE_DOWN_QUEUE_THRESHOLD` | `1` | Scale down when queue length falls below this |
| `POLLING_INTERVAL_SECONDS` | `10` | How often autoscaler checks queue depth |
| `COOLDOWN_PERIOD_SECONDS` | `10` | Minimum wait between scaling actions |
| `N8N_WORKER_SERVICE_NAME` | `n8n-worker` | Compose service name for workers |
| `N8N_WORKER_RUNNER_SERVICE_NAME` | `n8n-worker-runner` | Compose service name for runner sidecars |

#### Storage

| Variable | Default | Description |
|---|---|---|
| `N8N_DATA_DIR` | `./n8n-data` | Host path for n8n user data (workflows, credentials, binary files) |
| `N8N_DEFAULT_BINARY_DATA_MODE` | `database` | Where binary execution data is stored |

#### Log Rotation

| Variable | Default | Description |
|---|---|---|
| `LOG_DRIVER` | `json-file` | Docker log driver |
| `LOG_MAX_SIZE` | `10m` | Max size per log file |
| `LOG_MAX_FILE` | `3` | Number of log files to retain |

#### WhatsApp HTTP API (WAHA)

| Variable | Default | Description |
|---|---|---|
| `WAHA_API_KEY` | `admin` | API Key/token for WAHA gateway authentication |
| `WAHA_API_URL` | `http://waha:3000` | Internal URL of the WAHA service |

#### Ollama / AI Services

| Variable | Default / Recommended | Description |
|---|---|---|
| `OLLAMA_HOST` | `host.docker.internal:11434` | Address of the Ollama LLM server |
| `OLLAMA_MAX_LOADED_MODELS` | `2` | (Recommended) Allows both the LLM and the embedding model to stay in VRAM |
| `OLLAMA_NUM_PARALLEL` | `2` | (Recommended) Allows parallel requests to be processed |
| `OLLAMA_KEEP_ALIVE` | `1h` | (Recommended) Keeps models loaded in VRAM (avoids disk load times) |
| `OLLAMA_VULKAN` | `off` | Force prioritizes CUDA over Vulkan (host level) |
| `OLLAMA_FLASH_ATTENTION` | `1` | Enables Flash Attention for faster prompt processing (host level) |
| `CUDA_VISIBLE_DEVICES` | `0` | Binds Ollama to the dedicated GPU (host level) |
| `OLLAMA_IGPU_ENABLE` | `0` | Disables integrated GPU selection (host level) |

#### HuggingFace Inference API

| Variable | Default | Description |
|---|---|---|
| `HUGGINGFACE_API_TOKEN` | *(none)* | HuggingFace API token ("Read" scope). Create at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). Auto-provisioned as an `httpHeaderAuth` credential by `n8n-init`. |

#### Production-Grade RAG (Google Gemini Integration)

For high-performance, production-level AI reasoning without local resource constraints:
- **LLM Engine**: Integrate Google Gemini via the `@n8n/n8n-nodes-langchain.lmChatGoogleGemini` node pointing to `googlePalmApi` credentials.
- **Stealth Optimization**: This bypasses reasoning timeout failures (e.g. `Failed to receive response`) that occur when running complex ReAct/Agent workflows on local constrained LLMs (like Qwen 1.5B).
- **RAG Loading**: Always ensure that your `Load PDF` node is configured with `type: binary`, `loader: pdfLoader`, and `binaryDataKey: data`. This tells n8n to ingest actual binary PDF content instead of falling back to flat text metadata (like filenames and IDs).

> [!IMPORTANT]
> **VRAM / Memory Optimization for GPUs (e.g. GTX 1650 4GB):**
> When running local LLMs, always restrict the model's context window size to **`2048`** in n8n (inside the Ollama Chat Model node under parameters, click **Add Option** ➡️ **Context Window** and enter `2048`). By default, models like Qwen 2.5 request a 32k context size which allocates a massive ~2 GB KV Cache buffer in GPU VRAM. This will exceed a 4GB graphics card's capacity and cause Ollama to crash with an Out-of-Memory (OOM) error. Constraining it to `2048` reduces the total footprint to 1.2 GB, ensuring 100% GPU-accelerated speeds.

---

## 💻 Low-Resource PC & Stack Optimization

If you are running this production-grade stack on a local, resource-constrained Windows computer, follow these optimizations to keep both the n8n services and your PC running at maximum performance:

### 1. Cap WSL2/Docker RAM & CPU Allocation
Docker Desktop runs inside a WSL2 virtual machine, which can consume 100% of your PC's CPU and RAM if unconstrained.
- Create a `.wslconfig` file in your Windows user profile folder (`C:\Users\HELAL\.wslconfig`).
- Copy the optimized configurations from [wslconfig.txt](docs/wslconfig.txt) to cap memory and enable automatic RAM reclamation.
- Restart WSL via PowerShell: `wsl --shutdown` and restart Docker Desktop.

### 2. Node.js Memory Heap Tuning (Aggressive GC)
To prevent Node.js containers from exceeding memory limits and swapping to disk, the stack has pre-configured memory heap limits via `NODE_OPTIONS`:
- `n8n` & `n8n-worker` ➡️ capped at `768MB` heap.
- `n8n-webhook`, `n8n-runner` & `n8n-worker-runner` ➡️ capped at `384MB` heap.
This forces Node.js to garbage collect RAM aggressively, keeping the footprint tiny.

### 3. Disable Manual Test Execution Saves
In `.env`, we set:
```dotenv
EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS=false
```
This stops manual executions triggered inside the editor from writing logs to the database, saving massive disk I/O operations and disk space.

### 4. Ollama LLM Settings
If running local LLMs, always cap the context size to `2048` in the Ollama Chat Model node options inside the n8n editor, and configure Ollama to retain models in memory via environment variables (`OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=1h`).

For detailed operational guidance, see the [Operations Guide](docs/production_guide.md#wsl2-configuration-file-wslconfig) and [Troubleshooting Guide](docs/troubleshooting.md#host-pc--windows-performance-issues).

---

## 📈 Autoscaling

The `n8n-autoscaler` service runs a Python script that:

1. **Polls Redis** every `POLLING_INTERVAL_SECONDS` for the Bull queue depth (`bull:jobs:wait`)
2. **Scales up** when queue > `SCALE_UP_QUEUE_THRESHOLD` and workers < `MAX_REPLICAS`
3. **Scales down** when queue < `SCALE_DOWN_QUEUE_THRESHOLD` and workers > `MIN_REPLICAS`
4. **Respects cooldown** — waits `COOLDOWN_PERIOD_SECONDS` between any scaling action
5. **Scales worker + runner together** (1:1 ratio) in a single `docker compose up --scale` command

```bash
# Watch autoscaler decisions in real time
docker compose logs -f n8n-autoscaler

# Watch queue depth
docker compose logs -f redis-monitor

# Manually check queue length
docker compose exec redis redis-cli LLEN bull:jobs:wait

# Manually scale to 3 workers
docker compose up -d --scale n8n-worker=3 --scale n8n-worker-runner=3
```

---

## 🤖 MCP Workflow Generator

The `mcp_server` directory contains a standalone **Model Context Protocol (MCP)** server built with `FastMCP` that generates n8n JSON workflows autonomously from text prompts. It connects to HuggingFace, Ollama, or OpenRouter based on your `.env` configuration.

- **Modern UI**: Visit the server URL in your browser for a sleek status dashboard and connection instructions.
- **Connection**: To connect n8n to this server, use the Server-Sent Events (SSE) transport and specify the `/sse` endpoint in n8n (e.g., `http://mcp-server:8000/sse` or `http://localhost:8000/sse`).

For more details on running the server and configuring your LLM API keys, see the [MCP Server README](mcp_server/README.md).

---

## 🌐 Puppeteer & Playwright

The `n8n-worker-runner` image includes full Chromium browser automation support:

### Pre-installed JavaScript Packages

| Package | Description |
|---|---|
| `puppeteer-core@22.15.0` | Browser automation (Puppeteer) |
| `puppeteer-extra` | Puppeteer with plugin support |
| `puppeteer-extra-plugin-stealth` | Bot detection evasion |
| `playwright-core` | Browser automation (Playwright) |
| `playwright-extra` | Playwright with plugin support |
| `ajv` | JSON schema validation |
| `ajv-formats` | Additional AJV formats |

### Pre-installed Python Packages

| Package | Description |
|---|---|
| `requests` | HTTP library |
| `pillow` | Image processing (PIL) |
| `pandas` | Data analysis |
| `numpy` | Numerical computing |

### Pre-installed System Utilities

| Tool | Description |
|---|---|
| `chromium-browser` | Headless browser |
| `ffmpeg` / `ffprobe` | Video/audio processing |
| `imagemagick` | Image manipulation (`magick`, `convert`, `identify`, `mogrify`, `composite`) |
| `graphicsmagick` | Image manipulation (`gm`) |
| `git` | Version control |

### Quick Example (Puppeteer)

```javascript
const puppeteer = require('puppeteer-core');

const browser = await puppeteer.launch({
  executablePath: '/usr/bin/chromium-browser',
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
});

const page = await browser.newPage();
await page.goto('https://example.com');
const title = await page.title();
await browser.close();

return [{ json: { title } }];
```

### Quick Example (Playwright with Stealth)

```javascript
const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

chromium.use(StealthPlugin());

const browser = await chromium.launch({
  executablePath: '/usr/bin/chromium-browser',
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
});

const page = await browser.newPage();
await page.goto('https://example.com');
const title = await page.title();
await browser.close();

return [{ json: { title } }];
```

### Adding More npm Packages

1. Edit `Dockerfile.runner` — append to the `pnpm add` block:
   ```dockerfile
   RUN /usr/local/bin/node /usr/local/lib/node_modules/corepack/dist/corepack.js pnpm add \
       ... \
       your-package-here
   ```
2. Edit `n8n-task-runners.json` — add to `NODE_FUNCTION_ALLOW_EXTERNAL`
3. Rebuild: `docker compose build --no-cache n8n-worker-runner && docker compose up -d`

### Adding More Python Packages

1. Edit `Dockerfile.runner` — append to the `uv pip install` block:
   ```dockerfile
   RUN /usr/local/bin/uv pip install --python /opt/runners/task-runner-python/.venv/bin/python --no-cache \
       ... \
       your-package-here
   ```
2. Edit `n8n-task-runners.json` — add to `N8N_RUNNERS_EXTERNAL_ALLOW`
3. Rebuild: `docker compose build --no-cache n8n-worker-runner && docker compose up -d`

---

## 💾 Backup (Optional)

The `n8n-backup` service is **disabled by default** and requires the `backup` profile:

```bash
# Enable backups
docker compose --profile backup up -d

# Run a one-off backup immediately
BACKUP_RUN_ON_START=true docker compose --profile backup up n8n-backup
```

**What gets backed up:**
- PostgreSQL database via `pg_dump`
- Redis RDB snapshot
- n8n volume data (custom nodes, local files)

All bundled into a single timestamped `.tar.gz` (optionally GPG-encrypted, optionally uploaded via rclone).

**Key backup variables:**

| Variable | Default | Description |
|---|---|---|
| `BACKUP_SCHEDULE` | `0 2 * * *` | Cron schedule (daily at 2 AM) |
| `BACKUP_RETENTION_DAYS` | `30` | Days to keep old backups |
| `BACKUP_ENCRYPTION_KEY` | *(empty)* | GPG passphrase (empty = no encryption) |
| `BACKUP_RCLONE_DESTINATIONS` | *(empty)* | Comma-separated rclone remotes |

---

## 🔄 Common Operations

```bash
# View live logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f n8n-autoscaler
docker compose logs -f n8n-worker-runner
docker compose logs -f redis-monitor

# Restart a single service
docker compose restart n8n

# Rebuild runner after adding packages
docker compose build --no-cache n8n-worker-runner
docker compose up -d

# Take a manual database backup
docker compose exec postgres pg_dump -U n8n_user n8n > backup_$(date +%Y%m%d).sql

# Stop the stack (data is preserved in volumes)
docker compose down

# Destroy everything including volumes (⚠️ irreversible — data gone)
docker compose down -v
```

---

## 🛠️ Troubleshooting

### Autoscaler not scaling

```bash
docker compose logs -f n8n-autoscaler
```

Check `COMPOSE_PROJECT_NAME` in `.env` — it must exactly match the Docker Compose project name (run `docker compose ps` to see the project prefix).

---

### Autoscaler loops or makes Docker unresponsive

If the Docker daemon experiences high CPU/I/O load or temporary timeouts, a bug in the replica check could trigger an infinite loop of `docker compose scale` commands. 
* **Fix:** The autoscaler script has been updated to handle Docker API exceptions by skipping the scaling check instead of falling back to a scale-down command. Rebuild the autoscaler container to apply the fix:
  ```bash
  docker compose up -d --build n8n-autoscaler
  ```

---

### Ollama is slow or fails to run on GPU

* **Check model context window in n8n:** A context window size of `131k` or more requires over 13GB of KV cache memory, which will exceed a 4GB/8GB GPU or 16GB RAM machine and crash the LLM server. Keep the `Context Window` setting in the n8n Ollama Node to `4096`.
* **GPU watchdog timeout:** High CPU/disk load can cause Ollama's GPU discovery to time out. Set these environment variables globally in your User/System profile to optimize discovery and force GPU usage:
  * `OLLAMA_VULKAN=off` (Forces CUDA prioritize)
  * `CUDA_VISIBLE_DEVICES=0` (Binds dedicated GPU)
  * `OLLAMA_FLASH_ATTENTION=1` (Enables flash attention)

---

### Task runner fails: "contains no task runners"

The launcher is reading a stale config file.

```bash
docker compose restart n8n-worker-runner
```

---

### Task runner fails: "missing required value: N8N_RUNNERS_AUTH_TOKEN"

The token is not set in `.env`:

```bash
docker compose run --rm n8n-worker-runner env | grep N8N_RUNNERS_AUTH_TOKEN
```

---

### Puppeteer / Playwright crashes

Check that you're passing `--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage` in your launch args. These are required inside Docker containers.

---

### Workflows not executing

In queue mode, at least one worker must be running:

```bash
docker compose ps n8n-worker
docker compose logs -f n8n-worker
```

---

### n8n-main never becomes healthy

Check that PostgreSQL and Redis are healthy first:

```bash
docker compose ps
docker compose logs postgres
docker compose logs redis
```

---

### Redis container crash-loop (AOF Corruption)

**Symptom:** The `redis` container keeps restarting (`Restarting (1) 4 seconds ago`), and logs show:
```
Bad file format reading the append only file appendonly.aof.1.incr.aof
```

**Solution:**
Use the Redis check tool inside a temporary container to truncate the corrupt tail block:
```bash
docker compose run --rm redis redis-check-aof --fix /data/appendonlydir/appendonly.aof.manifest
```
Confirm with `y` when prompted to apply the fix. Redis will then start normally.

---

### MCP registry timeout on startup

```
Error fetching from Strapi API: timeout of 6000ms exceeded
```

Non-critical. Suppressed by `N8N_DIAGNOSTICS_ENABLED=false` — verify it's set.

---

### WAHA WhatsApp API connection issues

If n8n cannot connect to WAHA:
1. Verify the `waha` container is running: `docker compose ps waha`
2. Check `waha` container logs: `docker compose logs waha`
3. Ensure the community node `@devlikeapro/n8n-nodes-waha` was installed by checking `n8n-init` logs: `docker compose logs n8n-init`
4. Confirm `WAHA_API_KEY` in `.env` matches the key configured inside the WAHA container.

---

### Redis connection check

```bash
# Verify Redis is responding (no auth — unauthenticated setup)
docker compose exec redis redis-cli ping

# Check queue length manually
docker compose exec redis redis-cli LLEN bull:jobs:wait
```

---

### Google Drive / API node connection closed unexpectedly (ECONNRESET)

**Symptom:** Operations like downloading a file from Google Drive fail with: `The connection to the server was closed unexpectedly, perhaps it is offline. You can retry the request immediately or wait and retry later.`

**Solution:**
1. **Switch to Filesystem Storage:** In `.env`, set `N8N_DEFAULT_BINARY_DATA_MODE=filesystem`. This prevents worker container crashes by streaming files to disk rather than buffering them in memory, avoiding Out-Of-Memory (OOM) network/socket terminations.
2. **Enable Node Retries:** Open the node settings in the editor UI and enable **Retry on Fail** with `3` attempts and `3000`ms wait.
3. **Reconnect Credentials:** Re-authenticate your Google Drive or API credentials to refresh stale OAuth2 tokens.
4. See **[troubleshooting.md](docs/troubleshooting.md)** for a complete checklist.

---

### Pinecone Console / API Connection Timeout (`ERR_CONNECTION_TIMED_OUT`)

**Symptom:** Opening `app.pinecone.io` in your browser fails with `ERR_CONNECTION_TIMED_OUT`, or n8n Pinecone nodes time out.

**Solution:**
1. **Use a VPN:** Route browser and Docker host traffic through a VPN to bypass regional ISP network blockages (e.g. in Egypt).
2. **Configure Custom DNS:** Switch DNS settings to Google DNS (`8.8.8.8`) or Cloudflare DNS (`1.1.1.1`).
3. See **[troubleshooting.md](docs/troubleshooting.md)** for details on routing local Docker containers or hosting on VPS outside restricted regions.

---

## 🛠️ Operational & Diagnostic Scripts

The `scripts/` directory contains automation and database diagnostic scripts to maintain and troubleshoot the n8n production stack:

### Workflow Export Automation
- **[export_workflows.py](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/export_workflows.py)**: A Windows/Unix-compatible Python script that automates exporting all workflows from the n8n container database and splitting them into separate formatted JSON files inside the `workflows/` directory. Run this whenever you create new workflows or edit existing ones to sync them to the git repository:
  ```bash
  python scripts/export_workflows.py
  ```

### Workflow Node Automation (Ollama VRAM Optimization)
If you run into GPU Out-of-Memory (OOM) crashes on constrained GPUs (like a 4GB GTX 1650) when running local LLMs, you can batch-optimize your workflows:
- **[parse_nodes.py](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/parse_nodes.py)**: Scans a raw JSON workflow export (`workflow_nodes_raw.json`) and prints details of all Ollama chat model nodes.
- **[modify_workflow.py](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/modify_workflow.py)**: Automatically updates all Ollama chat nodes in `workflow_nodes_raw.json` to use `qwen2.5:1.5b` with a restricted context window of `2048` tokens (saving VRAM and preventing crashes), outputting `workflow_nodes_modified.json` for easy re-import.

### Database Maintenance & Cleanup
- **[cleanup.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/cleanup.sql)**: A PostgreSQL script to safely prune stale execution data older than 3 days, mark orphaned execution tasks as `crashed`, reclaim disk space using `VACUUM FULL`, and report table disk sizes.

### Database Diagnostic Queries
Run these queries inside the PostgreSQL database to troubleshoot workflow performance and errors:
- **[count_chat.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/count_chat.sql)**: Aggregates and counts chat history messages by session ID.
- **[durations.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/durations.sql)**: Analyzes and lists the duration and status of the 15 most recent executions.
- **[durations_times.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/durations_times.sql)**: Analyzes execution durations specifically for a given workflow ID.
- **[get_error.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/get_error.sql)**: Extracts raw error logs from execution data for a specific execution ID.
- **[get_keys.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/get_keys.sql)**: Identifies JSON result keys within execution logs.
- **[search_errors.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/search_errors.sql)**: Searches and extracts detailed error messages across all execution JSON blocks.

---

## 📁 Repository Structure

```
.
├── docker-compose.yml              # Full service orchestration
├── Dockerfile                      # Main n8n image (ffmpeg, git, jq, gm)
├── Dockerfile.runner               # Task runner image (Chromium, Puppeteer, Playwright, Python)
├── n8n-task-runners.json           # Runner launcher configuration
├── redis.conf                      # Production Redis configuration
├── .env.example                    # Environment variable template
├── .env                            # Your configuration (git-ignored)
├── .gitignore                      # Excludes secrets and runtime data
├── docs/                           # Documentation folder
│   ├── production_guide.md         # Production config & tuning guide
│   ├── software_engineering_standards.md # Repository software engineering guidelines
│   ├── scripts.md                  # Scripts directory index and run instructions
│   ├── troubleshooting.md          # Exhaustive troubleshooting checklist
│   ├── architecture.md             # Stack components architecture in-depth
│   └── infographic.svg             # Component interaction blueprint
├── autoscaler/
│   ├── Dockerfile                  # Autoscaler container (Python 3.12, multi-arch)
│   ├── autoscaler.py               # Scaling logic (Redis → docker compose)
│   └── requirements.txt            # redis, docker, python-dotenv
├── monitor/
│   ├── monitor.Dockerfile          # Redis monitor container (non-root)
│   └── monitor_redis_queue.py      # Queue depth logger
├── backup/
│   ├── Dockerfile                  # Backup container
│   ├── backup.py                   # pg_dump + Redis + rclone logic
│   └── rclone.conf.example         # Example rclone cloud storage config
├── CHANGELOG.md                    # Project version history
├── CONTRIBUTING.md                 # Development & contribution guidelines
├── LICENSE                         # MIT License
├── PORTFOLIO.md                    # Workflow portfolio details
├── README.md                       # This file
├── scripts/
│   ├── export_workflows.py         # Automates workflow backup and extraction
│   ├── provision.js                # One-shot credential provisioner (n8n-init)
│   ├── cleanup.sql                 # Database cleanup and VACUUM script
│   ├── count_chat.sql              # Aggregates chat count by session
│   ├── durations.sql               # Diagnostic for execution durations
│   ├── durations_times.sql         # Diagnostic for workflow execution durations
│   ├── get_error.sql               # Diagnostic to retrieve execution errors
│   ├── get_keys.sql                # Diagnostic to inspect execution JSON keys
│   ├── search_errors.sql           # Diagnostic to search error messages in execution logs
│   ├── parse_nodes.py              # Scans workflow nodes for Ollama chat nodes
│   └── modify_workflow.py          # Batch configures Ollama nodes (model & context)
├── workflows/
│   ├── GPT_OSS_20B_HuggingFace.json  # HuggingFace Inference API workflow (openai/gpt-oss-20b)
│   └── ...                         # 35+ production workflow JSON files
├── n8n-data/                       # n8n user data (git-ignored)
├── backups/                        # Local backup output (git-ignored)
```

---

## 🤝 Contributing

Pull requests are welcome. For significant changes, please open an issue first. 

Please review our comprehensive [Contributing Guidelines](CONTRIBUTING.md) before submitting code. All contributions must adhere to the [Software Engineering Standards](docs/software_engineering_standards.md), including:
- Conventional Commit message formats.
- Python quality checks via Ruff.
- Verification workflows inside GitHub Actions.

---

## 📜 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

> This project is a **deployment configuration** for [n8n](https://n8n.io), which is [fair-code licensed](https://faircode.io). Review n8n's own license before deploying commercially.
>
> Based on [conor-is-my-name/n8n-autoscaling](https://github.com/conor-is-my-name/n8n-autoscaling) — adapted for this environment.
