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

## Confirmed crash: `appendonly.aof.7.incr.aof` is corrupt (October 29, 2026)

The recorded local logs contain:

```text
DB loaded from base file appendonly.aof.7.base.rdb
Bad file format reading the append only file appendonly.aof.7.incr.aof
```

**This is not a slow healthcheck**. Redis successfully loads the base RDB
(19 keys) and aborts replaying a corrupt incremental AOF. A longer
`start_period` and more memory cannot repair malformed AOF bytes.

Use the steps below in PowerShell from the root of this repository. Each
command targets the Redis Docker **volume**, not PostgreSQL or the n8n data
directory. Redis persistence repair can truncate commands and lose pending
queue jobs; preserve the original files first.

### A. Stop Redis and services that use the queue

```powershell
docker compose stop n8n-autoscaler redis-monitor n8n-webhook n8n-worker n8n-worker-runner n8n n8n-runner redis
```

PostgreSQL may stay running. Do **not** use `docker compose down -v`.
Do not execute AOF repair while Redis is running or while an autoscaler is
trying to restart queue consumers.

### B. Identify and back up the exact Redis named volume

```powershell
# Use JSON output to avoid Windows PowerShell stripping double quotes from
# Go template expressions such as eq .Destination "/data".
$MountJson = docker inspect n8n-redis --format '{{json .Mounts}}'
if ($LASTEXITCODE -ne 0) {
    throw "Cannot inspect n8n-redis. Stop here."
}
$Mounts = $MountJson | ConvertFrom-Json
$RedisMount = @($Mounts | Where-Object {
    $_.Type -eq "volume" -and $_.Destination -eq "/data"
})
if ($RedisMount.Count -ne 1) {
    throw "Expected exactly one Redis named volume mounted at /data. Stop here."
}
$VolumeName = $RedisMount[0].Name
Write-Host "Redis volume: $VolumeName"

# Use a sibling directory OUTSIDE the Git repository; do not commit queue data.
$BackupDir = Join-Path (Split-Path -Parent $PWD.Path) ("n8n-redis-backup-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

docker run --rm `
    --mount "type=volume,source=$VolumeName,target=/data,readonly" `
    --mount "type=bind,source=$BackupDir,target=/backup" `
    --entrypoint sh redis:7-alpine `
    -c 'cd /data && tar -czf /backup/redis-data-before-repair.tar.gz .'
if ($LASTEXITCODE -ne 0) { throw "Backup failed. STOP: do not repair Redis." }

$Archive = Join-Path $BackupDir 'redis-data-before-repair.tar.gz'
if (-not (Test-Path $Archive) -or (Get-Item $Archive).Length -eq 0) {
    throw "Backup archive missing/empty. STOP: do not repair Redis."
}

docker run --rm `
    --mount "type=bind,source=$BackupDir,target=/backup,readonly" `
    --entrypoint sh redis:7-alpine `
    -c 'tar -tzf /backup/redis-data-before-repair.tar.gz >/dev/null'
if ($LASTEXITCODE -ne 0) { throw "Backup archive is unreadable. STOP." }

Get-Item $Archive | Select-Object FullName, Length
```

This verifies that the archive exists and can be listed; it does **not**
prove every Redis queue record is logically recoverable.

### C. Inspect on a *separate writable clone* (do not inspect a read-only mount)

**Why:** On Redis 7, `redis-check-aof` may open the base AOF in a mode that
requires a writable filesystem, **even without** `--fix`. A
`Cannot open file ... Read-only file system` error is an inspection-method
failure, not additional evidence of corruption. Never solve it by making the
original Redis volume writable for preliminary inspection.

Unpack the verified backup archive into a **new** Docker named volume. This
example uses the dated backup path from the October 29, 2026 incident;
adjust the path if your backup is elsewhere:

```powershell
$BackupDir = 'D:\courses\Data Science\Data Engineering\n8n-redis-backup-20261029-222256'
$Archive = Join-Path $BackupDir 'redis-data-before-repair.tar.gz'
if (-not (Test-Path $Archive)) { throw "Backup missing: $Archive" }

$RecoveryVolume = 'n8n-redis-recovery-' + (Get-Date -Format 'yyyyMMddHHmmss')
docker volume create $RecoveryVolume | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Cannot create scratch Redis volume" }

docker run --rm `
    --mount "type=volume,source=$RecoveryVolume,target=/data" `
    --mount "type=bind,source=$BackupDir,target=/backup,readonly" `
    --entrypoint sh redis:7-alpine `
    -c 'cd /data && tar -xzf /backup/redis-data-before-repair.tar.gz && test -s /data/appendonlydir/appendonly.aof.manifest'

if ($LASTEXITCODE -ne 0) { throw "Failed to extract or verify scratch copy" }

docker run --rm `
    --mount "type=volume,source=$RecoveryVolume,target=/data" `
    --entrypoint redis-check-aof redis:7-alpine `
    /data/appendonlydir/appendonly.aof.manifest

Write-Host "AOF checker exit code: $LASTEXITCODE"
```

The *scratch copy* is writable to the checker; the original `$VolumeName`
and original backup archive remain unmounted or read-only and unchanged.
A nonzero checker exit status is expected when corruption is detected.
Read the reported error offset and possible byte loss **before** any repair.

Redis 7+ tracks a base snapshot plus incremental files in a manifest.
**Do not** delete a damaged `.incr.aof` file or manually edit the manifest.

