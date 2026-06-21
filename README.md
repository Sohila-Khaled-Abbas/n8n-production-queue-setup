<div align="center">

<img src="https://n8n.io/n8n-logo.png" alt="n8n Logo" width="120" />

# n8n Production Autoscaling Stack

**A production-grade, self-hosted n8n deployment with dynamic worker autoscaling, Puppeteer/Playwright browser automation, queue-mode execution, PostgreSQL persistence, and automated Redis queue monitoring.**

[![n8n Version](https://img.shields.io/badge/n8n-2.0+-FF6D5A?logo=n8n&logoColor=white)](https://hub.docker.com/r/n8nio/n8n)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://hub.docker.com/_/postgres)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://hub.docker.com/_/redis)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-v2-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Configuration](#-configuration) · [Autoscaling](#-autoscaling) · [Puppeteer & Playwright](#-puppeteer--playwright) · [Troubleshooting](#-troubleshooting)

</div>

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
| **Data-Engineering Ready** | `pandas`, `numpy`, `pillow`, `requests` pre-installed in Python runner |
| **Qdrant Vector DB** | Included for high-performance RAG and embeddings |
| **Production-Tuned PostgreSQL** | `shared_buffers`, `wal_buffers`, `checkpoint_completion_target` pre-configured |
| **Health Checks** | All dependencies are health-checked before n8n starts |
| **Centralized Log Rotation** | Configurable via `.env` — `LOG_DRIVER`, `LOG_MAX_SIZE`, `LOG_MAX_FILE` |

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
                           │  n8n-init (One-Shot) ────────────────────────────── │
                           │    └── Seeds DB credentials                         │
                           │                                                      │
                           │  PostgreSQL (internal)  Redis (internal)            │
                           │  Qdrant (ports 6333/6334)                           │
                           └─────────────────────────────────────────────────────┘
```

### Services

| Container | Image | Role |
|---|---|---|
| `n8n` | Custom (`Dockerfile`) | Editor UI, REST API, task broker |
| `n8n-webhook` | Custom (`Dockerfile`) | Dedicated webhook processor |
| `n8n-worker` | Custom (`Dockerfile`) | Queue worker — **autoscaled** |
| `n8n-worker-runner` | Custom (`Dockerfile.runner`) | Task runner sidecar — **autoscaled 1:1 with worker** |
| `n8n-autoscaler` | Custom (`autoscaler/Dockerfile`) | Redis queue monitor + Docker Compose scaler |
| `redis-monitor` | Custom (`monitor/monitor.Dockerfile`) | Queue depth logger |
| `n8n-init` | `docker.n8n.io/n8nio/n8n:latest` | One-shot credential provisioner |
| `n8n-postgres` | `postgres:16-alpine` | Persistent data store |
| `n8n-redis` | `redis:7-alpine` | Queue broker |
| `qdrant` | `qdrant/qdrant:latest` | Vector database |
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

#### Database

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_TYPE` | ✅ | `postgresdb` | Database engine |
| `DB_POSTGRESDB_HOST` | ✅ | `postgres` | Service name (Docker network) |
| `DB_POSTGRESDB_DATABASE` | ✅ | `n8n` | Database name |
| `DB_POSTGRESDB_USER` | ✅ | `n8n_user` | Database user |
| `DB_POSTGRESDB_PASSWORD` | ✅ | — | Database password |

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

### MCP registry timeout on startup

```
Error fetching from Strapi API: timeout of 6000ms exceeded
```

Non-critical. Suppressed by `N8N_DIAGNOSTICS_ENABLED=false` — verify it's set.

---

### Redis connection check

```bash
# Verify Redis is responding (no auth — unauthenticated setup)
docker compose exec redis redis-cli ping

# Check queue length manually
docker compose exec redis redis-cli LLEN bull:jobs:wait
```

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
├── scripts/
│   └── provision.js                # One-shot credential provisioner (n8n-init)
├── n8n-data/                       # n8n user data (git-ignored)
├── backups/                        # Local backup output (git-ignored)
└── README.md                       # This file
```

---

## 🤝 Contributing

Pull requests are welcome. For significant changes, please open an issue first.

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-improvement`
3. Commit your changes: `git commit -m 'feat: add my improvement'`
4. Push and open a PR

---

## 📜 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

> This project is a **deployment configuration** for [n8n](https://n8n.io), which is [fair-code licensed](https://faircode.io). Review n8n's own license before deploying commercially.
>
> Based on [conor-is-my-name/n8n-autoscaling](https://github.com/conor-is-my-name/n8n-autoscaling) — adapted for this environment.
