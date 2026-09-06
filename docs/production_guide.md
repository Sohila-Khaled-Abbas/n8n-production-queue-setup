# Production Deployment & Operations Guide

This guide details best practices, architectural features, and configuration tuning for running this n8n Autoscaling Stack in a production environment.

---

## 💾 Binary Data Storage Modes

In n8n, files processed by nodes (e.g. PDFs, CSVs, images, zip files) are categorized as **binary data**. n8n supports three storage modes for this data, configured via the `N8N_DEFAULT_BINARY_DATA_MODE` environment variable in your `.env` file:

### 1. `filesystem` (Recommended for Production)
- **How it works**: Binary files are written directly to the server's disk under the `.n8n/binaryData` directory. In our Docker configuration, this directory is inside the `/home/node/.n8n` path, which is bound to the persistent host directory `./n8n-data`.
- **Pros**:
  - **Memory Efficiency**: Binary files are streamed directly to disk, keeping Node.js RAM footprint near zero.
  - **Scalability**: Prevents container Out-Of-Memory (OOM) crashes when downloading large files (e.g. large Google Drive PDFs or video assets).
  - **Inter-container sharing**: All containers (`n8n-main`, `n8n-worker`, `n8n-webhook`) share the same bind-mounted volume, so they can seamlessly read and write to this directory.
- **Cons**: Requires persistent, shared disk space.

### 2. `database` (Default/Development)
- **How it works**: Binary payloads are buffered entirely in the container's RAM, converted into base64 strings, and transmitted over the network to the PostgreSQL database.
- **Pros**: Easy to configure; no shared volume filesystem required.
- **Cons**:
  - **Memory spikes**: Downloading a 100MB file requires buffering it in memory multiple times. Under concurrent load, the container will exceed its memory limit (e.g. `1024M` in our compose stack) and get terminated by the OS Out-of-Memory (OOM) killer.
  - **Connection drops**: Bloated payloads sent to PostgreSQL can trigger packet size limits or transient network failures, resulting in the common error: `The connection to the server was closed unexpectedly`.

### 3. `memory`
- **How it works**: Stores binary data directly in Node.js process memory.
- **Pros**: Extremely fast read/write speeds.
- **Cons**: Highly vulnerable to OOM crashes. Absolutely not recommended for production.

---

## 🏎️ Database Tuning

To support high-concurrency queue execution (where multiple workers read/write to the database concurrently), our PostgreSQL container is pre-tuned with the following production-optimized configurations inside `docker-compose.yml`:

- `shared_buffers=128MB`: Dedicated RAM cache pool size.
- `effective_cache_size=384MB`: Guides the query planner on available file system cache.
- `work_mem=8MB`: Allocation per sorting or hash operation before writing to temporary disk files.
- `maintenance_work_mem=64MB`: Speeds up index builds, vacuums, and database migrations.
- `checkpoint_completion_target=0.9`: Spreads dirty page writes over 90% of the checkpoint duration to reduce I/O spikes.
- `wal_buffers=8MB`: Buffers WAL (Write-Ahead Logging) data before committing to disk.
- `max_connections=40`: Prevents database connection exhaustion.
- `synchronous_commit=off`: Disables waiting for disk commits on transactions, improving write performance significantly (at the minor risk of losing up to 3-5 seconds of execution history in a total server power outage).

---

## ⚡ Redis Broker Durability & Recovery Tuning

The Redis service acts as the central BullMQ queue broker coordinating between `n8n-main`, `n8n-webhook`, and `n8n-worker`. Our production setup in `redis.conf` is tuned for high throughput with crash-resilient persistence:

- **AOF + RDB Dual Durability**:
  - `appendonly yes` with `appendfsync everysec`: Records transactions to disk every second, ensuring virtually no queue loss.
  - `aof-use-rdb-preamble yes`: Uses compact RDB binary format for base AOF rewrites, accelerating container startup times.
- **Crash Self-Healing (`aof-load-truncated yes`)**:
  - In environments where Docker or the host PC may be terminated abruptly, the active `.incr.aof` file can end with a partial write. Setting `aof-load-truncated yes` allows Redis to automatically discard the damaged trailing fragment and boot immediately without blocking worker operations.
- **Memory Ceiling & Eviction**:
  - `maxmemory 96mb`: Caps Redis memory usage to fit low-resource deployments.
  - `maxmemory-policy allkeys-lru`: Evicts oldest idle keys under extreme load to prevent container Out-Of-Memory termination.

## 📊 Dynamic Worker Autoscaling

The `n8n-autoscaler` service monitors the BullMQ queue (`bull:jobs:wait`) inside Redis and dynamically adjusts worker replicas using `docker compose scale`.

### Key Environment Tuning

Modify these variables in `.env` to suit your production load:

```dotenv
# Replicas limits
MIN_REPLICAS=1
MAX_REPLICAS=2

# Thresholds (Queue depth)
SCALE_UP_QUEUE_THRESHOLD=5      # Scale up if queue has more than 5 waiting items
SCALE_DOWN_QUEUE_THRESHOLD=1    # Scale down if queue is empty or has <1 waiting items

# Cool-down configuration
POLLING_INTERVAL_SECONDS=10     # How often the autoscaler queries Redis
COOLDOWN_PERIOD_SECONDS=10      # Buffer time (seconds) to wait between scaling events to prevent thrashing
```

---

## 🛡️ Task Runner Concurrency & Isolation (n8n 2.0+)

n8n 2.0 offloads heavy JS and Python code executions to isolated sidecar runner containers (`n8n-worker-runner`).

### Configuration Settings
- `N8N_RUNNERS_MAX_CONCURRENCY`: Restricts the number of concurrent executions inside a single runner sidecar container (default: `5`).
- `N8N_RUNNERS_TASK_REQUEST_TIMEOUT`: Number of seconds (default: `120`) that n8n will wait for a task runner to pick up and process a queued code task before throwing a execution timeout error.
- `N8N_RUNNERS_AUTO_SHUTDOWN_TIMEOUT`: Set to `0` to keep the runner container running persistently, eliminating the cold-start delay for execution nodes.

---

## 🔒 Reverse Proxy & WebSockets (Nginx/Traefik)

If self-hosting n8n behind a reverse proxy (like Nginx, Apache, Traefik, or Caddy) to expose it over HTTPS, you **must** configure proxy support for WebSockets / Server-Sent Events (SSE) to prevent constant editor UI disconnects.

### Sample Nginx Configuration Block
Add this location block to your Nginx virtual host configuration:

```nginx
server {
    server_name n8n.yourdomain.com;

    location / {
        proxy_pass http://localhost:80; # Points to the n8n main server
        
        # Enable HTTP/1.1 for persistent connection support
        proxy_http_version 1.1;
        
        # Upgrade headers for WebSockets
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Disable proxy buffering to prevent SSE stream delays
        proxy_buffering off;
        
        # Set long read timeouts to keep persistent connections open
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

If you are experiencing constant disconnects behind a proxy, you can also force Server-Sent Events (SSE) as the push backend by setting this env var in `.env`:
```dotenv
N8N_PUSH_BACKEND=sse
```

---

## 💻 Low-Resource PC & Host Optimization (Windows / WSL2 / Docker)

When running the full production queue stack locally on a resource-constrained computer, performance issues are usually caused by **Docker/WSL2 RAM starvation** and **disk I/O bottlenecks** on Windows. Follow these steps to optimize your host PC:

### 1. Cap WSL2 Resource Usage (.wslconfig)
Docker Desktop on Windows runs inside a WSL2 virtual machine, which by default will consume up to 50% of your total PC RAM and lock CPU cores.
1. Open Windows Explorer and type `%USERPROFILE%` in the address bar (this points to your Windows home folder, e.g. `C:\Users\YourName\`).
2. Create a file named `.wslconfig` (make sure it doesn't end in `.txt`).
3. Copy the template from [wslconfig.txt](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/docs/wslconfig.txt) into it.
4. Open Windows PowerShell and shut down WSL2 to apply changes:
   ```powershell
   wsl --shutdown
   ```
5. Restart Docker Desktop.

### 2. Node.js Heap Optimization (Aggressive GC)
To prevent Node.js containers from exceeding their Docker RAM limits and crashing (or thrashing the host swap file), we have pre-configured `--max-old-space-size` memory heap limits in `docker-compose.yml`:
- **Main Server / Workers**: Capped at 768MB heap (inside 1024MB container limits).
- **Webhooks / Task Runners**: Capped at 384MB heap (inside 512MB/768MB container limits).
This forces Node.js to garbage-collect aggressively, keeping memory footprints low.

### 3. Disable Manual Execution DB Writes
Every manual workflow test run from the editor writes logs and binary history to PostgreSQL. Over time, this leads to heavy disk write operations that slow down your computer.
In `.env`, we set:
```dotenv
EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS=false
```
This stops manual editor executions from being stored permanently in the database, greatly improving disk I/O and saving disk space.

### 4. Ollama LLM Optimizations (Host-level)
If you are running Ollama locally on Windows for AI nodes, Ollama swaps models in and out of memory, causing long delays.
Set these Environment Variables in your Windows System Settings:
- `OLLAMA_MAX_LOADED_MODELS=2`: Allows both the LLM and the embedding model to reside in VRAM/RAM simultaneously.
- `OLLAMA_KEEP_ALIVE=1h`: Keeps models loaded in VRAM for 1 hour of inactivity, eliminating load times.
- `OLLAMA_NUM_PARALLEL=2`: Processes parallel requests efficiently.

