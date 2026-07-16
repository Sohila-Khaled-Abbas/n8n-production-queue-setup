import os
from dotenv import load_dotenv
load_dotenv()
import json
import uvicorn
import urllib.request
import urllib.error
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastmcp import FastMCP
from fastapi import Depends
from sqlalchemy.orm import Session
from llm_generator import generate_workflow
from database import init_db, get_db, ChatSession, ChatMessage

# Create the MCP Server
mcp = FastMCP("n8n-workflow-generator")

@mcp.tool()
async def create_n8n_workflow(prompt: str) -> str:
    """
    Generates a valid n8n JSON workflow based on a natural language prompt.
    The tool automatically selects the best available AI provider (HuggingFace, OpenRouter, or Ollama)
    from the environment variables and constructs the workflow.
    
    Args:
        prompt: A description of the desired n8n workflow.
    """
    print(f"[Tool Call] create_n8n_workflow called with prompt: {prompt}")
    
    try:
        workflow_json = generate_workflow(prompt)
        
        if "error" in workflow_json:
            return f"Error generating workflow: {workflow_json['error']}"
            
        return json.dumps(workflow_json, indent=2)
        
    except Exception as e:
        return f"Unexpected error during workflow generation: {str(e)}"

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

# Create a FastAPI app to wrap the MCP server and provide the Chat UI
app = FastAPI(title="n8n AI Chat UI", lifespan=lifespan)

class GenerateRequest(BaseModel):
    session_id: str
    messages: list
    custom_skills: str = None
    model_id: str = None
    provider: str = None

class ExportRequest(BaseModel):
    workflow: dict
    n8n_url: str
    api_key: str

