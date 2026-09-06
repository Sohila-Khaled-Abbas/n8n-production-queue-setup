# Operational & Diagnostic Scripts Reference Guide

This document lists, describes, and provides usage instructions for the automation, diagnostic, and maintenance scripts located in the `scripts/` directory.

---

## 🗂️ Overview of Scripts

| Script File | Language | Purpose | Environment |
| :--- | :--- | :--- | :--- |
| **[auto_sync.ps1](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/auto_sync.ps1)** | PowerShell | Automates exporting workflows, updating docs data, and git push. | Host Machine |
| **[configure_sql_server.ps1](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/configure_sql_server.ps1)** | PowerShell | Configures SQL Server host auth & creates logins. | Host Machine (Admin) |
| **[provision.js](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/provision.js)** | Node.js | Seeds default stack credentials & installs WAHA node. | `n8n-init` Container |
| **[cleanup.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/cleanup.sql)** | PostgreSQL | Prunes execution history and runs table compression. | `postgres` Database |
| **[modify_workflow.py](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/modify_workflow.py)** | Python | Batch configures Ollama nodes to optimize GPU VRAM. | Host/Any Machine |
| **[parse_nodes.py](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/parse_nodes.py)** | Python | Analyzes workflow exports for Ollama node details. | Host/Any Machine |
| **[durations.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/durations.sql)** | PostgreSQL | Measures the execution times of the latest 15 runs. | `postgres` Database |
| **[durations_times.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/durations_times.sql)** | PostgreSQL | Measures duration averages for a specific workflow ID. | `postgres` Database |
| **[search_errors.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/search_errors.sql)** | PostgreSQL | Searches JSON execution logs for explicit error messages. | `postgres` Database |
| **[get_error.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/get_error.sql)** | PostgreSQL | Extracts raw error messages from specific execution data. | `postgres` Database |
| **[get_keys.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/get_keys.sql)** | PostgreSQL | Lists top-level keys in execution logs JSON structure. | `postgres` Database |
| **[count_chat.sql](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/scripts/count_chat.sql)** | PostgreSQL | Aggregates and counts chat logs grouped by session ID. | `postgres` Database |

## 🛠️ Workflow & Repo Synchronization

### 1. `auto_sync.ps1`
- **Purpose**: Runs a complete automated sync workflow:
  1. Exports all n8n workflows from the running container into standard formatted `.json` files under `workflows/`.
  2. Runs `generate_docs_data.py` to refresh `docs/data.json`.
  3. Stages all changes, creates a timestamped git commit, and pushes to remote.
- **Execution**:
  ```powershell
  .\scripts\auto_sync.ps1
  ```

---

## 🛠️ Database Setup & Provisioning

### 1. `configure_sql_server.ps1`
- **Purpose**: Automates configuring a local Microsoft SQL Server instance to allow n8n connections.
  1. Enables Mixed Mode Authentication (SQL Server and Windows Authentication).
  2. Restarts the SQL Server (`MSSQLSERVER`) Windows service.
  3. Generates a secure, random password and creates a SQL Login named `n8n_sql_user` with `sysadmin` server role privileges.
  4. Automatically updates your local `.env` file with the newly generated password.
- **Execution**: Run as Administrator in PowerShell:
  ```powershell
  PowerShell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_sql_server.ps1
  ```

### 2. `provision.js`
- **Purpose**: Runs automatically inside the `n8n-init` container during stack startup.
  - Idempotently checks if essential system credentials (PostgreSQL, Redis, WAHA API, local Ollama instance, MSSQL, HuggingFace API) exist.
  - If missing, seeds them with values configured in `.env`.
  - The HuggingFace credential is provisioned as an `httpHeaderAuth` type with `Authorization: Bearer <HUGGINGFACE_API_TOKEN>`, ready for use with the HuggingFace Inference API.
  - Installs the community WAHA node (`@devlikeapro/n8n-nodes-waha`) if it is not already installed.
- **Execution**: Automatically triggered during `docker compose up`. If needed, you can force trigger it:
  ```bash
  docker compose run --rm n8n-init
  ```

---

## 🧹 Database Maintenance

### 1. `cleanup.sql`
- **Purpose**: Heavy execution history can cause n8n database storage to swell to hundreds of gigabytes (bloat). This script cleans it up safely.
  - Dynamically sets orphaned execution records older than 24 hours (e.g. from terminated worker processes) to `crashed`.
  - Deletes all execution entities and binary data logs older than 3 days.
  - Reclaims and compresses physical disk space using `VACUUM FULL`.
  - Reports final table sizes.
- **Execution**: Run directly on your postgres container:
  ```bash
  docker compose exec -T postgres psql -U n8n_user -d n8n < scripts/cleanup.sql
  ```

---

## 🏎️ Performance & Diagnostic Queries

Execute these queries inside the PostgreSQL container to troubleshoot workflows:
```bash
# To open interactive database CLI:
docker compose exec postgres psql -U n8n_user -d n8n
```

### 1. `durations.sql`
- **Purpose**: Lists details of the 15 most recent executions, sorted by start time.
- **Why use**: Easily identify which workflows are currently active, failing, or running exceptionally slow.
- **Query**:
  ```sql
  SELECT id, status, mode, "workflowId", ("stoppedAt" - "startedAt") as duration 
  FROM execution_entity 
  ORDER BY "startedAt" DESC LIMIT 15;
  ```

### 2. `durations_times.sql`
- **Purpose**: Diagnostic query to view durations for a specific workflow ID.
- **Usage**: Edit the query to substitute the target `workflowId` to inspect slow-running workflows.

### 3. `search_errors.sql` and `get_error.sql`
- **Purpose**: Parse raw execution JSON documents stored in the database to retrieve node error messages and stack traces without loading the full execution log in the n8n UI (which can crash browsers if log payloads are huge).
- **Usage**: Replace `2308` with the failed execution ID.

### 4. `count_chat.sql`
- **Purpose**: Lists conversational message counts for all active sessions in the `n8n_chat_histories` table.
- **Query**:
  ```sql
  SELECT count(*), session_id FROM n8n_chat_histories GROUP BY session_id;
  ```

---

## 🧠 Workflow Node Automation (Ollama Optimization)

### 1. `parse_nodes.py`
- **Purpose**: Reads a raw workflow export (`workflow_nodes_raw.json`) and prints full JSON data of any detected Ollama Chat Model nodes.
- **Usage**:
  ```bash
  python scripts/parse_nodes.py
  ```

### 2. `modify_workflow.py`
- **Purpose**: Automatically optimizes Ollama nodes inside the workflow export (`workflow_nodes_raw.json`) to prevent Out-Of-Memory crashes on low-end GPUs (e.g., GTX 1650 4GB).
  - Switches the model to `qwen2.5:1.5b` (highly performant small-footprint model).
  - Sets the context window (`numCtx`) limit option to `2048` tokens (saving up to 2GB VRAM cache overhead).
  - Outputs a ready-to-import `workflow_nodes_modified.json` file.
- **Usage**:
  ```bash
  python scripts/modify_workflow.py
  ```
