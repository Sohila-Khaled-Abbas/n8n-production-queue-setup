# Contribution Guidelines

Thank you for contributing to the n8n Production Autoscaling Stack! To ensure code quality, reproducibility, and security, please follow these software engineering guidelines.

## Development Workflow

1. **Local Environment**:
   - Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) on Windows/macOS or Docker Engine on Linux.
   - Configure local configurations in `.env` using `.env.example` as a baseline. Never commit `.env` or raw credential keys.

2. **Managing Workflows**:
   - All workflows should be exported and version-controlled inside the `workflows/` directory.
   - To export a workflow for version control:
     ```bash
     docker compose exec n8n n8n export:workflow --id=<WORKFLOW_ID> --output=/home/node/<WORKFLOW_NAME>.json
     docker compose cp "n8n:/home/node/<WORKFLOW_NAME>.json" "workflows/<WORKFLOW_NAME>.json"
     ```
   - To import / update a workflow:
     ```bash
     docker compose cp "workflows/<WORKFLOW_NAME>.json" "n8n:/home/node/<WORKFLOW_NAME>.json"
     docker compose exec n8n n8n import:workflow --input=/home/node/<WORKFLOW_NAME>.json
     ```

## Code Quality & Engineering Best Practices

### Task Runners & Dependencies
- Avoid global package installations. Keep custom system/python/npm dependencies localized and reproducible inside `Dockerfile.runner`.
- If you add custom npm libraries:
  1. Append them in `Dockerfile.runner` to the `pnpm add` block.
  2. Add the module namespace to `NODE_FUNCTION_ALLOW_EXTERNAL` in `n8n-task-runners.json` to grant sandbox permission.
- If you add custom Python libraries:
  1. Append them in `Dockerfile.runner` to the `uv pip install` block.
  2. Add the library namespace to `N8N_RUNNERS_EXTERNAL_ALLOW` in `n8n-task-runners.json`.

### Database Maintenance
- Keep the database clean. Do not store manual execution histories forever. Use `scripts/cleanup.sql` periodically to vacuum dead records:
  ```bash
  docker compose exec -T postgres psql -U n8n_user -d n8n < scripts/cleanup.sql
  ```

### AI & Vector DB Integration
- When building RAG pipelines, ensure document loaders are configured as **binary** (e.g. `pdfLoader`) and target the correct binary data key (`data`). Defaulting to text loaders may cause n8n to index file metadata (names and paths) instead of actual contents.
- Keep Ollama models context constrained to `2048` or `4096` inside n8n model options to avoid GPU out-of-memory crashes on constrained hardware.
- For production-level performance, favor cloud model integrations (e.g., Google Gemini) using the `googlePalmApi` credentials.
