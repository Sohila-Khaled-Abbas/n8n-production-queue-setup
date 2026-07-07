# 🤝 Contributing Guidelines

Welcome to the **n8n Production Autoscaling Stack**! To maintain code quality, ease of deployment, and clean version control, please follow these guidelines when contributing to this repository.

---

## 📂 Table of Contents
1. [Development Environment](#-development-environment)
2. [Git Workflow & Branching](#-git-workflow--branching)
3. [Commit Message Conventions](#-commit-message-conventions)
4. [Pull Request Process](#-pull-request-process)
5. [Code Quality & Linting](#-code-quality--linting)
6. [Testing Guidelines](#-testing-guidelines)
7. [Workflow Version Control](#-workflow-version-control)
8. [Custom Packages and Sandbox Configuration](#-custom-packages-and-sandbox-configuration)
9. [Database Maintenance & Safety](#-database-maintenance--safety)

---

## 💻 Development Environment

- **Prerequisites**: Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine (Linux) installed.
- **Secrets Management**: Configuration parameters must be stored in `.env`.
  
  > [!CAUTION]
  > Never commit `.env` or files containing decrypted API keys, passwords, or session tokens to the repository. The `.gitignore` is pre-configured to ignore all local environments.

---

## 🌿 Git Workflow & Branching

We follow a structured branching model to keep the main branch stable:

- **Main Branch (`main`)**: Reflects the production-ready state. Directly committing to `main` is restricted.
- **Feature Branches (`feat/...`)**: Used for introducing new features, tools, or integrations.
- **Bug Fix Branches (`fix/...`)**: Used for fixing issues and resolving failures.
- **Documentation Branches (`docs/...`)**: Used for editing README, templates, guides, or other documentation.
- **Refactoring Branches (`refactor/...`)**: Code improvement, optimization, or renaming without changing behavior.
- **Chore/Maintenance Branches (`chore/...`)**: Dependency upgrades, CI updates, or dev-environment adjustments.

---

## 💬 Commit Message Conventions

We use **Conventional Commits** to enforce a readable and searchable commit history. The commit message format should be:

```
<type>(<scope>): <short description>

[optional body describing changes in detail]

[optional footer for issue tracking, e.g., Closes #123]
```

### Allowed Types:
* `feat`: A new feature (e.g., `feat(autoscaler): add cooldown interval logic`)
* `fix`: A bug fix (e.g., `fix(runner): handle Chromium browser launch error`)
* `docs`: Documentation updates (e.g., `docs(readme): update API key guidelines`)
* `style`: Styling changes that do not affect code logic (whitespace, formatting)
* `refactor`: A code change that neither fixes a bug nor adds a feature
* `test`: Adding missing tests or correcting existing tests
* `chore`: Maintenance tasks, dependencies updates, CI configs

---

## 🔀 Pull Request Process

1. **Create a Branch**: Create a branch off `main` following the branching guidelines.
2. **Commit and Push**: Write clean code, commit following the Conventional Commits rules, and push your changes.
3. **Verify Locally**: Run the linting and styling tools locally before opening a PR.
4. **Open a PR**: Open a Pull Request to merge into `main`. Fill out the Pull Request Template completely.
5. **CI Status**: Ensure all GitHub Actions checks (linting, Docker checks) pass.
6. **Peer Review**: A minimum of one approved review is required before merging.

---

## 🛡️ Code Quality & Linting

We enforce static analysis and styling standards to ensure long-term codebase health.

### Python Code Quality (autoscaler, monitor, scripts)
We use **Ruff** for linting, code quality checks, and formatting. Configure your IDE to run Ruff on save, or run it manually:

* **Lint Code**:
  ```bash
  ruff check .
  ```
* **Auto-fix Lint Issues**:
  ```bash
  ruff check . --fix
  ```
* **Format Check**:
  ```bash
  ruff format --check .
  ```
* **Auto-format Code**:
  ```bash
  ruff format .
  ```

### Dockerfiles
We use **Hadolint** to check Dockerfile standards. Check your Dockerfiles before committing:
```bash
hadolint Dockerfile Dockerfile.runner autoscaler/Dockerfile monitor/monitor.Dockerfile
```

---

## 🧪 Testing Guidelines

Before pushing changes to production or staging services, verify functionality:

### 1. Script Unit & Integration Verification
When modifying automation scripts (`export_workflows.py`, `modify_workflow.py`):
- Run the script locally in a test directory to verify file generation and formatting.
- Ensure proper error logging using Python's standard `logging` library. Do not use plain `print` statements for errors.

### 2. Autoscaler Simulation
When modifying the autoscaler (`autoscaler.py`):
- Test the Redis connection handler locally by mocking Redis queue lengths.
- Perform a local dry-run of compose scaling commands to check subprocess handling:
  ```bash
  # Start local containers
  docker compose up -d redis postgres
  # Run autoscaler locally with debug log level
  export REDIS_HOST=localhost
  export REDIS_PORT=6379
  export LOG_LEVEL=DEBUG
  python autoscaler/autoscaler.py
  ```

### 3. Stack Deployment Verification
Verify the entire Docker Compose orchestration starts correctly:
```bash
docker compose config  # Check compose syntax validity
docker compose up -d   # Launch the stack
docker compose ps      # Verify all containers are running and healthy
```

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

## 🗄️ Database Maintenance & Safety

### Database Hygiene
Keep the persistent PostgreSQL storage optimal. Execute cleanup tasks using the provided SQL script:
```bash
docker compose exec -T postgres psql -U n8n_user -d n8n < scripts/cleanup.sql
```

### ⚠️ Commit Safety Warning
Do **NOT** commit raw SQL backups (`.sql`) or Postgres dumps (`.dump`) to the git repository. 
- These files are large, slow down git operations, and can contain sensitive credential records or API keys.
- The `.gitignore` is set to block `.sql` and `.dump` files. If you generate temporary backups, make sure they are stored outside the Git working directory or placed inside ignored folders.
