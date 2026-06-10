# Architecture — n8n Production Stack

This document expands on the high-level overview in the [README](../README.md) and explains every architectural decision in depth.

---

## Overview

The stack is composed of five Docker containers that communicate exclusively over an isolated Docker network (`n8n-network`). No container port is exposed to the host except `n8n-main:80`.

```
Browser / Webhook
       │
       ▼
┌──────────────────────────────────────────────┐
│              n8n-network (bridge)            │
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
│  └───────────────┬─────────────────────┘     │
│                  │ Task Runner Protocol      │
│                  ▼                           │
│  ┌─────────────────────────────────────┐     │
│  │  n8n-python-runner                 │     │
│  │  • n8n launcher binary             │     │
│  │  • JavaScript runner (:5681)       │     │
│  │  • Python runner     (:5682)       │     │
│  └─────────────────────────────────────┘     │
│                                              │
│  ┌──────────────┐   ┌────────────────────┐   │
│  │  PostgreSQL  │   │  Redis             │   │
│  │  :5432       │   │  :6379             │   │
│  │  (internal)  │   │  (internal)        │   │
│  └──────────────┘   └────────────────────┘   │
└──────────────────────────────────────────────┘
```

---

## Service Deep-Dives

### n8n-main

| Attribute | Value |
|---|---|
| Image | `docker.n8n.io/n8nio/n8n:latest` |
| Exposed port | `80` (maps to internal `5678`) |
| Role | Editor UI, REST API, task broker, webhook ingress |
| Queue mode | `EXECUTIONS_MODE=queue` |

`n8n-main` runs in **queue mode**, which means it never directly executes workflow nodes. Instead it enqueues execution jobs into Redis via the [Bull](https://github.com/OptimalBits/bull) library and delegates task runner operations to the internal broker endpoint (`:5679`).

**Health check:** HTTP GET `http://localhost:5678/healthz` — must return `200` before workers or runners start.

---

### n8n-worker

| Attribute | Value |
|---|---|
| Image | `docker.n8n.io/n8nio/n8n:latest` |
| Command | `n8n worker` |
| Scalable | Yes (`docker compose up -d --scale n8n-worker=N`) |

Workers are **stateless** — they share no disk with each other. All state lives in PostgreSQL (workflow definitions, credentials) and Redis (queue, locks). This makes horizontal scaling trivial.

> **Important:** Remove `container_name: n8n-worker-1` from `docker-compose.yml` before scaling to multiple replicas, as Docker Compose cannot assign a fixed name to multiple containers.

---

### n8n-python-runner

| Attribute | Value |
|---|---|
| Image | Custom — built from `Dockerfile.runner` |
| Base | `docker.n8n.io/n8nio/n8n-task-runners:latest` |
| Manages | JavaScript runner (port 5681) + Python runner (port 5682) |

This sidecar runs the **n8n launcher binary**, which spawns and supervises both a JavaScript and a Python sub-process. Each sub-process:
1. Connects back to the broker inside `n8n-main` over `:5679`.
2. Receives isolated task payloads (code + input items).
3. Executes the code in a sandboxed environment.
4. Streams results back to the broker.

The launcher reads its configuration from `/etc/n8n-task-runners.json` (mounted from the host). **No rebuild is needed** to change runner configuration — just edit the file and run `docker compose restart n8n-python-runner`.

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

---

### Redis

| Attribute | Value |
|---|---|
| Image | `redis:7-alpine` |
| Internal port | `6379` |
| Data volume | Named Docker volume `redis_data` |

Acts as the **Bull queue broker**. Each workflow execution becomes a Bull job on the `n8n` queue. Redis also handles distributed locks to prevent duplicate execution across worker replicas.

---

## Startup Ordering & Health Checks

Docker Compose `depends_on` with `condition: service_healthy` enforces strict ordering:

```
postgres  ──(healthy)──► n8n-main  ──(healthy)──► n8n-worker
redis     ──(healthy)──►                           n8n-python-runner
```

All services include `restart: unless-stopped` so the stack recovers automatically after host reboots or transient failures.

---

## Security Considerations

| Concern | Mitigation |
|---|---|
| Secrets in version control | `.env` is `.gitignore`d; `.env.example` contains only placeholders |
| Runner auth | `N8N_RUNNERS_AUTH_TOKEN` shared secret prevents rogue runner connections |
| Database exposure | PostgreSQL and Redis ports are not published to the host |
| Code execution sandbox | Task runners run as a separate process/container, isolated from the main n8n process |
| Encryption at rest | n8n encrypts credentials using `N8N_ENCRYPTION_KEY` (set in `.env`) |

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
