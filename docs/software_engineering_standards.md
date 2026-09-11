# Repository Software Engineering Standards

This document establishes the architectural, coding, operational, and security standards for the **n8n Production Autoscaling Stack**. All developers and operators must adhere to these guidelines to ensure reliability, scalability, and security.

---

## 📂 Table of Contents
1. [System Architecture & Decoupling](#1-system-architecture--decoupling)
2. [Configuration & Secrets Management](#2-configuration--secrets-management)
3. [Code Quality & Linting Standards](#3-code-quality--linting-standards)
4. [Logging, Diagnostics, and Observability](#4-logging-diagnostics-and-observability)
5. [Database Hygiene & Storage Operations](#5-database-hygiene--storage-operations)
6. [Resiliency, Error Handling, and Fallbacks](#6-resiliency-error-handling-and-fallbacks)

---

## 1. System Architecture & Decoupling

The stack is designed with a **decoupled, multi-service architecture** to isolate duties and eliminate single points of failure.

```
                  ┌──────────────────────┐
                  │      n8n-main        │ (Editor, API, Scheduler)
                  └──────────┬───────────┘
                             │ (Enqueue)
                             ▼
  ┌──────────────┐     ┌───────────┐
  │ n8n-webhook  ├────►│   Redis   │ (Queue Broker)
  └──────────────┘     └─────┬─────┘
                             │ (Dequeue)
                             ▼
                  ┌──────────────────────┐
                  │      n8n-worker      │ (Autoscaled Queue Worker)
                  └──────────┬───────────┘
                             │ (Code Offload)
                             ▼
                  ┌──────────────────────┐
                  │  n8n-worker-runner   │ (Autoscaled Sidecar Runner)
                  └──────────────────────┘
```

### Architectural Rules:
- **Independent Webhook Processing (`n8n-webhook`)**: Inbound webhooks must be routed through the dedicated `n8n-webhook` container. This ensures spikes in external webhook traffic do not slow down the Editor UI or block backend workers.
- **Worker & Runner 1:1 Ratio**: For every `n8n-worker` instance scaled, there must be exactly one `n8n-worker-runner` sidecar instance. The autoscaler handles this atomicity by scaling both services together using a single Docker Compose execution.
- **Task Delegation**: Custom code nodes (JS/Python) must be offloaded from workers to runners. Do not execute heavy libraries directly on the worker's node process.

---

## 2. Configuration & Secrets Management

Security is critical in production deployment pipelines. Storing credentials or encryption keys in source control is strictly forbidden.

### Standards:
- **Environment Separation**: All configuration parameters must live in `.env`. The `.env.example` file serves as the single source of truth for configuration variables.
- **Key Generation**:
  - `N8N_ENCRYPTION_KEY`: Generate a 24-character base64 string once:
    ```bash
    openssl rand -base64 24
    ```
    *Never change this key after deployment; doing so corrupts existing encrypted credentials in the database.*
  - `N8N_RUNNERS_AUTH_TOKEN`: Generate a secure 32-character hex token:
    ```bash
    openssl rand -hex 32
    ```
- **File Safety**: Ensure `.env` is never removed from `.gitignore`. 

---

## 3. Code Quality & Linting Standards

Consistency in code formatting increases readability and lowers code review overhead.

### Python Guidelines:
- **Linter & Formatter**: We use **Ruff** (configured via [pyproject.toml](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/pyproject.toml)) for linting and code formatting.
- **Rules Enforced**:
  - `F` (Pyflakes): Detects syntax errors, unused variables, and imports.
  - `E` & `W` (pycodestyle): Enforces PEP 8 style formatting.
  - `I` (isort): Sorts and organizes imports.
  - `UP` (pyupgrade): Upgrades syntax to Python 3.12+ standards.
- **CLI Commands**:
  - Format code: `ruff format .`
  - Lint code: `ruff check . --fix`

### Dockerfile Guidelines:
- Use **Hadolint** to check Dockerfile health.
- Avoid pinning `:latest` tags for production base images (use specific versions, e.g., `postgres:16-alpine`, `n8n:2.28.6`).
- Minimize Docker layers by chaining commands in a single `RUN` instruction and cleaning up package manager caches (`rm -rf /var/cache/apk/*`, `uv cache clean`).

---

## 4. Logging, Diagnostics, and Observability

A high-load environment requires structured logging and lightweight diagnostic methods.

### Standards:
- **Docker Log Rotation**: Large log files can fill up host disk drives. Always configure log rotation limits inside `docker-compose.yml`:
  ```yaml
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
  ```
- **High-Load Diagnostics (Avoid UI Crashes)**:
  - If a workflow execution fails with a massive JSON payload (e.g. processing large files or large scraping arrays), loading that execution in the n8n Editor UI can crash browser tabs.
  - **Best Practice**: Use the database diagnostic SQL scripts inside the `scripts/` directory to query execution logs:
    - Run [search_errors.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/search_errors.sql) or [get_error.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/get_error.sql) to retrieve stack traces directly from the database without fetching them in the web UI.

---

## 5. Database Hygiene & Storage Operations

Under heavy production loads, n8n's database tables can experience database bloat, causing query slowdowns and high disk usage.

### Database Standards:
- **Automated Retention**: Always maintain the database execution history pruning logic. Storing logs for every execution indefinitely is an anti-pattern.
- **Cleanup Strategy**: Run the [cleanup.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/cleanup.sql) script weekly to:
  1. Prune all execution history and logs older than 3 days.
  2. Mark stale runs (from crashed/restarted containers) as `crashed`.
  3. Reclaim unused storage space using `VACUUM FULL`.
- **Git Safety**: Never commit `.sql` files or `.dump` backups to Git. Keep database backups on secure, isolated cloud servers or local drives.

---

## 6. Resiliency, Error Handling, and Fallbacks

Our services must be designed to withstand downstream network failures or resource limitations.

### Guidelines:
- **Binary Storage (`filesystem` mode)**:
  - For production workloads, set `N8N_DEFAULT_BINARY_DATA_MODE=filesystem` in `.env`.
  - This streams large binary files (PDFs, images, ZIPs) straight to disk instead of holding them in RAM, preventing worker containers from crashing due to Out-Of-Memory (OOM) errors.
- **Node-level Retries**:
  - Any node making external HTTP requests or interacting with external APIs (like Slack, Google Drive, or Pinecone) should have **Retry on Fail** configured (typically `3` attempts with `3000ms` wait intervals) to protect against transient network drops (e.g., `ECONNRESET`).
- **Autoscaler Resilience**:
  - The autoscaler script must handle Docker API or Redis connection exceptions gracefully. If Docker or Redis is temporarily unresponsive, the autoscaler must log the warning, sleep, and retry instead of exiting the process.
- **Broker Crash Resilience & Auto-Recovery**:
  - The Redis queue broker must have `aof-load-truncated yes` and `aof-use-rdb-preamble yes` enabled in `redis.conf`. This guarantees that partial writes caused by abrupt container termination or host reboots do not block Redis from booting.
- **Orphan Execution Healing**:
  - Worker crashes can leave database records in `running` or `waiting` state indefinitely. Database maintenance scripts must dynamically detect and mark orphaned executions older than 24 hours as `crashed`.

---

## 7. Distributed Workflow Idempotency & Deduplication

In a distributed queue environment, external webhook triggers (e.g. Stripe, Shopify, Telegram) operate on **at-least-once delivery** semantics. Network retries can cause identical webhook events to arrive multiple times.

### Architectural Standards:
- **Idempotency Keys**: All transactional workflows (e.g. order creation, payments, inventory mutations) must generate or extract an idempotency key from inbound request headers (e.g. `X-Idempotency-Key` or `event.id`).
- **Atomic Deduplication Check (Redis `SETNX`)**:
  - Before performing downstream mutations, workflows must query Redis or a deduplication table:
    ```javascript
    // Pseudocode inside Code node / Function node
    const key = `idempotency:${event.id}`;
    const acquired = await redis.set(key, "PROCESSING", "NX", "EX", 3600);
    if (!acquired) {
      return [{ json: { status: "duplicate_ignored", eventId: event.id } }];
    }
    ```
- **Terminal State Validation**: Always verify whether an entity already exists in PostgreSQL/CRM before issuing an `INSERT` or sending an email/message notification.

---

## 8. Dead Letter Queues (DLQ) & Circuit Breakers

When unexpected payloads cause unhandled errors, repeatedly failing jobs must not block worker queues or exhaust memory.

### Standards:
- **Error Trigger Handlers**: Every production workflow must configure a dedicated **Error Trigger** workflow (`Error Workflow.json`).
- **Poison Pill Isolation (DLQ)**:
  - If a job fails after 3 automatic retries, the Error Trigger must route the full execution payload, error stack trace, and timestamp to a dedicated Dead Letter Queue in Redis (`bull:dlq:jobs`) or PostgreSQL table.
  - Workers must immediately acknowledge and clear the poisoned task from the primary queue to keep the pipeline moving.
- **Circuit Breaker for External APIs**:
  - If an upstream API (e.g. OpenAI, Notion, Google Sheets) returns consecutive `5xx` or `429 Too Many Requests` errors exceeding 5 failures in 1 minute, the workflow should trip a circuit breaker flag in Redis to reject subsequent requests fast rather than waiting for timeouts.

---

## 9. CI/CD Quality Gates & Automated Verification

Every commit and pull request must satisfy rigorous software engineering checks prior to deployment.

### Quality Gate Hierarchy:
1. **Python Quality Gate (`ruff check .` & `ruff format --check .`)**:
   - Zero syntax errors, zero unused imports, zero unused local variables (`scaled`), and PEP 8 compliant formatting.
   - Enforced via GitHub Actions (`.github/workflows/ci.yml`).
2. **Container Security & Linting (`hadolint`)**:
   - Validates multi-stage Dockerfiles against Docker best practices (non-root users, package manager cache cleanup, pinned image tags).
3. **Automated Secret Scanning**:
   - Greps workflow JSONs and scripts for hardcoded API keys (`sk-`, `AIza`, passwords).
4. **Continuous Documentation Deployment (`peaceiris/actions-gh-pages`)**:
   - Changes to `docs/**`, `workflows/**`, or `scripts/generate_docs_data.py` trigger automated compilation and deployment to the `gh-pages` branch.
