# Architecture — n8n Production Stack

This document expands on the high-level overview in the [README](../README.md) and explains every architectural decision in depth.

---

## Overview

The stack is composed of seven Docker containers that communicate exclusively over an isolated Docker bridge network (`n8n-net`). No container port is exposed to the host except `n8n-main:80`, `ollama:11434`, and `qdrant:6333` (for host-level access to AI services).

```
Browser / Webhook
       │
       ▼
┌──────────────────────────────────────────────┐
│              n8n-net (bridge)                │
│                                              │
│  ┌─────────────────────────────────────┐     │
│  │  n8n-main  (host port 80 → 5678)   │     │
│  │  ─────────────────────────────────  │     │
│  │  • Editor UI  (HTTP)               │     │
│  │  • REST API   (/api/v1/*)          │     │
│  │  • Webhook receiver                │     │
│  │  • Task Broker   (:5679 internal)  │     │
│  │  • Enqueues executions → Redis     │     │
│  └───────────────┬─────────────────────┘     │
│                  │ Bull queue                │
│                  ▼                           │
│  ┌─────────────────────────────────────┐     │
│  │  n8n-worker (scalable replicas)    │     │
│  │  • Dequeues & executes workflows   │     │
│  │  • Sends code tasks → broker       │     │
│  │  • N8N_RUNNERS_MODE=external       │     │
│  └───────────────┬─────────────────────┘     │
│                  │ Task Runner Protocol      │
│                  ▼                           │
│  ┌─────────────────────────────────────┐     │
│  │  n8n-python-runner                 │     │
│  │  • n8n launcher binary             │     │
│  │  • JavaScript runner (:5681)       │     │
│  │  • Python runner     (:5682)       │     │
│  │  • Health check      (:5680)       │     │
│  └─────────────────────────────────────┘     │
│                                              │
│  ┌──────────────┐   ┌──────────────┐         │
│  │  PostgreSQL  │   │  Redis       │         │
│  │  :5432       │   │  :6379       │         │
│  │  (internal)  │   │  (internal)  │         │
│  └──────────────┘   └──────────────┘         │
│                                              │
│                     ┌──────────────┐         │
│                     │  Qdrant      │         │
│                     │  :6333       │         │
│                     │  (Vector DB) │         │
│                     └──────────────┘         │
└──────────────────────────────────────────────┘
```

---

## Service Deep-Dives

### n8n-main

| Attribute | Value |
|---|---|
| Image | `docker.n8n.io/n8nio/n8n:2.25.6` |
| Exposed port | `80` (maps to internal `5678`) |
| Role | Editor UI, REST API, task broker, webhook ingress |
| Queue mode | `EXECUTIONS_MODE=queue` |

