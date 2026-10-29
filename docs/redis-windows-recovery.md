# Redis startup recovery — Windows PowerShell / Docker Desktop

This runbook applies to `docker compose up -d` failing with
`dependency failed to start: container n8n-redis is unhealthy`.

The Redis container is the queue broker. The n8n main process, webhook
processor, workers and queue monitor wait for its healthcheck. A failed
dependency is **not** proof of data corruption, and a larger startup grace
period only helps *slow* AOF loading; it does not repair a broken server.

## 1. Inspect before changing anything

Run from the repository directory in **PowerShell** (Docker Desktop running):

```powershell
docker compose config --quiet
docker compose ps -a
docker compose logs --no-color --tail=120 redis
docker inspect n8n-redis --format '{{json .State.Health}}'
docker inspect n8n-redis --format 'Status={{.State.Status}} Exit={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}}'
docker stats --no-stream n8n-redis
```

If Redis is `unhealthy` but still running, its healthcheck log helps distinguish
`LOADING` (AOF still replaying), `PONG` (healthcheck mismatch) and connection errors.
If Redis has exited, the Redis service logs are the primary source of truth.
Inspect Docker Desktop's disk and memory resources if you see `OOMKilled=true`,
`No space left on device`, or `MISCONF`. Free host disk space and avoid scaling
workers until the broker is healthy.

Do not post your `.env`, passwords, encryption key, or raw credentials in an
issue or troubleshooting chat.

## 2. Apply the non-destructive Redis configuration changes

On the `fix/redis-local-startup-health` branch:

- `redis.conf` uses `maxmemory-policy noeviction`. Redis returns a write error
  rather than silently deleting Bull queue keys when the limit is reached.
- Redis has a 192 MB data limit and a 256 MB container limit, leaving room for
  process overhead. **These are starter values, not guaranteed capacity**.
- The healthcheck requires a literal `PONG`, and permits 60 seconds of startup
  grace plus retries while Redis replays persistent AOF data.

To start the broker first, without deleting or recreating any volumes:

```powershell
docker compose up -d postgres redis
docker compose ps redis
docker compose logs --no-color --tail=80 redis
docker exec n8n-redis redis-cli ping
```

Expected output from the final command: `PONG`.

If the Redis service is still unhealthy, **stop here** and use the log-based
decision guide below rather than repeatedly recreating containers.

## 3. Interpret common failures

| Log / inspection result | Meaning | Safe next action |
| --- | --- | --- |
| `LOADING Redis is loading the dataset in memory` | Redis is replaying persistent data | Monitor the logs and disk activity; allow initialization time |
| `OOMKilled=true`, `signal: killed`, or exit code 137 | Container or VM memory pressure | Check `docker stats` and Docker/WSL memory settings; limit other services before retrying |
| `Fatal error, can't open config file` or `Permission denied` | `./redis.conf` bind mount or file access failed | Verify the file exists in the Compose project root and Docker Desktop has access |
| `No space left on device` or `Can't open append-only file` | Storage is full or inaccessible | Check free space and Docker Desktop storage location; preserve the Redis volume |
| `Bad file format reading the append only file` | AOF corruption is possible | Back up the Redis volume **before** any repair; inspect the exact failing AOF/manifest file |
| `PONG` but healthcheck still fails | Healthcheck or Compose mismatch | Inspect `.State.Health.Log`, `docker compose config` and the deployed image |

**Do not** run `redis-check-aof --fix` against a live, unbacked-up volume.
That tool can truncate invalid data, which can mean lost queue jobs. If logs
prove AOF corruption, first stop Redis, make a verified copy of the `redis_data`
volume (including `appendonlydir` and the manifest), and plan repair against a
copy. The exact repair target depends on the log and Redis AOF layout; never
guess a file path.

**Do not** run `docker compose down -v`, `docker volume prune`, `docker system
prune --volumes`, or manually delete the `redis_data` / `postgres_data` volume
as a troubleshooting shortcut.

## 4. Start n8n only after Redis is healthy

For a lighter local startup on Windows, launch the core queue-mode services:

```powershell
docker compose up -d n8n n8n-runner n8n-worker n8n-worker-runner
docker compose ps
docker compose logs --no-color --tail=60 n8n n8n-worker
```

The repository's base Compose maps `80:5678`, so its current default
editor URL is **http://localhost**. That host port is not explicitly bound to
loopback in the base file; restrict inbound access via a firewall or use a
separate local-only port override before treating this as a private service.

Other services (`n8n-webhook`, `qdrant`, `waha`, queue monitor, autoscaler)
can be brought up individually when needed. Starting all of them on a
memory-constrained Windows development laptop can increase WSL/Docker pressure.
Do not change an existing `N8N_ENCRYPTION_KEY` or reset PostgreSQL data.

## 5. Share only safe diagnostic output if it still fails

Capture the following (redact sensitive application data before sharing):

```powershell
docker compose ps -a
docker compose logs --no-color --tail=100 redis
docker inspect n8n-redis --format '{{json .State.Health}}'
```

The Docker-generated *Gordon* suggestion is optional; it does not identify
the failure by itself. These three outputs allow a specific diagnosis.

## Related resources

- [Docker: Control startup and shutdown order](https://docs.docker.com/compose/how-tos/startup-order/)
- [BullMQ: Going to production — maxmemory-policy](https://docs.bullmq.io/guide/going-to-production)
- [Redis: Key eviction](https://redis.io/docs/latest/develop/reference/eviction/)
