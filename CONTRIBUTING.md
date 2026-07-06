# 🤝 Contributing Guidelines

Welcome to the **n8n Production Autoscaling Stack**! To maintain code quality, ease of deployment, and clean version control, please follow these guidelines when contributing to this repository.

---

## 📂 Table of Contents
1. [Development Environment](#-development-environment)
2. [Workflow Version Control](#-workflow-version-control)
3. [Automation Scripts](#-automation-scripts)
4. [Custom Packages and Sandbox Configuration](#-custom-packages-and-sandbox-configuration)
5. [Database Maintenance](#-database-maintenance)

---

## 💻 Development Environment

- **Prerequisites**: Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine (Linux) installed.
- **Secrets Management**: Configuration parameters must be stored in `.env`.
  
  > [!CAUTION]
  > Never commit `.env` or files containing decrypted API keys, passwords, or session tokens to the repository.

---

## 🔄 Workflow Version Control

All workflows are stored as individual files under the `workflows/` directory.

### Automating Exports (Preferred)
A custom script has been created to pull all workflows from the running n8n instance, clean up temporary configurations, and write them as separate files:
```bash
python scripts/export_workflows.py
```

### Manual Workflow Management
To import or export single workflows manually via Docker CLI:

- **Exporting a single workflow**:
  ```powershell
  docker compose exec n8n n8n export:workflow --id=<WORKFLOW_ID> --output=/home/node/<WORKFLOW_NAME>.json
  docker compose cp n8n:/home/node/<WORKFLOW_NAME>.json workflows/<WORKFLOW_NAME>.json
  ```

- **Importing a single workflow**:
  ```powershell
  docker compose cp workflows/<WORKFLOW_NAME>.json n8n:/home/node/<WORKFLOW_NAME>.json
  docker compose exec n8n n8n import:workflow --input=/home/node/<WORKFLOW_NAME>.json
  ```

---

## ⚡ Automation Scripts

The `scripts/` directory contains automation and diagnostic tools:
- **[export_workflows.py](scripts/export_workflows.py)**: Automates workflow backup and extraction from the database.
- **[modify_workflow.py](scripts/modify_workflow.py)**: Batch updates model properties and context sizes for local LLM nodes.
- **[cleanup.sql](scripts/cleanup.sql)**: A PostgreSQL script to optimize storage, mark orphaned runs as crashed, and run vacuuming.

---

## 🌐 Custom Packages and Sandbox Configuration

If your workflows require custom Python packages or Node.js modules in n8n Code nodes:

1. **JavaScript Dependencies**:
   - Append to the `pnpm add` block in `Dockerfile.runner`.
   - Update `NODE_FUNCTION_ALLOW_EXTERNAL` inside `n8n-task-runners.json` to allow sandbox usage.

2. **Python Dependencies**:
   - Append to the `uv pip install` block in `Dockerfile.runner`.
   - Update `N8N_RUNNERS_EXTERNAL_ALLOW` inside `n8n-task-runners.json`.

3. **Apply Changes**:
   ```bash
   docker compose build --no-cache n8n-worker-runner && docker compose up -d
   ```

---

## 🗄️ Database Maintenance

Keep the persistent PostgreSQL storage optimal. Execute cleanup tasks using the provided SQL script:
```bash
docker compose exec -T postgres psql -U n8n_user -d n8n < scripts/cleanup.sql
```
