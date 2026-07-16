import json
import uvicorn
import urllib.request
import urllib.error
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
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

# Create a FastAPI app to wrap the MCP server and provide the Chat UI
app = FastAPI(title="n8n AI Chat UI")

class GenerateRequest(BaseModel):
    prompt: str

class ExportRequest(BaseModel):
    workflow: dict
    n8n_url: str
    api_key: str

@app.post("/api/generate")
async def api_generate(req: GenerateRequest):
    try:
        workflow_json = generate_workflow(req.prompt)
        if "error" in workflow_json:
            return {"success": False, "error": workflow_json["error"]}
        return {"success": True, "workflow": workflow_json}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/export")
async def api_export(req: ExportRequest):
    url = f"{req.n8n_url.rstrip('/')}/api/v1/workflows"
    
    headers = {
        'Content-Type': 'application/json',
        'X-N8N-API-KEY': req.api_key
    }
    
    request = urllib.request.Request(
        url,
        data=json.dumps(req.workflow).encode('utf-8'),
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
        
        <div class="mt-auto border-t border-slate-700 pt-4">
            <button onclick="openSettings()" class="flex items-center gap-2 w-full p-2 hover:bg-slate-700 rounded transition text-sm">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                n8n Settings
            </button>
        </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="flex-1 flex flex-col relative">
        <div id="chat-container" class="chat-container flex-1 w-full pb-8">
            
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
            <h2 class="text-xl font-bold mb-4">Export Settings</h2>
            <p class="text-sm text-slate-400 mb-4">Configure your n8n connection to automatically export workflows.</p>
            
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-1">n8n Host URL</label>
                    <input type="text" id="n8n-url" class="w-full bg-[#343541] border border-slate-600 rounded p-2 text-white" placeholder="http://localhost:5678">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">n8n API Key</label>
                    <input type="password" id="n8n-key" class="w-full bg-[#343541] border border-slate-600 rounded p-2 text-white" placeholder="n8n_api_...">
                    <p class="text-xs text-slate-400 mt-1">Generate this in n8n -> Settings -> n8n API</p>
                </div>
            </div>
            
            <div class="mt-6 flex justify-end gap-3">
                <button onclick="closeSettings()" class="px-4 py-2 rounded text-slate-300 hover:bg-slate-700">Cancel</button>
                <button onclick="saveSettings()" class="px-4 py-2 rounded bg-rose-600 hover:bg-rose-700 font-medium">Save</button>
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

    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
    <script>
        let currentWorkflowJson = null;
        let chatHistory = [];

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

        function saveHistory() {
            localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
        }

        function loadHistory() {
            const saved = localStorage.getItem('chatHistory');
            if (saved) {
                try {
                    chatHistory = JSON.parse(saved);
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
                } catch (e) {
                    console.error('Failed to parse history', e);
                }
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
                    currentWorkflowJson = workflowObj;
                    
                    html += `
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
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });
                const data = await res.json();
                
                document.getElementById(loadingId).remove();
                
                if (data.success && data.workflow) {
                    addMessage('bot', `<p>I have built the workflow based on your requirements. You can review the JSON below or export it directly.</p>`, data.workflow);
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
        };

        function openSettings() {
            document.getElementById('n8n-url').value = localStorage.getItem('n8nUrl') || 'http://localhost:5678';
            document.getElementById('n8n-key').value = localStorage.getItem('n8nKey') || '';
            document.getElementById('settings-modal').classList.add('active');
        }
        function closeSettings() {
            document.getElementById('settings-modal').classList.remove('active');
        }
        function saveSettings() {
            localStorage.setItem('n8nUrl', document.getElementById('n8n-url').value.trim());
            localStorage.setItem('n8nKey', document.getElementById('n8n-key').value.trim());
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