@app.post("/api/generate")
async def api_generate(req: GenerateRequest, db: Session = Depends(get_db)):
    try:
        # Save user message
        if not req.messages:
            return {"success": False, "error": "No messages provided"}
            
        last_user_msg = req.messages[-1]
        
        # Create session if not exists
        db_session = db.query(ChatSession).filter(ChatSession.id == req.session_id).first()
        if not db_session:
            db_session = ChatSession(id=req.session_id)
            db.add(db_session)
            db.commit()

        user_db_msg = ChatMessage(session_id=req.session_id, role="user", content=last_user_msg["content"])
        db.add(user_db_msg)
        db.commit()

        # Generate response
        response = generate_workflow(req.messages, model_name=req.model_id, provider=req.provider, custom_skills=req.custom_skills)
        
        if "error" in response:
            return {"success": False, "error": response["error"]}
            
        # Save bot message
        workflow_str = json.dumps(response.get("workflow")) if response.get("workflow") else None
        bot_db_msg = ChatMessage(session_id=req.session_id, role="bot", content=response.get("message", ""), workflow_json=workflow_str)
        db.add(bot_db_msg)
        db.commit()

        return response
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/export")
async def api_export(req: ExportRequest):
    url = f"{req.n8n_url.rstrip('/')}/api/v1/workflows"
    
    headers = {
        'Content-Type': 'application/json',
        'X-N8N-API-KEY': req.api_key
    }
    
    # Remove read-only fields for n8n API
    wf_payload = req.workflow.copy()
    wf_payload.pop('active', None)
    wf_payload.pop('id', None)
    if 'settings' not in wf_payload:
        wf_payload['settings'] = {}
    
    request = urllib.request.Request(
        url,
        data=json.dumps(wf_payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode())
            return {"success": True, "result": result}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {"success": False, "error": f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/history/{session_id}")
async def api_get_history(session_id: str, db: Session = Depends(get_db)):
    try:
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
        history = []
        for msg in messages:
            workflow = None
            if msg.workflow_json:
                try:
                    workflow = json.loads(msg.workflow_json)
                except:
                    pass
            history.append({
                "role": msg.role,
                "content": msg.content,
                "workflowObj": workflow
            })
        return {"success": True, "history": history}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/templates")
async def api_get_templates(search: str = ""):
    try:
        url = f"https://api.n8n.io/api/templates/workflows?search={urllib.parse.quote(search)}&limit=10"
        request = urllib.request.Request(url, headers={'User-Agent': 'n8n-ai-assistant'})
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode())
            return {"success": True, "templates": result.get('workflows', [])}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/models")
async def get_models():
    """
    Dynamically fetches available models from the configured providers in .env
    """
    models = []
    
    # Check Ollama
    ollama_host = os.getenv("OLLAMA_HOST", "127.0.0.1:11434")
    if ollama_host == "0.0.0.0" or "host.docker.internal" in ollama_host:
        ollama_host = "127.0.0.1:11434"
    if not ollama_host.startswith("http"):
        ollama_host = f"http://{ollama_host}"
    try:
        res = requests.get(f"{ollama_host}/api/tags", timeout=2)
        if res.status_code == 200:
            ollama_models = res.json().get("models", [])
            for m in ollama_models:
                models.append({
                    "id": m["name"],
                    "name": f"Ollama: {m['name']}",
                    "provider": "ollama"
                })
    except Exception as e:
        print(f"Error fetching Ollama models: {e}")

    # Fetch models used in local n8n workflows
    try:
        import glob, json
        workflow_models = set()
        for path in glob.glob('d:/courses/Data Science/Data Engineering/n8n/workflows/*.json'):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for node in data.get('nodes', []):
                    params = node.get('parameters', {})
                    if params.get('model'): workflow_models.add(params['model'])
                    for k, v in params.items():
                        if 'model' in k.lower() and isinstance(v, str):
                            workflow_models.add(v)
        
        # Add workflow models if not already in the list
        existing_ids = [m['id'] for m in models]
        for wm in workflow_models:
            if wm not in existing_ids:
                models.append({
                    "id": wm,
                    "name": f"Workflow Extracted: {wm}",
                    "provider": "ollama" if ":" in wm else "huggingface"
                })
    except Exception as e:
        print(f"Error fetching workflow models: {e}")

    # Check OpenRouter
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            res = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {openrouter_key}"}, timeout=5)
            if res.status_code == 200:
                or_models = res.json().get("data", [])
                for m in or_models:
                    pricing = m.get('pricing', {})
                    if ":free" in m["id"].lower() or pricing.get('prompt') == "0" or pricing.get('prompt') == 0:
                        models.append({
                            "id": m["id"],
                            "name": f"OpenRouter: {m.get('name', m['id'])}",
                            "provider": "openrouter"
                        })
        except Exception as e:
            print(f"Error fetching OpenRouter models: {e}")

    # Check AgentRouter (OpenAI Compatible)
    agentrouter_key = os.getenv("AGENTROUTER_API_KEY")
    agentrouter_url = os.getenv("AGENTROUTER_URL")
    if agentrouter_key and agentrouter_url:
        try:
            res = requests.get(f"{agentrouter_url}/models", headers={"Authorization": f"Bearer {agentrouter_key}"}, timeout=3)
            if res.status_code == 200:
                ar_models = res.json().get("data", [])
                for m in ar_models:
                    models.append({
                        "id": m["id"],
                        "name": f"AgentRouter: {m.get('id')}",
                        "provider": "agentrouter"
                    })
        except Exception as e:
            print(f"Error fetching AgentRouter models: {e}")

    # Check HF Router (OpenAI Compatible)
    hf_router_key = os.getenv("HF_ROUTER_API_KEY")
    hf_router_url = os.getenv("HF_ROUTER_URL")
    if hf_router_key and hf_router_url:
        try:
            res = requests.get(f"{hf_router_url}/models", headers={"Authorization": f"Bearer {hf_router_key}"}, timeout=3)
            if res.status_code == 200:
                hfr_models = res.json().get("data", [])
                for m in hfr_models:
                    models.append({
                        "id": m["id"],
                        "name": f"HF Router: {m.get('id')}",
                        "provider": "hf_router"
                    })
        except Exception as e:
            print(f"Error fetching HF Router models: {e}")

    # Check HuggingFace Serverless API (Fallback static models)
    hf_key = os.getenv("HUGGINGFACE_API_TOKEN")
    if hf_key:
        models.append({"id": "openai/gpt-oss-120b", "name": "HF: openai/gpt-oss-120b", "provider": "huggingface"})
        models.append({"id": "meta-llama/Meta-Llama-3-8B-Instruct", "name": "HF: Llama-3-8B-Instruct", "provider": "huggingface"})
        models.append({"id": "mistralai/Mistral-7B-Instruct-v0.2", "name": "HF: Mistral-7B-Instruct", "provider": "huggingface"})
        models.append({"id": "Qwen/Qwen2.5-7B-Instruct", "name": "HF: Qwen-2.5-7B", "provider": "huggingface"})
        models.append({"id": "Qwen/Qwen2.5-Coder-32B-Instruct", "name": "HF: Qwen-Coder-32B", "provider": "huggingface"})
        
    # Check Gemini (Antigravity Models)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        models.append({"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini"})
        models.append({"id": "gemini-exp-1206", "name": "Gemini Exp 1206", "provider": "gemini"})
        models.append({"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "gemini"})

    return {"success": True, "models": models}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    html_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>n8n AI Workflow Generator</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <style>
        body { background-color: #343541; color: #ececf1; }
        .sidebar { background-color: #202123; }
        .chat-container { height: calc(100vh - 120px); overflow-y: auto; }
        .message-bot { background-color: #444654; }
        .message-user { background-color: #343541; }
        .input-box { background-color: #40414f; border: 1px solid #565869; }
        
        /* Modal */
        .modal { display: none; background: rgba(0,0,0,0.6); }
        .modal.active { display: flex; }
    </style>
</head>
<body class="flex h-screen overflow-hidden">
    
    <!-- Sidebar -->
    <aside class="sidebar w-64 flex-shrink-0 flex flex-col p-4">
        <button onclick="newChat()" class="flex items-center gap-2 border border-slate-600 rounded-md p-3 hover:bg-slate-700 transition">
            <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" class="h-4 w-4" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            New Workflow
        </button>
        
        <div class="flex-1 mt-6">
            <div class="text-xs text-slate-500 mb-3 font-semibold uppercase">History</div>
            <div id="history-list" class="space-y-2"></div>
        </div>
        
        <div class="mt-auto border-t border-slate-700 pt-4 flex flex-col gap-2">
            <button onclick="openTemplates()" class="flex items-center gap-2 w-full p-2 hover:bg-slate-700 rounded transition text-sm text-green-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                Community Templates
            </button>
            <button onclick="clearChat()" class="flex items-center gap-2 w-full p-2 hover:bg-slate-700 rounded transition text-sm text-red-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                Clear Chat History
            </button>
            <button onclick="openSettings()" class="flex items-center gap-2 w-full p-2 hover:bg-slate-700 rounded transition text-sm">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                n8n Settings
            </button>
        </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="flex-1 flex flex-col relative">
        <header class="h-14 border-b border-slate-700 flex items-center justify-end px-6 bg-[#343541]">
            <select id="model-select" class="bg-[#202123] border border-slate-600 rounded p-1.5 text-sm text-slate-200 focus:outline-none">
                <option value="">Loading Models...</option>
            </select>
        </header>
        <div id="chat-container" class="chat-container flex-1 w-full pb-36">
            
            <div class="message-bot border-b border-black/10 text-gray-100">
                <div class="max-w-4xl mx-auto flex p-6 gap-6 text-base">
                    <div class="w-8 h-8 rounded-sm bg-rose-600 flex items-center justify-center flex-shrink-0 font-bold">AI</div>
                    <div class="flex-1">
                        <p>Hello! I am your AI n8n Workflow Architect.</p>
                        <p class="mt-2 text-slate-300">Describe the automation you want to build (e.g., "A workflow that watches a Telegram channel and sends new messages to Google Sheets"), and I will generate the JSON for you!</p>
                    </div>
                </div>
            </div>
            
        </div>
        
        <!-- Input Area -->
        <div class="absolute bottom-0 left-0 w-full bg-gradient-to-t from-[#343541] via-[#343541] to-transparent pt-6 pb-6 px-4">
            <div class="max-w-3xl mx-auto relative flex items-center">
                <textarea id="prompt-input" class="input-box w-full rounded-xl py-4 pl-4 pr-12 text-white focus:outline-none focus:ring-1 focus:ring-slate-500 shadow-md resize-none" rows="1" placeholder="Describe your workflow..." onkeydown="handleEnter(event)"></textarea>
                <button onclick="sendPrompt()" id="send-btn" class="absolute right-3 p-2 text-slate-400 hover:text-white rounded-md transition disabled:opacity-50">
                    <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" xmlns="http://www.w3.org/2000/svg"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                </button>
            </div>
            <div class="text-xs text-center text-slate-400 mt-3">AI models can make mistakes. Always verify workflows before activating them in production.</div>
        </div>
    </main>

    <!-- Settings Modal -->
    <div id="settings-modal" class="modal fixed inset-0 z-50 items-center justify-center">
        <div class="bg-[#202123] rounded-xl border border-slate-600 w-full max-w-md p-6 shadow-2xl">
            <h2 class="text-xl font-bold mb-4">Settings</h2>
            <p class="text-sm text-slate-400 mb-4">Configure your n8n connection and AI instructions.</p>
            
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-1">n8n Host URL</label>
                    <input type="text" id="n8n-url" class="w-full bg-[#343541] border border-slate-600 rounded p-2 text-white" value="https://tightrope-large-petty.ngrok-free.dev" placeholder="http://localhost:80">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">n8n API Key</label>
                    <input type="password" id="n8n-key" class="w-full bg-[#343541] border border-slate-600 rounded p-2 text-white" placeholder="n8n_api_...">
                    <p class="text-xs text-slate-400 mt-1">Generate this in n8n -> Settings -> n8n API</p>
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Global AI Skills & Instructions</label>
                    <textarea id="n8n-skills" rows="3" class="w-full bg-[#343541] border border-slate-600 rounded p-2 text-white text-sm" placeholder="e.g., 'Always use internal.api.com for HTTP nodes', 'Always add an Error Trigger'"></textarea>
                    <p class="text-xs text-slate-400 mt-1">These custom rules will be sent to the AI with every prompt.</p>
                </div>
            </div>
            
            <div class="mt-6 flex justify-end gap-3">
                <button onclick="closeSettings()" class="px-4 py-2 rounded text-slate-300 hover:bg-slate-700">Cancel</button>
                <button onclick="saveSettings()" class="px-4 py-2 rounded bg-rose-600 hover:bg-rose-700 font-medium">Save Settings</button>
            </div>
        </div>
    </div>

    <!-- Export Modal (Success/Error) -->
    <div id="alert-modal" class="modal fixed inset-0 z-50 items-center justify-center">
        <div class="bg-[#202123] rounded-xl border border-slate-600 w-full max-w-sm p-6 shadow-2xl text-center">
            <h2 id="alert-title" class="text-xl font-bold mb-2">Notice</h2>
            <p id="alert-msg" class="text-slate-300 mb-6"></p>
            <button onclick="closeAlert()" class="px-6 py-2 rounded bg-rose-600 hover:bg-rose-700 font-medium w-full">Close</button>
        </div>
    </div>

    <!-- Templates Modal -->
    <div id="templates-modal" class="modal fixed inset-0 z-50 items-center justify-center">
        <div class="bg-[#202123] rounded-xl border border-slate-600 w-full max-w-2xl p-6 shadow-2xl flex flex-col max-h-[80vh]">
            <h2 class="text-xl font-bold mb-4">Search n8n Community Templates</h2>
            <div class="flex gap-2 mb-4">
                <input type="text" id="template-search" class="flex-1 bg-[#343541] border border-slate-600 rounded p-2 text-white" placeholder="e.g. Telegram, Google Sheets, Notion...">
                <button onclick="searchTemplates()" class="px-4 py-2 rounded bg-rose-600 hover:bg-rose-700 font-medium">Search</button>
            </div>
            <div id="templates-results" class="flex-1 overflow-y-auto space-y-3 mb-4"></div>
            <div class="mt-auto flex justify-end gap-3 pt-4 border-t border-slate-700">
                <button onclick="closeTemplates()" class="px-4 py-2 rounded text-slate-300 hover:bg-slate-700">Close</button>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
    <script>
        let currentWorkflowJson = null;
        let chatHistory = [];

        function clearChat() {
            if (confirm("Are you sure you want to clear your chat history?")) {
                sessionId = 'sess_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('chatSessionId', sessionId);
                newChat();
            }
        }

        function openTemplates() {
            document.getElementById('templates-modal').classList.add('active');
        }

        function closeTemplates() {
            document.getElementById('templates-modal').classList.remove('active');
        }

        async function searchTemplates() {
            const query = document.getElementById('template-search').value;
            const resultsDiv = document.getElementById('templates-results');
            resultsDiv.innerHTML = '<div class="text-center text-slate-400 py-4">Searching...</div>';
            try {
                const res = await fetch(`/api/templates?search=${encodeURIComponent(query)}`);
                const data = await res.json();
                if (data.success && data.templates.length > 0) {
                    resultsDiv.innerHTML = data.templates.map(t => `
                        <div class="p-3 border border-slate-600 rounded hover:border-rose-500 bg-[#343541]">
                            <h3 class="font-bold mb-1">${t.name}</h3>
                            <p class="text-sm text-slate-300 mb-3">${t.description ? t.description.substring(0, 100) + '...' : 'No description'}</p>
                            <button onclick='useTemplate(${JSON.stringify(t)})' class="px-3 py-1 bg-slate-700 hover:bg-rose-600 text-sm rounded transition">Load into Chat</button>
                        </div>
                    `).join('');
                } else {
                    resultsDiv.innerHTML = '<div class="text-center text-slate-400 py-4">No templates found.</div>';
                }
            } catch(e) {
                resultsDiv.innerHTML = '<div class="text-center text-red-400 py-4">Error fetching templates.</div>';
            }
        }

        function useTemplate(template) {
            closeTemplates();
            // Just ask the AI to explain and adapt the template
            const prompt = `I found this community template: "${template.name}".

Description: ${template.description}

Please help me adapt it for my needs! Here is the JSON:
\`\`\`json
${JSON.stringify(template.workflow || {})}
\`\`\``;
            document.getElementById('prompt-input').value = prompt;
            sendPrompt();
        }

        // Auto-resize textarea
        const tx = document.getElementById('prompt-input');
        tx.setAttribute('style', 'height:' + (tx.scrollHeight) + 'px;overflow-y:hidden;');
        tx.addEventListener("input", OnInput, false);

        function OnInput() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        }

        function handleEnter(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendPrompt();
            }
        }

        function scrollToBottom() {
            const container = document.getElementById('chat-container');
            container.scrollTop = container.scrollHeight;
        }

        let sessionId = localStorage.getItem('chatSessionId');
        if (!sessionId) {
            sessionId = 'sess_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chatSessionId', sessionId);
        }

        function saveHistory() {
            // History is saved on the server now during /api/generate
            // We just keep the local array for fast UI rendering
        }

        async function loadHistory() {
            try {
                const res = await fetch(`/api/history/${sessionId}`);
                const data = await res.json();
                if (data.success && data.history.length > 0) {
                    chatHistory = data.history;
                    // Clear default welcome message
                    document.getElementById('chat-container').innerHTML = '';
                    
                    const histList = document.getElementById('history-list');
                    histList.innerHTML = '';
                    
                    // Re-render all messages
                    chatHistory.forEach(msg => {
                        renderMessageHTML(msg.role, msg.content, msg.workflowObj);
                        if (msg.role === 'user') {
                            histList.innerHTML = `<div class="p-2 text-sm text-slate-300 hover:bg-slate-700 rounded cursor-pointer truncate">${msg.content}</div>` + histList.innerHTML;
                        }
                    });
                    scrollToBottom();
                }
            } catch (e) {
                console.error('Failed to load history from server', e);
            }
        }

        function renderMessageHTML(role, content, workflowObj = null) {
            const container = document.getElementById('chat-container');
            const div = document.createElement('div');
            
            if (role === 'user') {
                div.className = 'message-user border-b border-black/10';
                div.innerHTML = `
                <div class="max-w-4xl mx-auto flex p-6 gap-6 text-base">
                    <div class="w-8 h-8 rounded-sm bg-slate-600 flex items-center justify-center flex-shrink-0 font-bold">U</div>
                    <div class="flex-1 whitespace-pre-wrap">${content}</div>
                </div>`;
            } else {
                div.className = 'message-bot border-b border-black/10 text-gray-100';
                let html = `
                <div class="max-w-4xl mx-auto flex p-6 gap-6 text-base">
                    <div class="w-8 h-8 rounded-sm bg-rose-600 flex items-center justify-center flex-shrink-0 font-bold">AI</div>
                    <div class="flex-1">
                        <div class="prose prose-invert max-w-none">${content}</div>`;
                
                if (workflowObj) {
                    const jsonStr = JSON.stringify(workflowObj, null, 2);
                    
                    // Workflow Diffing Logic
                    let diffHtml = "";
                    if (currentWorkflowJson && currentWorkflowJson.nodes && workflowObj.nodes) {
                        const oldNodes = currentWorkflowJson.nodes;
                        const newNodes = workflowObj.nodes;
                        const added = newNodes.filter(n => !oldNodes.find(o => o.name === n.name));
                        const removed = oldNodes.filter(o => !newNodes.find(n => n.name === o.name));
                        const modified = newNodes.filter(n => {
                            const old = oldNodes.find(o => o.name === n.name);
                            return old && JSON.stringify(old.parameters) !== JSON.stringify(n.parameters);
                        });
                        
                        if (added.length > 0 || removed.length > 0 || modified.length > 0) {
                            diffHtml = `<div class="mt-4 p-3 bg-slate-800 rounded-lg border border-slate-700 text-sm">
                                <h4 class="font-bold text-slate-300 mb-2 border-b border-slate-700 pb-1">🔍 Version Control Diff</h4>
                                <ul class="space-y-1">`;
                            added.forEach(n => diffHtml += `<li class="text-green-400">🟩 <b>Added:</b> ${n.name} (${n.type})</li>`);
                            removed.forEach(n => diffHtml += `<li class="text-red-400">🟥 <b>Removed:</b> ${n.name}</li>`);
                            modified.forEach(n => diffHtml += `<li class="text-yellow-400">🟨 <b>Modified:</b> ${n.name} parameters updated</li>`);
                            diffHtml += `</ul></div>`;
                        }
                    }
                    
                    currentWorkflowJson = workflowObj;
                    
                    html += diffHtml + `
                        <div class="mt-4 bg-black rounded-lg overflow-hidden border border-slate-700">
                            <div class="flex justify-between items-center px-4 py-2 bg-slate-800 text-xs font-mono border-b border-slate-700">
                                <span>workflow.json</span>
                                <button onclick="exportWorkflow()" class="bg-rose-600 hover:bg-rose-500 text-white px-3 py-1 rounded shadow flex items-center gap-1 transition">
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                                    Export to n8n
                                </button>
                            </div>
                            <pre class="m-0 p-4 max-h-96 overflow-y-auto"><code class="language-json">${jsonStr.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>
                        </div>
                    `;

                    // Check for webhooks
                    let webhooks = [];
                    if (workflowObj.nodes && Array.isArray(workflowObj.nodes)) {
                        webhooks = workflowObj.nodes.filter(n => n.type === 'n8n-nodes-base.webhook');
                    }
                    if (webhooks.length > 0) {
                        const baseUrl = localStorage.getItem('n8nUrl') || 'http://localhost:80';
                        webhooks.forEach(wh => {
                            const path = wh.parameters?.path || 'your-webhook-path';
                            const method = wh.parameters?.httpMethod || 'GET';
                            html += `
                            <div class="mt-4 bg-slate-800 rounded-lg overflow-hidden border border-slate-700 p-4">
                                <h4 class="text-sm font-bold text-rose-400 mb-2">⚡ Webhook Detected: ${wh.name || 'Webhook'}</h4>
                                <p class="text-xs text-slate-400 mb-2">You can trigger this webhook using the following curl command after exporting:</p>
                                <pre class="bg-black p-3 rounded text-xs font-mono text-green-400 overflow-x-auto">curl -X ${method} ${baseUrl}/webhook-test/${path}</pre>
                            </div>
                            `;
                        });
                    }
                }
                
                html += `</div></div>`;
                div.innerHTML = html;
            }
            
            container.appendChild(div);
            if (workflowObj) Prism.highlightAllUnder(div);
            scrollToBottom();
        }

        function addMessage(role, content, workflowObj = null) {
            chatHistory.push({ role, content, workflowObj });
            saveHistory();
            renderMessageHTML(role, content, workflowObj);
        }

        async function sendPrompt() {
            const input = document.getElementById('prompt-input');
            const btn = document.getElementById('send-btn');
            const prompt = input.value.trim();
            if (!prompt) return;

            input.value = '';
            input.style.height = 'auto';
            input.disabled = true;
            btn.disabled = true;

            addMessage('user', prompt);
            
            // Add to history sidebar
            const histList = document.getElementById('history-list');
            histList.innerHTML = `<div class="p-2 text-sm text-slate-300 hover:bg-slate-700 rounded cursor-pointer truncate">${prompt}</div>` + histList.innerHTML;
            
            // Add loading indicator
            const loadingId = 'loading-' + Date.now();
            const container = document.getElementById('chat-container');
            const loadingDiv = document.createElement('div');
            loadingDiv.id = loadingId;
            loadingDiv.className = 'message-bot border-b border-black/10 text-gray-100';
            loadingDiv.innerHTML = `
                <div class="max-w-4xl mx-auto flex p-6 gap-6 text-base">
                    <div class="w-8 h-8 rounded-sm bg-rose-600 flex items-center justify-center flex-shrink-0 font-bold animate-pulse">AI</div>
                    <div class="flex-1 flex items-center text-slate-400">
                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-rose-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                        Designing workflow structure...
                    </div>
                </div>`;
            container.appendChild(loadingDiv);
            scrollToBottom();

            try {
                const selectedModelIdx = document.getElementById('model-select').value;
                let modelParams = {};
                if (selectedModelIdx !== "" && availableModels[selectedModelIdx]) {
                    modelParams = {
                        model_id: availableModels[selectedModelIdx].id,
                        provider: availableModels[selectedModelIdx].provider
                    };
                }

                // Send the entire chat history so the AI has context
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        session_id: sessionId, 
                        messages: chatHistory,
                        custom_skills: localStorage.getItem('n8n_skills') || '',
                        ...modelParams
                    })
                });
                const data = await res.json();
                
                document.getElementById(loadingId).remove();
                
                if (data.success) {
                    addMessage('bot', `<p>${data.message.replace(/\n/g, '<br>')}</p>`, data.workflow);
                } else {
                    addMessage('bot', `<p class="text-red-400">Error: ${data.error}</p>`);
                }
            } catch (err) {
                document.getElementById(loadingId).remove();
                addMessage('bot', `<p class="text-red-400">Connection error: ${err.message}</p>`);
            }

            input.disabled = false;
            btn.disabled = false;
            input.focus();
        }

        function newChat() {
            chatHistory = [];
            saveHistory();
            currentWorkflowJson = null;
            document.getElementById('history-list').innerHTML = '';
            document.getElementById('chat-container').innerHTML = `
            <div class="message-bot border-b border-black/10 text-gray-100">
                <div class="max-w-4xl mx-auto flex p-6 gap-6 text-base">
                    <div class="w-8 h-8 rounded-sm bg-rose-600 flex items-center justify-center flex-shrink-0 font-bold">AI</div>
                    <div class="flex-1">
                        <p>Hello! I am your AI n8n Workflow Architect.</p>
                        <p class="mt-2 text-slate-300">Describe the automation you want to build (e.g., "A workflow that watches a Telegram channel and sends new messages to Google Sheets"), and I will generate the JSON for you!</p>
                    </div>
                </div>
            </div>`;
        }

        // Initialize on load
        window.onload = function() {
            loadHistory();
            loadModels();
        };

        let availableModels = [];
        async function loadModels() {
            try {
                const select = document.getElementById('model-select');
                const res = await fetch('/api/models');
                const data = await res.json();
                if (data.success && data.models.length > 0) {
                    availableModels = data.models;
                    select.innerHTML = '';
                    let foundMain = -1;
                    data.models.forEach((m, idx) => {
                        const opt = document.createElement('option');
                        opt.value = idx;
                        opt.textContent = m.name;
                        select.appendChild(opt);
                        if (m.id === 'openai/gpt-oss-120b') {
                            foundMain = idx;
                        }
                    });
                    if (foundMain !== -1) {
                        select.value = foundMain;
                    }
                } else {
                    select.innerHTML = '<option value="">No models available</option>';
                }
            } catch (e) {
                console.error('Failed to load models', e);
                document.getElementById('model-select').innerHTML = '<option value="">Error loading models</option>';
            }
        }

        function openSettings() {
            document.getElementById('n8n-url').value = localStorage.getItem('n8nUrl') || 'https://tightrope-large-petty.ngrok-free.dev';
            document.getElementById('n8n-key').value = localStorage.getItem('n8nKey') || '';
            document.getElementById('n8n-skills').value = localStorage.getItem('n8n_skills') || '';
            document.getElementById('settings-modal').classList.add('active');
        }
        function closeSettings() {
            document.getElementById('settings-modal').classList.remove('active');
        }
        function saveSettings() {
            localStorage.setItem('n8nUrl', document.getElementById('n8n-url').value.trim());
            localStorage.setItem('n8nKey', document.getElementById('n8n-key').value.trim());
            localStorage.setItem('n8n_skills', document.getElementById('n8n-skills').value.trim());
            closeSettings();
        }

        function showAlert(title, msg) {
            document.getElementById('alert-title').innerText = title;
            document.getElementById('alert-msg').innerText = msg;
            document.getElementById('alert-modal').classList.add('active');
        }
        function closeAlert() {
            document.getElementById('alert-modal').classList.remove('active');
        }

        async function exportWorkflow() {
            if (!currentWorkflowJson) return;
            
            const n8nUrl = localStorage.getItem('n8nUrl');
            const n8nKey = localStorage.getItem('n8nKey');
            
            if (!n8nUrl || !n8nKey) {
                openSettings();
                return;
            }
            
            try {
                const res = await fetch('/api/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        workflow: currentWorkflowJson,
                        n8n_url: n8nUrl,
                        api_key: n8nKey
                    })
                });
                
                const data = await res.json();
                if (data.success) {
                    showAlert("Success!", `Workflow successfully exported to n8n! ID: ${data.result.id}`);
                } else {
                    showAlert("Export Failed", data.error || "Unknown error occurred.");
                }
            } catch (err) {
                showAlert("Connection Error", "Could not reach the server to export the workflow.");
            }
        }
    </script>
</body>
</html>'''
    return HTMLResponse(content=html_content)

# Mount the FastMCP app at the root (it will handle /sse and /messages)
# NOTE: mounting must be done *after* our own routes to avoid shadowing root
app.mount("/mcp", mcp.http_app())

if __name__ == "__main__":
    print("Starting n8n Workflow Generator Server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
