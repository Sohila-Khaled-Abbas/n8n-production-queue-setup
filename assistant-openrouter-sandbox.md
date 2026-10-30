# n8n Assistant with OpenRouter and local sandbox

> **Opt-in feature, local development only.** This does not replace the existing queue-mode Compose project, Redis, Postgres, workers, volumes, external task runners or ngrok port. Never run this on a production-facing instance without reviewing the privileged Docker-in-Docker risk. n8n recommends Daytona for production.

## 0. Prerequisites and safety

- **Revoke the OpenRouter key previously shared in chat.** Create a fresh key and set limits/restrictions in OpenRouter. Never paste or commit it to GitHub.
- Follow [Redis recovery](redis-windows-recovery.md) until Redis is healthy. Corrupt AOF must be recovered separately; the Assistant overlay does not fix it.
- Follow [in-place n8n version migration](n8n-v3-beta-in-place.md). Confirm the currently running image is n8n 2.35+ and compatible with the Assistant. **Do not let the 3.0.1 default in .env.example unintentionally upgrade production data.** Use the version verified for your stack.
- Back up Postgres, the n8n bind mount, your existing private .env, and Redis queue data before any version change. Keep `N8N_ENCRYPTION_KEY` unchanged. Never run `docker compose down -v`.
- Docker Desktop + WSL2 must have adequate CPU, memory and disk. Keep backups outside the repo.
- The Assistant is a preview feature. Review all changes it proposes, especially workflows that access credentials.

## 1. Private .env only

Edit your EXISTING .env; **do not replace it with .env.example**.

```dotenv
# Pin the release verified against https://github.com/n8n-io/n8n-sandbox-service/releases
N8N_SANDBOX_VERSION=REPLACE_WITH_VERIFIED_STABLE_SERVICE_VERSION

# Use the exact OpenRouter model identifier; confirm its tool-calling
# compatibility and free-tier limits at https://openrouter.ai/models
N8N_INSTANCE_AI_MODEL=openrouter/openrouter/free
N8N_INSTANCE_AI_MODEL_API_KEY=REPLACE_WITH_NEW_ROTATED_OPENROUTER_KEY

# If you have existing explicitly enabled modules, list all of them too.
N8N_ENABLED_MODULES=instance-ai

# Secrets: generate separate random values for these fields.
SANDBOX_API_KEYS=REPLACE_WITH_RANDOM_API_KEY
N8N_SANDBOX_SERVICE_API_KEY=REPLACE_WITH_SAME_API_KEY
SANDBOX_API_RUNNER_REGISTRATION_TOKEN=REPLACE_WITH_RANDOM_REGISTRATION_TOKEN
SANDBOX_API_RUNNER_API_KEY=REPLACE_WITH_RANDOM_RUNNER_KEY
SEARXNG_SECRET=REPLACE_WITH_RANDOM_SEARCH_SECRET
```

PowerShell to generate each random secret (run separately and paste only into local .env):

```powershell
# Run this once per independent secret.
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant()
```

Avoid providing model keys to other services via `env_file: .env`; the override injects only required variables into each sandbox container.

## 2. Inspect before launch

From the existing repository folder, in PowerShell:

```powershell
git status --short --branch
docker compose ps -a
docker compose logs --tail 80 redis postgres
docker compose exec n8n n8n --version
docker compose -f docker-compose.yml -f compose.assistant.yml config --quiet
```

Check the status/versions; stop if existing data services are unhealthy or a migration is outstanding. **Do not print `docker compose config` to a public log**: it expands secret values. A successful `--quiet` validation confirms syntax only, not runtime compatibility.

## 3. Launch opt-in services, then restart n8n

```powershell
$files = @('-f','docker-compose.yml','-f','compose.assistant.yml')
docker compose @files pull sandbox-certs sandbox-api sandbox-runner-1 searxng
docker compose @files up -d sandbox-certs sandbox-api sandbox-runner-1 searxng
docker compose @files ps sandbox-api sandbox-runner-1 searxng
docker compose @files logs --tail 80 sandbox-certs sandbox-api sandbox-runner-1
```

Wait for sandbox-api healthy and runner registration. If all sandbox services work and your n8n version prerequisites pass:

```powershell
docker compose @files up -d --no-build n8n
docker compose @files exec n8n wget -qO- http://sandbox-api:8080/healthz
docker compose @files ps n8n sandbox-api sandbox-runner-1
```

The n8n service has an existing host-bound port 80 and external task runners. Don't add a new port 5678 mapping or launch the one-line installer against this project. If your custom n8n image does not have wget, test through `docker compose @files exec n8n node -e "..."` only after checking the installed runtime.

Open your existing editor at http://localhost or your configured secure ngrok URL; use **Settings → Assistant** to check the selected model provider and sandbox configuration. Build a disposable test workflow only, run it and confirm outputs. OpenRouter free models can be unavailable, rate-limited, or lack required tool-call behavior. Try an explicitly supported, tool-capable free model if the router fails.

## 4. Verify and troubleshoot

- `sandbox-certs` should complete successfully. API should be **healthy**.
- Verify the runner is registered in `sandbox-api` logs.
- If a connection is refused, check internal service DNS and logs; don't expose port 8080/9090.
- Runner launch may require pulling a nested sandbox image (disk usage).
- Only the main n8n process needs the Assistant UI settings; keep main/worker versions and runner images aligned.
- For runtime problems check service-specific logs without publishing secrets.
- Stop just the optional services with:
```powershell
docker compose @files stop sandbox-runner-1 sandbox-api searxng
```
To disable the Assistant, remove the override from startup commands and recreate **only n8n** using the base Compose after verifying its config. Do not destroy any volumes.

## Production hardening notes

The bundled sandbox runner is **privileged**; reserve it for a trusted local development machine and never publish its ports. The upstream certificate bootstrap currently sets broad read access, so this example should **not** be taken as an independently audited hardened mTLS deployment. For production, evaluate [Daytona](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-n8n-assistant/#setup-3-daytona-managed-sandbox-recommended-for-production), tighter firewall boundaries, secrets management and verified TLS permissions. Keep the sandbox version pinned across API, runner and nested sandbox images; never use `latest` for them.

## References

- https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-n8n-assistant/
- https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose/
- https://github.com/n8n-io/n8n/blob/master/docker/get-n8n-compose.yml
- https://github.com/n8n-io/n8n-sandbox-service/releases
- https://openrouter.ai/models
