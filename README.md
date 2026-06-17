<div align="center">

<img src="https://n8n.io/n8n-logo.png" alt="n8n Logo" width="120" />

# n8n Production AI Stack

**A production-grade, self-hosted n8n deployment optimized for Data Engineering, featuring BigQuery and Airflow orchestration, lightweight AI via OpenRouter APIs (with Qdrant for RAG), queue-mode scaling, PostgreSQL persistence, and an isolated Python/JavaScript code execution sidecar.**

[![n8n Version](https://img.shields.io/badge/n8n-latest-FF6D5A?logo=n8n&logoColor=white)](https://hub.docker.com/r/n8nio/n8n)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://hub.docker.com/_/postgres)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://hub.docker.com/_/redis)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-v2-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Configuration](#-configuration) · [Scaling](#-scaling) · [Troubleshooting](#-troubleshooting)

</div>

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Queue-Mode Execution** | Workflows execute via Bull/Redis queues — no single point of failure |
| **PostgreSQL Backend** | Durable workflow, credential, and execution history storage |
| **External Task Runners** | Sandboxed Python + JavaScript Code node execution via a dedicated sidecar |
| **Horizontal Worker Scaling** | Add workers with a single `--scale` flag |
| **Data-Engineering Ready** | `pandas`, `numpy`, `pyarrow`, `requests` pre-installed in the Python runner |
| **Runtime Config Hot-Swap** | Update runner configuration without rebuilding the Docker image |
| **Health Checks** | All dependencies are health-checked before n8n starts |
| **Production-Tuned PostgreSQL** | `shared_buffers`, `wal_buffers`, `checkpoint_completion_target` pre-configured |
| **AOF-Persistent Redis** | Redis uses append-only file persistence + memory cap — no data loss on restart |
| **Pinned Image Versions** | All images are pinned to exact versions — no surprise upgrades |
| **Lightweight AI via APIs** | Use OpenRouter via n8n's AI nodes for advanced intelligence without taxing your local 4GB GPU |
| **ETL & Data Engineering** | Pre-installed PyArrow and pandas for local data validation before pushing to BigQuery or triggering Airflow DAGs |
| **Vector Database** | Qdrant included for high-performance RAG and embeddings |

---

## 📐 Architecture

```
                           ┌─────────────────────────────────────────┐
                           │         n8n-net (bridge network)        │
                           │                                          │
  Browser / Webhook ──────►│  n8n-main (port 80)                     │
                           │    ├── REST API & Editor UI              │
                           │    ├── Task Broker (port 5679, internal) │
                           │    └── Enqueues executions → Redis       │
                           │                                          │
                           │  n8n-worker ──────────────────────────── │
                           │    └── Dequeues & runs workflows         │
                           │                                          │
                           │  n8n-python-runner ───────────────────── │
                           │    ├── JS runner  (health: 5681)         │
                           │    └── Python runner (health: 5682)      │
                           │         Connects to broker at :5679      │
                           │                                          │
                           │  PostgreSQL (port 5432, internal)        │
                           │  Redis      (port 6379, internal)        │
                           │  Qdrant     (port 6333, vector DB)       │
                           └─────────────────────────────────────────┘
```

### Services

| Container | Image | Role |
|---|---|---|
| `n8n-main` | `docker.n8n.io/n8nio/n8n:latest` | Editor UI, REST API, task broker |
| `n8n-worker-1` | `docker.n8n.io/n8nio/n8n:latest` | Queue worker (scalable) |
| `n8n-python-runner` | Custom (`Dockerfile.runner`) | Sandboxed code execution sidecar |
| `n8n-postgres` | `postgres:16-alpine` | Persistent data store |
| `n8n-redis` | `redis:7-alpine` | Queue broker & session cache |
| `qdrant` | `qdrant/qdrant:latest` | Vector Database for embeddings |

---

## ⚡ Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 4.x (Windows/macOS) or Docker Engine ≥ 24 + Docker Compose plugin (Linux)
- Git

### 1 · Clone

```bash
git clone https://github.com/YOUR_USERNAME/n8n-production-stack.git
cd n8n-production-stack
```

### 2 · Configure

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```dotenv
N8N_EDITOR_BASE_URL=https://your-public-url.example.com
WEBHOOK_URL=https://your-public-url.example.com
N8N_RUNNERS_AUTH_TOKEN=<output of: openssl rand -hex 32>
DB_POSTGRESDB_PASSWORD=<strong password>
```

> **Note on `N8N_DATA_DIR`**  
> By default the stack writes n8n's user data to `./n8n-data/` (created automatically).  
> To use a different host path, set `N8N_DATA_DIR=/absolute/path/to/data` in `.env`.

### 3 · Build & Launch

```bash
# Build the custom runner image (only needed on first run or after changes)
docker compose build n8n-python-runner

# Start the full stack in the background
docker compose up -d
```

### 4 · Open n8n

Navigate to `http://localhost` (or your public URL). Create your owner account on first launch.

> **Data Engineering Note:** This stack is optimized for low-VRAM devices (like 4GB GPUs). Instead of running local LLMs, configure an **OpenRouter** credential in the n8n UI to power the Advanced AI nodes, keeping your local resources free for data processing.

---

## ⚙️ Configuration

### Environment Variables

All variables live in `.env` (never committed). The table below documents every variable used across the stack.

#### Access & Identity

| Variable | Required | Example | Description |
|---|---|---|---|
| `N8N_EDITOR_BASE_URL` | ✅ | `https://n8n.example.com` | Public URL of the n8n editor |
| `WEBHOOK_URL` | ✅ | `https://n8n.example.com` | Base URL for inbound webhooks |
| `N8N_PROXY_HOPS` | — | `1` | Number of reverse proxies (e.g., ngrok, nginx) in front of n8n. Fixes `X-Forwarded-For` rate-limit errors. |
| `N8N_RELEASE_TYPE` | — | `stable` | Pin to `stable` or `next` |
| `NODE_ENV` | — | `production` | Node.js environment |
| `N8N_LOG_LEVEL` | — | `info` | Log verbosity: `error`, `warn`, `info`, `debug` |
| `N8N_DIAGNOSTICS_ENABLED` | — | `false` | Disable telemetry & external API calls on startup |
| `N8N_VERSION_NOTIFICATIONS_ENABLED` | — | `false` | Suppress version-check requests to `api.n8n.io` |

#### Task Runners

| Variable | Required | Description |
|---|---|---|
| `N8N_RUNNERS_AUTH_TOKEN` | ✅ | Shared secret between `n8n-main` and `n8n-python-runner`. Generate with `openssl rand -hex 32`. |

> **Removed variable:** `N8N_RUNNERS_ENABLED` is **no longer needed** in n8n v2.25+ and must be removed from `.env`. Keeping it will produce a deprecation warning on every boot.

#### Database

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_TYPE` | ✅ | `postgresdb` | Database engine |
| `DB_POSTGRESDB_HOST` | ✅ | `postgres` | Service name (Docker network) |
| `DB_POSTGRESDB_PORT` | — | `5432` | Port |
| `DB_POSTGRESDB_DATABASE` | ✅ | `n8n` | Database name |
| `DB_POSTGRESDB_USER` | ✅ | `n8n_user` | Database user |
| `DB_POSTGRESDB_PASSWORD` | ✅ | — | Database password |

#### Storage

| Variable | Default | Description |
|---|---|---| 
| `N8N_DATA_DIR` | `./n8n-data` | Host path for n8n user data (workflows, credentials, binary files) |
| `N8N_DEFAULT_BINARY_DATA_MODE` | `filesystem` | Where binary execution data is stored (`filesystem` or `s3`) |



### Redis Configuration (`redis.conf`)

Redis is started with a dedicated `redis.conf` file (mounted read-only into the container). This replaces the noisy default configuration. Key settings:

| Setting | Value | Reason |
|---|---|---|
| `appendonly yes` | AOF persistence | Durable writes; survives container crashes |
| `appendfsync everysec` | 1-second fsync | Balance between durability and performance |
| `maxmemory 256mb` | Memory cap | Prevents OOM from unbounded queue growth |
| `maxmemory-policy allkeys-lru` | LRU eviction | Evicts oldest data when cap is reached |
| `save 3600 1` | Hourly RDB snapshot | Safety net backup |

To tune memory for your host, edit `redis.conf` and change `maxmemory`.  
No container rebuild is needed — just restart Redis:

```bash
docker compose restart redis
```

### PostgreSQL Tuning

The following flags are passed directly to the `postgres` process in `docker-compose.yml`:

| Flag | Value | Reason |
|---|---|---|
| `shared_buffers` | `256MB` | Main read cache — reduces disk I/O |
| `effective_cache_size` | `768MB` | Planner hint for index vs. seq scan |
| `checkpoint_completion_target` | `0.9` | Spreads I/O across 90% of checkpoint interval (reduces I/O spikes) |
| `wal_buffers` | `16MB` | Reduces WAL write latency |
| `max_wal_size` | `2GB` | Allows more WAL before forcing a checkpoint |
| `log_min_duration_statement` | `1000ms` | Logs queries slower than 1 second |

### Task Runner Config (`n8n-task-runners.json`)

This file configures the launcher sidecar that manages JavaScript and Python runner processes. It is mounted read-only into the `n8n-python-runner` container at `/etc/n8n-task-runners.json`.

**You do not need to rebuild the Docker image to change this file** — just edit it and restart the container:

```bash
docker compose restart n8n-python-runner
```

Key settings:

| Field | Description |
|---|---|
| `runner-type` | `javascript` or `python` |
| `health-check-server-port` | Port the launcher exposes for health checks |
| `allowed-env` | Allowlist of env vars forwarded to the runner subprocess |
| `env-overrides` | Env vars injected into the runner subprocess |
| `NODE_FUNCTION_ALLOW_EXTERNAL` | Comma-separated npm packages allowed in JS Code nodes |
| `N8N_RUNNERS_EXTERNAL_ALLOW` | Python packages allowed in Python Code nodes (`*` = all installed) |

---

## 🛠 Data Engineering & AI Workflows

This architecture is tailored for Data Engineers looking to orchestrate ETL/ELT pipelines while integrating AI capabilities:

1. **Lightweight AI with OpenRouter:** Since running heavy models on a 4GB GPU can cause Out-Of-Memory (OOM) crashes, we recommend using **OpenRouter** in n8n's Advanced AI nodes. This gives you access to GPT-4, Claude 3.5 Sonnet, and Llama 3 via API without any local hardware tax.
2. **BigQuery ETL:** Use n8n's native Google BigQuery nodes to load, query, and transform data.
3. **Airflow Orchestration:** Use n8n to connect disparate webhooks and APIs to your **Apache Airflow** environment. You can trigger Airflow DAGs via the HTTP Request node (calling the Airflow REST API) as part of a larger n8n-orchestrated pipeline.
4. **Vector Search (Qdrant):** Qdrant is included for Retrieval-Augmented Generation (RAG). You can embed your raw data using an API embedding model and store it in Qdrant for semantic search.

---

## 🐍 Python Code Nodes

The `n8n-python-runner` image extends `n8nio/runners:latest` with the following pre-installed libraries:

| Library | Purpose |
|---|---|
| `pandas` | DataFrames, CSV/Excel/JSON processing |
| `numpy` | Numerical computing |
| `pyarrow` | Parquet & columnar data I/O |
| `requests` | HTTP client |

### Adding More Libraries

1. Edit `Dockerfile.runner` and append your package(s):
   ```dockerfile
   RUN cd /opt/runners/task-runner-python \
       && uv pip install --no-cache-dir \
           pandas numpy pyarrow requests \
           scikit-learn   # ← add here
   ```
2. Rebuild and restart:
   ```bash
   docker compose build n8n-python-runner
   docker compose up -d n8n-python-runner
   ```

---

## 📈 Scaling

### Horizontal Worker Scaling

Workers are stateless — spin up as many as your host allows:

```bash
# Run 3 concurrent workers
docker compose up -d --scale n8n-worker=3
```

> **Tip:** Remove the `container_name: n8n-worker-1` line in `docker-compose.yml` before scaling, as Docker Compose cannot assign the same name to multiple containers.

### Multiple Python Runners

The launcher sidecar already manages both JS and Python runners in a single container. To scale code execution, simply run additional `n8n-python-runner` replicas (after removing `container_name`):

```bash
docker compose up -d --scale n8n-python-runner=2
```

---

## 🔄 Common Operations

```bash
# View live logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f n8n-python-runner

# Restart a single service
docker compose restart n8n

# Update n8n to a new pinned version
# 1. Edit docker-compose.yml: change both n8n image tags to the new version
# 2. Pull and redeploy:
docker compose pull n8n n8n-worker
docker compose up -d n8n n8n-worker

# Stop the stack (data is preserved in volumes)
docker compose down

# Destroy everything including volumes (⚠️ irreversible)
docker compose down -v
```

---

## 🛠️ Troubleshooting

### Deprecation warnings on startup

```
N8N_RUNNERS_ENABLED -> Remove this environment variable
OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS -> ...
```

**Fix:** Ensure `N8N_RUNNERS_ENABLED` is **absent** from `.env`. `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS=true` is already set in `docker-compose.yml` — do not set it to `false` in `.env`.

---

### MCP registry timeout on startup

```
Error fetching from Strapi API (https://api.n8n.io/api/mcp-servers): timeout of 6000ms exceeded
```

This is a non-critical informational fetch. It is suppressed in this stack by `N8N_DIAGNOSTICS_ENABLED=false`. If you see it again, verify that variable is set in `docker-compose.yml`.

---

### Runner fails: "contains no task runners"

The launcher binary inside the container is reading a stale or differently-formatted config file.

**Fix:** The `docker-compose.yml` mounts `./n8n-task-runners.json` over `/etc/n8n-task-runners.json` at runtime, so the live file always wins. Ensure the runner container was started via Compose (not a raw `docker run`):

```bash
docker compose up -d n8n-python-runner
```

---

### Runner fails: "missing required value: N8N_RUNNERS_AUTH_TOKEN"

The `N8N_RUNNERS_AUTH_TOKEN` is not set in `.env`, or `.env` was not found.

```bash
# Verify the variable is loaded
docker compose run --rm n8n-python-runner env | grep N8N_RUNNERS_AUTH_TOKEN
```

---

### n8n-main never becomes healthy

Check that PostgreSQL and Redis are healthy first:

```bash
docker compose ps
docker compose logs postgres
docker compose logs redis
```

PostgreSQL logs `database system was not properly shut down` on first start after an unclean shutdown — this is normal. Wait for `database system is ready to accept connections` before investigating further. The `start_period: 30s` on the healthcheck gives it time to complete WAL recovery.

---

### Workflows not executing

In queue mode, at least one worker must be running. Verify:

```bash
docker compose ps n8n-worker
```

---

### Node does not have any credentials set

This is a runtime workflow warning — the node in your workflow has no API credentials attached. Fix it in the n8n UI under the node's **Credentials** dropdown, not in the Docker configuration.

---

## 📁 Repository Structure

```
.
├── docker-compose.yml          # Full service orchestration
├── Dockerfile.runner           # Custom Python/JS runner image
├── n8n-task-runners.json       # Runner launcher configuration
├── redis.conf                  # Production Redis configuration
├── .env.example                # Environment variable template
├── .gitignore                  # Excludes secrets and runtime data
├── docs/
│   ├── architecture.md         # Detailed architecture notes
│   └── troubleshooting.md      # Extended troubleshooting guide
└── README.md                   # This file
```

---

## 🤝 Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss your proposal.

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-improvement`
3. Commit your changes: `git commit -m 'feat: add my improvement'`
4. Push and open a PR

---

## 📜 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

> This project is a **deployment configuration** for [n8n](https://n8n.io), which is [fair-code licensed](https://faircode.io). Review n8n's own license before deploying commercially.
