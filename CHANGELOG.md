# 📜 Changelog

All notable changes to the **n8n Production Autoscaling Stack** will be documented in this file. This project follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [1.4.1] - 2026-09-11

### 🛡️ Fixed & Hardened (CI/CD Quality Gates)
- **CI Python Linting & Formatting**:
  - Reconfigured `pyproject.toml` moving `exclude` to the top-level `[tool.ruff]` section to properly filter generated downstream showcase repositories (`published_repos/`) and ephemeral caches.
  - Added `E501` to `[tool.ruff.lint].ignore` in alignment with official Ruff guidelines when using `ruff format`.
  - Removed unused variables (`scaled`), eliminated extraneous f-string prefixes, resolved trailing whitespace issues, and formatted the entire codebase with `ruff format`.
  - Both `ruff check .` and `ruff format --check .` now pass cleanly in CI with 0 errors.
- **GitHub Pages Deployment Conflict Resolution**:
  - Diagnosed and resolved the 5-second failure on `Deploy Docs to GitHub Pages` caused by a branch configuration mismatch in `actions/deploy-pages@v4` and a race condition on concurrency group `"pages"`.
  - Consolidated deployment logic into `.github/workflows/deploy.yml` using `peaceiris/actions-gh-pages@v4` targeting the active `gh-pages` branch.
  - Added smart path triggers (`docs/**`, `workflows/**`, `scripts/generate_docs_data.py`, and `.github/workflows/deploy.yml`) to prevent redundant builds on unrelated commits.
  - Removed the conflicting `.github/workflows/deploy-docs.yml`.

### 📚 Documentation & Software Engineering Standards
- **Enterprise Software Engineering Extensions**:
  - Documented enterprise production tooling blueprints across the stack: **Prometheus & Grafana** (`n8n-observability`), **OpenTelemetry** distributed tracing with W3C traceparent headers, **Traefik v3 / Caddy** reverse proxy and rate-limiting, **PgBouncer** connection pooling, **HashiCorp Vault / Infisical** dynamic secret management, and **k6** webhook stress testing.
- **Architectural Diagrams**:
  - Added Mermaid sequence diagrams for distributed webhook ingestion and task runner sidecar IPC.
  - Added Mermaid flowchart for the autoscaler queue-depth decision engine loop.
- **Reliability & Operations**:
  - Added Site Reliability Engineering (SRE) SLOs and SLIs (99.95% availability, P95 < 150ms).
  - Added operational runbooks for zero-downtime rolling updates, Redis health checks, and database orphan healing.
  - Updated workflow portfolio metrics to reflect 100 compiled production workflows.

---

## [1.4.0] - 2026-09-06

### 🚀 Changed
- **n8n Upgraded to Latest Release**: Upgraded core base images to latest official release (`docker.n8n.io/n8nio/n8n:latest`).
- **Standardized Multi-Stage Docker Builds**: Aligned `Dockerfile` and `docker-compose.yml` to pull from the official `docker.n8n.io` mirror, ensuring identical base image layering between `n8n-init`, `n8n-main-server`, `n8n-webhook`, and `n8n-worker`.

### 🛡️ Fixed & Hardened
- **Redis AOF Crash-Loop Resolution & Self-Healing**:
  - Diagnosed and fixed an append-only file (AOF) corruption (`appendonly.aof.6.incr.aof: Expected \r\n, got: 0000`) caused by an ungraceful container termination, which was putting Redis in a persistent restart loop.
  - Truncated the corrupt 5,644 trailing bytes to restore complete volume data integrity without data loss.
  - Added `aof-load-truncated yes` and `aof-use-rdb-preamble yes` to `redis.conf` to permanently prevent crash loops and enable automatic crash self-healing on container reboots.
- **Worker & Sidecar Health Stabilization**: Verified worker health check endpoints (`http://127.0.0.1:5679/healthz`), restored clean connectivity to the BullMQ Redis broker, and stabilized runner sidecars (`n8n-worker-runner`).
- **Dynamic Database Orphan Cleanup**: Modernized `scripts/cleanup.sql` to dynamically detect and transition orphaned executions older than 24 hours from `running`/`waiting` to `crashed`, replacing historical hardcoded execution IDs.