### D. Confirmed AOF corruption: 227-byte invalid suffix (October 29, 2026)

Observed against the independent recovery volume:

```text
BASE AOF appendonly.aof.7.base.rdb is valid
AOF analyzed: filename=appendonly.aof.7.incr.aof,
  size=48033949, ok_up_to=48033722, diff=227
AOF appendonly.aof.7.incr.aof is not valid.
```

The Redis checker considers the first 48,033,722 bytes valid; the
unparseable 227-byte suffix is 0.00047% of the incremental AOF. Repairing
that tail has a small *byte* impact but could still remove an important
incomplete job command. Do not treat a small truncation as proof of zero
lost jobs.

With the confirmed, verified 2,826,543-byte archive and scratch volume,
repair **only the scratch copy** first:

```powershell
$RecoveryVolume = "n8n-redis-recovery-20261029222615"

docker run --rm -it `
    --mount "type=volume,source=$RecoveryVolume,target=/data" `
    --entrypoint redis-check-aof redis:7-alpine `
    --fix /data/appendonlydir/appendonly.aof.manifest
```

Review the prompt and approve the truncation only if the expected
227-byte suffix is proposed. Stop if the tool reports a different file,
a substantially larger loss, or a different corruption offset.

Re-check the **repaired copy**:

```powershell
docker run --rm `
    --mount "type=volume,source=$RecoveryVolume,target=/data" `
    --entrypoint redis-check-aof redis:7-alpine `
    /data/appendonlydir/appendonly.aof.manifest

if ($LASTEXITCODE -ne 0) { throw "Scratch AOF is still invalid. Stop." }
```

### E. Boot the repaired copy in an isolated test container

Avoid connecting to the n8n Docker network, exposing a host port, or
running any queue consumers against the scratch copy:

```powershell
$TestContainer = "n8n-redis-recovery-test-" + (Get-Date -Format "yyyyMMddHHmmss")
docker run -d `
    --network none `
    --name $TestContainer `
    --mount "type=volume,source=$RecoveryVolume,target=/data" `
    --entrypoint redis-server redis:7-alpine `
    --appendonly yes --dir /data --appenddirname appendonlydir `
    --maxmemory 192mb --maxmemory-policy noeviction

if ($LASTEXITCODE -ne 0) { throw "Cannot start isolated Redis test" }
docker logs --tail 50 $TestContainer
docker exec $TestContainer redis-cli ping
docker exec $TestContainer redis-cli INFO keyspace
```

Verify `Ready to accept connections` in the logs and `PONG` from
`redis-cli ping`. Redis may briefly return `LOADING` while it replays
the AOF; check logs again if necessary.

Once verified, stop and remove **only the test container** (do not remove
`$RecoveryVolume`):

```powershell
docker stop $TestContainer
docker rm $TestContainer
```

### F. Apply the same verified repair to the original Redis volume

Only after the isolated test succeeds and the potential loss of the last
incomplete Redis operation is acceptable:

```powershell
docker compose stop n8n-autoscaler redis-monitor n8n-webhook n8n-worker n8n-worker-runner n8n n8n-runner redis
if ($LASTEXITCODE -ne 0) { throw "Failed to stop queue services" }

$MountJson = docker inspect n8n-redis --format '{{json .Mounts}}'
if ($LASTEXITCODE -ne 0) { throw "Cannot inspect original Redis mount" }
$RedisMount = @($MountJson | ConvertFrom-Json | Where-Object {
    $_.Type -eq "volume" -and $_.Destination -eq "/data"
})
if ($RedisMount.Count -ne 1) { throw "Cannot identify original Redis volume" }
$VolumeName = $RedisMount[0].Name
if ($VolumeName -eq $RecoveryVolume) { throw "Refusing to use scratch volume as original" }

$Running = docker inspect n8n-redis --format '{{.State.Running}}'
if ($LASTEXITCODE -ne 0 -or $Running.Trim() -ne 'false') {
    throw "Original Redis must be stopped before repair"
}

Write-Host "Original Redis volume: $VolumeName"
Write-Host "Recovery-only scratch volume: $RecoveryVolume"

docker run --rm -it `
    --mount "type=volume,source=$VolumeName,target=/data" `
    --entrypoint redis-check-aof redis:7-alpine `
    --fix /data/appendonlydir/appendonly.aof.manifest
```

Review the live-volume repair's own reported suffix before agreeing.
Afterwards, run the checker without `--fix` against the original volume
and ensure it exits with code 0.

### G. Validate the repaired production Redis broker, then start core n8n

```powershell
docker compose up -d redis
docker compose logs --no-color --tail=60 redis
docker exec n8n-redis redis-cli ping
docker compose ps redis
```

`PONG` and `healthy` are expected. If Redis exits again, stop and examine
the newly emitted error; do not repeatedly run `--fix`.

Only when Redis is healthy:

```powershell
docker compose up -d n8n n8n-runner n8n-worker n8n-worker-runner
docker compose ps
```

Review failed/queued workflow executions before restarting autoscaling or
other optional services. Existing PostgreSQL data and
`N8N_ENCRYPTION_KEY` must remain untouched.

### References

- [Redis persistence and AOF recovery](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [Docker named-volume backup methods](https://docs.docker.com/engine/storage/volumes/)

---

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
