# Infrastructure Blueprint

A clean, modern, simplified architecture diagram of the self-hosted **n8n AI Production Stack**, designed like a Draw.io blueprint.

## Diagram

### Modern Vector (SVG) Format
The SVG version supports infinite scaling and crisp lines. You can open it directly in your browser:
🔗 **[infographic.svg](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/docs/infographic.svg)**

### Image (PNG) Format
A high-resolution PNG format suitable for presentation slides and documentation pages:
🔗 **[infographic.png](file:///d:/courses/Data%20Science/Data%20Engineering/n8n/docs/infographic.png)**

---

## Architecture Flow Overview

1. **Client / External Access**: Web browsers and external webhooks access `n8n-main` through port `80`.
2. **n8n-main**: Handles editor traffic, manages scheduling, processes Webhook payloads, and brokers code tasks. When a workflow executes, it sends a job metadata payload to the Redis queue.
3. **Redis (Broker)**: Temporarily holds executing workflow tasks in a fast, Append-Only (AOF) persistent memory store.
4. **n8n-worker**: Scales horizontally. Replicas pull active tasks from the Redis queue, execute workflow logic, and pull/push state to the PostgreSQL database.
5. **PostgreSQL**: Stores persistent data: credentials, workflow history, user accounts, and execution results.
6. **Sidecar (Task Runners)**: The sandboxed environment executing custom Python and JS scripts isolated from core n8n logic.
7. **Ollama & Qdrant**: The AI layer. Prompts are routed locally to Ollama (leveraging your Nvidia GPU), and text search embedding vectors are stored and indexed in Qdrant for RAG-based workflows.
8. **n8n-init (One-Shot Provisioner)**: Runs briefly on stack startup to seed PostgreSQL with predefined workflow credentials securely, then exits.
