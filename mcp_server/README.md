# n8n MCP Workflow Generator

A FastMCP-based Server-Sent Events (SSE) server and standalone **ChatGPT-style Web Application** that allows you to automatically generate n8n workflows from natural language prompts using LLMs.

## Features

- **Standalone AI Chat UI**: The root URL serves a complete ChatGPT-like interface where you can chat with the AI to design your workflows.
- **1-Click n8n Export**: The web UI connects directly to your n8n instance via the REST API (`/api/v1/workflows`) to automatically push generated workflows with a single click.
- **Smart Routing**: Connects to the best available LLM provider (OpenRouter, HuggingFace, or Ollama) using `llm_generator.py`.
- **FastMCP Powered**: Still exposes the `create_n8n_workflow` tool seamlessly via SSE for traditional MCP clients.

## Running the Server

Make sure you have installed the dependencies:

```bash
pip install -r requirements.txt
```

Start the server:

```bash
python server.py
```

The server will be available at `http://localhost:8000`. If you visit this in your browser, you'll be greeted by the AI Chat Interface!

## Using the Chat Interface

1. Open `http://localhost:8000` in your web browser.
2. Click **n8n Settings** in the bottom-left corner.
3. Set your **n8n Host URL** (e.g., `http://localhost` if running locally via docker).
4. Paste your **n8n API Key** (generate this in n8n -> Settings -> n8n API).
5. Describe your workflow in the chat. When the AI generates the JSON, click **Export to n8n** to instantly deploy it!

## Connecting to n8n via MCP (Optional)

If you still want to use the MCP Server directly inside an n8n workflow using the "Model Context Protocol" Tool node:

1. In the n8n workflow canvas, add an **MCP Tool** node.
2. Set the Transport type to **SSE**.
3. Set the URL to:
   ```
   http://host.docker.internal:8000/mcp/sse
   ```
   *(Important: Ensure you include the `/mcp/sse` path!)*

## Environment Variables

Ensure the parent directory's `.env` file contains at least one of the following:
- `OPENROUTER_API_KEY` (Recommended for complex workflows)
- `HUGGINGFACE_API_TOKEN`
- `OLLAMA_HOST`
