import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastmcp import FastMCP
from llm_generator import generate_workflow

# Create the MCP Server
mcp = FastMCP("n8n-workflow-generator")

@mcp.tool()
async def create_n8n_workflow(prompt: str) -> str:
    """
    Generates a valid n8n JSON workflow based on a natural language prompt.
    The tool automatically selects the best available AI provider (HuggingFace, OpenRouter, or Ollama)
    from the environment variables and constructs the workflow.
    
    Args:
        prompt: A description of the desired n8n workflow. (e.g. "Create a workflow that triggers every hour, fetches data from a weather API, and sends an email.")
    """
    print(f"[Tool Call] create_n8n_workflow called with prompt: {prompt}")
    
    try:
        workflow_json = generate_workflow(prompt)
        
        if "error" in workflow_json:
            return f"Error generating workflow: {workflow_json['error']}"
            
        return json.dumps(workflow_json, indent=2)
        
    except Exception as e:
        return f"Unexpected error during workflow generation: {str(e)}"

# Create a FastAPI app to wrap the MCP server
app = FastAPI(title="n8n MCP Server UI")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Dynamically get the base URL to show the correct SSE endpoint
    base_url = str(request.base_url).rstrip('/')
    sse_url = f"{base_url}/sse"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>n8n MCP Workflow Generator</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <script>
            tailwind.config = {{
                theme: {{
                    extend: {{
                        fontFamily: {{ sans: ['Inter', 'sans-serif'] }},
                        colors: {{
                            brand: {{ 50: '#fff1f2', 100: '#ffe4e6', 500: '#f43f5e', 600: '#e11d48' }},
                            dark: {{ 800: '#1e293b', 900: '#0f172a' }}
                        }}
                    }}
                }}
            }}
            
            function copyToClipboard() {{
                const urlText = document.getElementById('sse-url').innerText;
                navigator.clipboard.writeText(urlText).then(() => {{
                    const btn = document.getElementById('copy-btn');
                    const originalHTML = btn.innerHTML;
                    btn.innerHTML = '<svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>';
                    setTimeout(() => {{ btn.innerHTML = originalHTML; }}, 2000);
                }});
            }}
        </script>
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            .glass {{
                background: rgba(30, 41, 59, 0.7);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            .gradient-text {{
                background: linear-gradient(to right, #f43f5e, #fb923c);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .blob {{
                position: absolute;
                filter: blur(80px);
                z-index: -1;
                opacity: 0.4;
            }}
        </style>
    </head>
    <body class="bg-dark-900 text-slate-200 min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
        
        <!-- Background Blobs -->
        <div class="blob bg-brand-600 w-96 h-96 rounded-full top-[-10%] left-[-10%]"></div>
        <div class="blob bg-purple-600 w-96 h-96 rounded-full bottom-[-10%] right-[-10%]"></div>
        
        <div class="glass max-w-3xl w-full rounded-2xl shadow-2xl p-8 md:p-12 relative z-10 transform transition-all hover:scale-[1.01] duration-500">
            <div class="flex items-center justify-between mb-8">
                <div>
                    <h1 class="text-3xl md:text-4xl font-bold tracking-tight mb-2 gradient-text">n8n Workflow Generator</h1>
                    <p class="text-slate-400 font-medium text-sm md:text-base">Model Context Protocol (MCP) Server</p>
                </div>
                <div class="flex items-center space-x-2 bg-dark-800/50 px-4 py-2 rounded-full border border-slate-700">
                    <span class="relative flex h-3 w-3">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                    <span class="text-green-400 text-sm font-semibold tracking-wide uppercase">Online</span>
                </div>
            </div>

            <div class="bg-dark-800/80 rounded-xl p-6 border border-slate-700/50 mb-8 shadow-inner">
                <h2 class="text-lg font-semibold text-white mb-4 flex items-center">
                    <svg class="w-5 h-5 mr-2 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
                    Connection URL
                </h2>
                <p class="text-sm text-slate-400 mb-3">Use this URL when configuring your MCP Server in n8n (Transport: SSE):</p>
                <div class="flex items-center justify-between bg-dark-900 rounded-lg p-3 border border-slate-700 group hover:border-brand-500/50 transition-colors">
                    <code id="sse-url" class="text-brand-400 font-mono text-sm sm:text-base truncate">{sse_url}</code>
                    <button id="copy-btn" onclick="copyToClipboard()" class="ml-4 p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-all focus:outline-none focus:ring-2 focus:ring-brand-500" title="Copy URL">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                    </button>
                </div>
            </div>

            <div class="mb-2">
                <h2 class="text-lg font-semibold text-white mb-4 flex items-center">
                    <svg class="w-5 h-5 mr-2 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                    Available Tools
                </h2>
                <div class="bg-dark-800/50 rounded-xl p-5 border border-slate-700/50 hover:bg-dark-800 transition-colors">
                    <div class="flex items-start">
                        <div class="flex-shrink-0 mt-1">
                            <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500/20 text-brand-400 border border-brand-500/30">
                                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                            </span>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-md font-medium text-white font-mono">create_n8n_workflow</h3>
                            <p class="mt-1 text-sm text-slate-400">Generates a valid n8n JSON workflow based on a natural language prompt using AI models.</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="mt-8 pt-6 border-t border-slate-700/50 text-center text-xs text-slate-500">
                Powered by <a href="https://gofastmcp.com/" target="_blank" class="text-brand-400 hover:underline">FastMCP</a> &bull; Connect with n8n over SSE
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Mount the FastMCP app at the root (it will handle /sse and /messages)
app.mount("/", mcp.http_app())

if __name__ == "__main__":
    print("Starting n8n Workflow Generator MCP Server on port 8000...")
    # Run the wrapped FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8000)
