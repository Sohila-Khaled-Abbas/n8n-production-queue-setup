<div align="center">

<img src="https://n8n.io/n8n-logo.png" alt="n8n Logo" width="120" />

# n8n Production Stack

**A production-grade, self-hosted n8n deployment with queue-mode scaling, PostgreSQL persistence, and an isolated Python/JavaScript code execution sidecar.**

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

---

## 📐 Architecture

```
                           ┌─────────────────────────────────────────┐
                           │              Docker Network              │
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

---

## ⚙️ Configuration

### Environment Variables

All variables live in `.env` (never committed). The table below documents every variable used across the stack.

#### Access & Identity

| Variable | Required | Example | Description |
|---|---|---|---|
| `N8N_EDITOR_BASE_URL` | ✅ | `https://n8n.example.com` | Public URL of the n8n editor |
| `WEBHOOK_URL` | ✅ | `https://n8n.example.com` | Base URL for inbound webhooks |
| `N8N_RELEASE_TYPE` | — | `stable` | Pin to `stable` or `next` |
| `NODE_ENV` | — | `production` | Node.js environment |

#### Task Runners

| Variable | Required | Description |
|---|---|---|
| `N8N_RUNNERS_AUTH_TOKEN` | ✅ | Shared secret between `n8n-main` and `n8n-python-runner`. Generate with `openssl rand -hex 32`. |

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

# Stop the stack (data is preserved in volumes)
docker compose down

# Destroy everything including volumes (⚠️ irreversible)
docker compose down -v

# Pull latest n8n image and redeploy
docker compose pull n8n n8n-worker
docker compose up -d n8n n8n-worker
```

---

## 🛠️ Troubleshooting

### Runner fails: "contains no task runners"

The launcher binary inside the container is reading a stale or differently-formatted config file.

**Fix:** The `docker-compose.yml` mounts `./n8n-task-runners.json` over `/etc/n8n-task-runners.json` at runtime, so the live file always wins. Ensure the runner container was started via Compose (not a raw `docker run`):

```bash
docker compose up -d n8n-python-runner
```

### Runner fails: "missing required value: N8N_RUNNERS_AUTH_TOKEN"

The `N8N_RUNNERS_AUTH_TOKEN` is not set in `.env`, or `.env` was not found.

```bash
# Verify the variable is loaded
docker compose run --rm n8n-python-runner env | grep N8N_RUNNERS_AUTH_TOKEN
```

### n8n-main never becomes healthy

Check that PostgreSQL and Redis are healthy first:

```bash
docker compose ps
docker compose logs postgres
docker compose logs redis
```

### Workflows not executing

In queue mode, at least one worker must be running. Verify:

```bash
docker compose ps n8n-worker
```

---

## 📁 Repository Structure

```
.
├── docker-compose.yml          # Full service orchestration
├── Dockerfile.runner           # Custom Python/JS runner image
├── n8n-task-runners.json       # Runner launcher configuration
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