### 📚 Documentation
- **Production Troubleshooting Runbook**: Added comprehensive runbook in `docs/troubleshooting.md` for diagnosing and repairing Redis AOF corruptions using `redis-check-aof` and offset truncation.
- **Production Guide Updates**: Updated `docs/production_guide.md` with Redis queue broker persistence and durability guidelines.
- **Engineering Standards**: Updated `docs/software_engineering_standards.md` with broker resilience standards and database orphan-healing rules.

### ✨ Added
- **GPT-OSS-20B Workflows**: Added two new workflows for 20B+ parameter inference:
  - `GPT_OSS_20B_OpenRouter.json`: Uses OpenRouter's API (`openai/gpt-oss-20b:free`) to bypass local hardware limits.
  - `GPT_OSS_20B_HuggingFace.json`: Uses Hugging Face's OpenAI-compatible v1 router (`router.huggingface.co/v1`) with Groq backend.

### 🐛 Fixed
- **AI Agent "Invalid input" Errors**: Fixed an issue in `GPT-OSS-20B_AI_Agent_Advanced.json` where the OpenAI Chat Model node failed with "Bad request" when tools were attached. Removed invalid expression prefixes from the model string and explicitly switched the Agent Type to **Conversational Agent** (ReAct) to bypass native function-calling requirements on open-source models.
- **Hugging Face Inference Support**: Replaced legacy Serverless Inference API endpoints with the new OpenAI-compatible v1 router to fix `Model not supported by provider hf-inference` errors on large models.
- **Model Language Drift**: Injected an English-enforcing system prompt (`"Always respond in English..."`) into AI workflows to prevent models from mirroring foreign languages from user prompts.

---

## [1.3.0] - 2026-07-13

### ✨ Added
- **HuggingFace Inference API Integration**: Added auto-provisioned `httpHeaderAuth` credential (`HuggingFace API — n8n Stack`) for calling HuggingFace-hosted models (e.g. `openai/gpt-oss-20b`) from n8n workflows.
  - New `.env` variable: `HUGGINGFACE_API_TOKEN` — set your HF token once and the credential is seeded automatically by `n8n-init`.
  - New workflow: `GPT_OSS_20B_HuggingFace.json` — a complete workflow with Chat Trigger → HTTP Request → 503/model-loading retry logic → Response Parser.
- **Updated `provision.js`**: Extended the one-shot credential provisioner to create the HuggingFace `httpHeaderAuth` credential alongside existing PostgreSQL, Redis, WAHA, Ollama, and MSSQL credentials.

---

## [1.2.0] - 2026-07-06

### ✨ Added
- **Workflow Export Automation**: Developed `scripts/export_workflows.py`, a cross-platform Python script that runs on the host and automates exporting all active workflows from n8n's internal PostgreSQL database and splitting them into individual, clean, formatted JSON files in the `workflows/` directory.

### 🔧 Changed
- **Ollama Local Engine Restoration**: Reconfigured both the V1 and V2 workflows (`Apple RAG ChatBot` and `Apple RAG Chatbot V2`) to use local Ollama models (`qwen2.5:3b-4k`) with the shared credential `wDe9MCIO6q1M7Gau` to satisfy local computing preferences.

### 🐛 Fixed
- **Google Drive Trigger Error in V2**: Resolved the `No data with the current filter could be found` error. Corrected the folder watch target from an empty/invalid placeholder ID to the actual PDF folder ID `1kiyeVdh-lP45tH8uV-_8hpPVQc1DR_NK`.
- **Default Data Loader Parser Bug in V2**: Updated the LangChain `Default Data Loader` parameters to specify `"loader": "pdfLoader"` and `"binaryDataKey": "data"`, enabling accurate text extraction from PDF streams.
- **RAG System Prompt Constraints**: Removed artificial instructions limiting the AI agent to only Q1 reports, permitting full reasoning over Q1-Q4 fiscal data.

---

## [1.1.0] - 2026-07-06

### 🐛 Fixed
- **Windows Color Picker UI Freeze**: Globally pinned n8n and Task Runner versions in `docker-compose.yml` to `2.28.6` to pull the patch resolving local Windows UI colorpicker freezes.

---

## [1.0.0] - 2026-07-05

### 🚀 Added
- **Production Queue Stack**: Initial release of the production-ready n8n stack featuring Redis queue-mode workers, autoscaling logic, Qdrant database integration, and WAHA community node deployment.
