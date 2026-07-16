# n8n MCP Workflow Generator

A FastMCP-based Server-Sent Events (SSE) server that allows n8n (or any MCP client) to automatically generate workflows from natural language prompts using LLMs.

## Features

- **Modern UI/UX Frontend**: A sleek HTML interface provides connection instructions and server status on the root URL.
- **Smart Routing**: Connects to the best available LLM provider (OpenRouter, HuggingFace, or Ollama).
- **FastMCP Powered**: Uses the official `fastmcp` SDK to expose the `create_n8n_workflow` tool seamlessly.

## Running the Server

Make sure you have installed the dependencies:

```bash
pip install -r requirements.txt
```

Start the server:

```bash
python server.py
```

The server will be available at `http://localhost:8000`. If you visit this in your browser, you'll see a modern UI detailing how to connect.

## Connecting to n8n

1. In n8n, navigate to **Settings** > **Model Context Protocol (MCP)**.
2. Click **Add Server**.
3. Set the Transport type to **SSE**.
4. Set the URL to:
   ```
   http://localhost:8000/sse
   ```
   *(Important: Ensure you include the `/sse` path!)*

Once connected, you can use the AI Agent node in n8n and enable the **`create_n8n_workflow`** tool.

## Environment Variables

Ensure the parent directory's `.env` file contains at least one of the following:
- `OPENROUTER_API_KEY` (Recommended for complex workflows)
- `HUGGINGFACE_API_TOKEN`
- `OLLAMA_HOST`