`n8n-main` runs in **queue mode**, which means it never directly executes workflow nodes. Instead it enqueues execution jobs into Redis via the [Bull](https://github.com/OptimalBits/bull) library and delegates task runner operations to the internal broker endpoint (`:5679`).

Manual executions are offloaded to workers via `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS=true` — this is the recommended setting in n8n v2.25+ to avoid overloading the main process.

**Diagnostics suppressed:** `N8N_DIAGNOSTICS_ENABLED=false` prevents n8n from making outbound requests to `api.n8n.io` on startup (MCP registry and version-check calls), eliminating the 6-second timeout error that appears in environments with restricted outbound access.

**Health check:** HTTP GET `http://localhost:5678/healthz` — must return `200` before workers or runners start.

---

### n8n-worker

| Attribute | Value |
|---|---|
| Image | `docker.n8n.io/n8nio/n8n:2.25.6` |
| Command | `n8n worker` |
| Scalable | Yes (`docker compose up -d --scale n8n-worker=N`) |
| Runner mode | `N8N_RUNNERS_MODE=external` |

Workers are **stateless** — they share no disk with each other. All state lives in PostgreSQL (workflow definitions, credentials) and Redis (queue, locks). This makes horizontal scaling trivial.

The worker is explicitly configured with `N8N_RUNNERS_MODE=external` and pointed at the main instance's task broker (`N8N_RUNNERS_TASK_BROKER_URI=http://n8n:5679`). Without this, the worker tries to start a Python runner internally and fails because Python is not installed in the base n8n image.

> **Important:** Remove `container_name: n8n-worker-1` from `docker-compose.yml` before scaling to multiple replicas, as Docker Compose cannot assign a fixed name to multiple containers.

---

### n8n-python-runner

| Attribute | Value |
|---|---|
| Image | Custom — built from `Dockerfile.runner` |
| Base | `n8nio/runners:latest` |
| Manages | JavaScript runner (port 5681) + Python runner (port 5682) |
| Health check | `GET http://localhost:5680/healthz` |

This sidecar runs the **n8n launcher binary**, which spawns and supervises both a JavaScript and a Python sub-process. Each sub-process:
1. Connects back to the broker inside `n8n-main` over `:5679`.
2. Receives isolated task payloads (code + input items).
3. Executes the code in a sandboxed environment.
4. Streams results back to the broker.

The launcher reads its configuration from `/etc/n8n-task-runners.json` (mounted from the host). **No rebuild is needed** to change runner configuration — just edit the file and run `docker compose restart n8n-python-runner`.

`N8N_RUNNERS_AUTO_SHUTDOWN_TIMEOUT=0` keeps the runner alive indefinitely instead of shutting down after an idle period. This prevents the WebSocket `i/o timeout` handshake failure that occurs when the runner disconnects and the broker tries to reconnect after a long idle period.

**Pre-installed Python packages:**

| Package | Reason |
|---|---|
| `pandas` | DataFrame manipulation, CSV/Excel/JSON |
| `numpy` | Vectorised numeric operations |
| `pyarrow` | Parquet & columnar I/O |
| `requests` | Outbound HTTP calls from Python code nodes |

---

### PostgreSQL

| Attribute | Value |
|---|---|
| Image | `postgres:16-alpine` |
| Internal port | `5432` |
| Data volume | Named Docker volume `postgres_data` |

Stores all n8n application data: workflow definitions, credentials (encrypted at rest by n8n), execution history, and user accounts. The database is **never exposed** to the host network.

#### Production Tuning

The following flags are applied via the `command:` override in `docker-compose.yml`:

| Parameter | Value | Effect |
|---|---|---|
| `shared_buffers` | `256MB` | Main read cache; reduces disk hits |
| `effective_cache_size` | `768MB` | Planner hint for index preference |
| `work_mem` | `16MB` | Per-sort/hash memory; speeds complex queries |
| `maintenance_work_mem` | `128MB` | Speeds up VACUUM, CREATE INDEX |
| `checkpoint_completion_target` | `0.9` | Spreads checkpoint I/O over 90% of the interval — eliminates the 18–21 second checkpoint spikes seen in untuned deployments |
| `wal_buffers` | `16MB` | Reduces WAL write round-trips |
| `max_wal_size` | `2GB` | Allows more WAL before triggering an early checkpoint |
| `min_wal_size` | `512MB` | Prevents thrashing on low-traffic instances |
| `synchronous_commit` | `local` | Writes WAL to the OS page cache before returning from COMMIT, but does **not** wait for the physical disk fsync. Eliminates multi-second COMMIT latency caused by Docker Desktop's virtualised I/O layer on Windows while still protecting against process crashes |
| `log_min_duration_statement` | `2000ms` | Logs queries slower than 2 seconds for visibility |

The healthcheck includes `start_period: 30s` so Compose does not declare Postgres unhealthy during the WAL recovery phase that follows an unclean shutdown.

---

### Redis

| Attribute | Value |
|---|---|
| Image | `redis:7-alpine` |
| Internal port | `6379` |
| Data volume | Named Docker volume `redis_data` |
| Config file | `./redis.conf` (mounted read-only) |

Acts as the **Bull queue broker**. Each workflow execution becomes a Bull job on the `n8n` queue. Redis also handles distributed locks to prevent duplicate execution across worker replicas.

#### Production Configuration (`redis.conf`)

Redis is started with an explicit configuration file instead of the default settings. Key changes from the default:

| Setting | Default → Production | Reason |
|---|---|---|
| Config file | None | `Warning: no config file specified` is now gone |
| Persistence | RDB only | AOF (`appendonly yes`) is primary; RDB kept as backup |
| `appendfsync` | — | `everysec` — durable, low overhead |
| `maxmemory` | Unlimited | `256mb` — prevents OOM from queue growth |
| `maxmemory-policy` | `noeviction` | `allkeys-lru` — graceful eviction |
| Slow log | Disabled | Enabled at 10ms threshold for visibility |

---



### Qdrant (Vector Database)

| Attribute | Value |
|---|---|
| Image | `qdrant/qdrant:latest` |
| Internal ports | `6333` (REST), `6334` (gRPC) |
| Data volume | Named Docker volume `qdrant_storage` |

Qdrant is a high-performance vector database used for Retrieval-Augmented Generation (RAG) and embedding storage. n8n vector store nodes interact with it over `http://qdrant:6333`. It is highly recommended to pair this with an OpenRouter API embedding model to avoid overloading the local GPU.

---

## Startup Ordering & Health Checks

Docker Compose `depends_on` with `condition: service_healthy` enforces strict ordering:

```
postgres  ──(healthy, start_period=30s)──► n8n-main  ──(started)──► n8n-worker
redis     ──(healthy, start_period=10s)──►                           n8n-python-runner
```

All services include `restart: unless-stopped` so the stack recovers automatically after host reboots or transient failures.

### Shutdown Grace Periods

Docker's default stop timeout is **10 seconds** — too short for PostgreSQL to finish an in-progress checkpoint. Without explicit grace periods, every `docker compose down` or host reboot causes an unclean shutdown, which forces WAL recovery on the next start.

| Service | `stop_grace_period` | Reason |
|---|---|---|
| `postgres` | `60s` | Completes the shutdown checkpoint + WAL flush before SIGKILL |
| `redis` | `20s` | Flushes the AOF buffer to disk |
| `n8n` | `30s` | Finishes in-flight HTTP requests |
| `n8n-worker` | `30s` | Completes any currently-executing workflow node |

---

## Network Isolation

All services are attached to the named bridge network `n8n-net` defined in `docker-compose.yml`. Benefits:

- Services resolve each other by container name DNS (e.g., `postgres`, `redis`, `n8n`)
- The network is isolated from other containers running on the Docker host
- Only `n8n-main:80` is published externally

---

## Security Considerations

| Concern | Mitigation |
|---|---|
| Secrets in version control | `.env` is `.gitignore`d; `.env.example` contains only placeholders |
| Runner auth | `N8N_RUNNERS_AUTH_TOKEN` shared secret prevents rogue runner connections |
| Database exposure | PostgreSQL and Redis ports are not published to the host |
| Code execution sandbox | Task runners run as a separate process/container, isolated from the main n8n process |
| Encryption at rest | n8n encrypts credentials using `N8N_ENCRYPTION_KEY` (set in `.env`) |
| Image stability | All images pinned to exact versions — no silent breaking upgrades |

---

## Data Flow: Workflow Execution

```
1. User triggers workflow  →  n8n-main receives trigger
2. n8n-main enqueues job   →  Redis (Bull queue)
3. n8n-worker dequeues job →  executes non-code nodes locally
4. Worker hits Code node   →  sends task to n8n-main broker (:5679)
5. Broker dispatches task  →  n8n-python-runner (JS or Python runner)
6. Runner executes code    →  streams result back to broker
7. Broker returns result   →  worker continues workflow
8. Worker writes result    →  PostgreSQL (execution history)
```
