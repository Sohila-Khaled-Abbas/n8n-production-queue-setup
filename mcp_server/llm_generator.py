import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import re

# Load .env from the parent directory (n8n root)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

def get_available_providers():
    providers = []
    if os.getenv("GEMINI_API_KEY"):
        providers.append("gemini")
    if os.getenv("HUGGINGFACE_API_TOKEN"):
        providers.append("huggingface")
    if os.getenv("OLLAMA_HOST"):
        providers.append("ollama")
    if os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_TOKEN"):
        providers.append("openrouter")
    return providers

def get_client_and_model(prompt: str, preferred_model: str = None, preferred_provider: str = None):
    """
    Selects the best available API and model based on user preference, prompt complexity
    and available environment keys.
    """
    providers = get_available_providers()
    if not providers:
        raise ValueError("No AI API keys found. Please set GEMINI_API_KEY, OPENROUTER_API_KEY, HUGGINGFACE_API_TOKEN, or OLLAMA_HOST in the .env file.")

    # Override with preferences if valid
    if preferred_provider in providers:
        if preferred_provider == "gemini":
            client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=os.getenv("GEMINI_API_KEY"),
            )
            return client, preferred_model or "gemini-2.5-flash"
            
        elif preferred_provider == "openrouter":
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
            )
            return client, preferred_model or "openrouter/free"
        
        elif preferred_provider == "ollama":
            ollama_host = os.getenv("OLLAMA_HOST", "127.0.0.1:11434")
            if ollama_host == "0.0.0.0" or "host.docker.internal" in ollama_host:
                ollama_host = "127.0.0.1:11434"
            if not ollama_host.startswith("http"):
                ollama_host = f"http://{ollama_host}"
            client = OpenAI(base_url=f"{ollama_host}/v1", api_key="ollama")
            
            # If no model is preferred, fetch available models dynamically
            if not preferred_model:
                import requests
                try:
                    res = requests.get(f"{ollama_host}/api/tags", timeout=2)
                    if res.status_code == 200:
                        models = res.json().get("models", [])
                        if models:
                            preferred_model = models[0]["name"]
                except Exception:
                    pass
            return client, preferred_model or "llama3.2:3b"

        elif preferred_provider == "huggingface":
            client = OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=os.getenv("HUGGINGFACE_API_TOKEN") or os.getenv("HF_ROUTER_API_KEY")
            )
            # Map the fictional model requested by the user to a highly capable real HF model
            actual_model = preferred_model or "Qwen/Qwen2.5-Coder-32B-Instruct"
            if actual_model == "openai/gpt-oss-120b":
                actual_model = "Qwen/Qwen2.5-Coder-32B-Instruct"
            return client, actual_model
            
        elif preferred_provider == "agentrouter":
            client = OpenAI(
                base_url=os.getenv("AGENTROUTER_URL", "https://agentrouter.org/v1"),
                api_key=os.getenv("AGENTROUTER_API_KEY"),
            )
            return client, preferred_model or "gpt-3.5-turbo"
            
        elif preferred_provider == "hf_router":
            client = OpenAI(
                base_url=os.getenv("HF_ROUTER_URL", "https://router.huggingface.co/v1"),
                api_key=os.getenv("HF_ROUTER_API_KEY"),
            )
            return client, preferred_model or "meta-llama/Meta-Llama-3-8B-Instruct"

    # Default logic if no valid preference
    if "gemini" in providers:
        client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        return client, "gemini-2.5-flash"

    if "openrouter" in providers:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        return client, "openai/gpt-4o-mini"

    if "ollama" in providers:
        ollama_host = os.getenv("OLLAMA_HOST").replace("host.docker.internal", "127.0.0.1")
        if not ollama_host.startswith("http"):
            ollama_host = f"http://{ollama_host}"
        
        # Try to find an available model dynamically
        model_name = "llama3.2:3b" # default fallback
        import requests
        try:
            res = requests.get(f"{ollama_host}/api/tags", timeout=2)
            if res.status_code == 200:
                models = res.json().get("models", [])
                if models:
                    model_names = [m["name"] for m in models]
                    if "llama3:latest" in model_names or "llama3" in model_names:
                        model_name = "llama3"
                    else:
                        model_name = model_names[0]
        except:
            pass
            
        client = OpenAI(base_url=f"{ollama_host}/v1", api_key="ollama")
        return client, model_name

    if "huggingface" in providers:
        client = OpenAI(
            base_url="https://api-inference.huggingface.co/v1/",
            api_key=os.getenv("HUGGINGFACE_API_TOKEN")
        )
        return client, "openai/gpt-oss-120b"

    raise ValueError("Failed to select a valid AI provider.")

from n8n_client import build_knowledge_index, build_credential_index

# Pre-load local n8n knowledge base to save context limits
# If API fails, we fallback to empty strings
KNOWLEDGE_INDEX = build_knowledge_index() or "(No local portfolio found from API)"
CREDENTIAL_INDEX = build_credential_index() or "(No local credentials found from API)"

def fetch_relevant_template(prompt: str) -> str:
    """Naive keyword extraction to find a community template"""
    import urllib.parse
    import requests
    stop_words = {'make', 'a', 'bot', 'that', 'reads', 'from', 'to', 'and', 'with', 'create', 'workflow', 'the', 'an', 'in', 'on', 'for', 'my', 'i', 'want', 'need', 'using'}
    words = [w for w in prompt.lower().replace(',', '').replace('.', '').split() if w not in stop_words and len(w) > 2]
    if not words: return ""
    query = urllib.parse.quote(' '.join(words[:2]))
    try:
        res = requests.get(f'https://api.n8n.io/api/templates/workflows?search={query}', timeout=3)
        if res.status_code == 200:
            data = res.json()
            if data.get('workflows'):
                w_id = data['workflows'][0]['id']
                w_res = requests.get(f'https://api.n8n.io/api/templates/workflows/{w_id}', timeout=3)
                if w_res.status_code == 200:
                    wf = w_res.json().get('workflow', {}).get('workflow', {})
                    # Clean up huge things like pinData to save context window
                    wf.pop('pinData', None)
                    return json.dumps(wf)
    except Exception:
        pass
def search_n8n_docs(query: str) -> str:
    """Search official n8n documentation via DuckDuckGo HTML"""
    import urllib.parse
    import urllib.request
    import re
    try:
        url = 'https://html.duckduckgo.com/html/'
        data = urllib.parse.urlencode({'q': f'site:docs.n8n.io {query}'}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
            snippets = re.findall(r'<a class="result__snippet[^>]+>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
            clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets]
            return '\n'.join(clean_snippets[:3]) if clean_snippets else 'No documentation found.'
    except Exception as e:
        return f"Error searching docs: {str(e)}"

def generate_workflow(messages: list, model_name: str = None, provider: str = None, custom_skills: str = None) -> dict:
    """
    Main entry point for conversational workflow generation.
    Takes a conversation history, uses the LLM, and extracts generated n8n JSON.
    """
    # Extract the last user message to determine model routing
    last_prompt = messages[-1]["content"] if messages else ""
    client, model = get_client_and_model(last_prompt, preferred_model=model_name, preferred_provider=provider)
    print(f"[llm_generator] Routing conversational request to model: {model}")
    template_context = ""
    fetched_template = fetch_relevant_template(last_prompt)
    if fetched_template:
        template_context += f"\n# N8N COMMUNITY TEMPLATE FOUNDATION\nThe user's request matches an official n8n community template. Use this as a strong foundation:\n```json\n{fetched_template}\n```\n"

    # Naive RAG documentation extraction based on keywords
    import urllib.parse
    stop_words = {'make', 'a', 'bot', 'that', 'reads', 'from', 'to', 'and', 'with', 'create', 'workflow', 'the', 'an', 'in', 'on', 'for', 'my', 'i', 'want', 'need', 'using'}
    doc_words = [w for w in last_prompt.lower().replace(',', '').replace('.', '').split() if w not in stop_words and len(w) > 2]
    if doc_words:
        docs = search_n8n_docs(' '.join(doc_words[:2]))
        if docs and docs != "No documentation found.":
            template_context += f"\n# RAG DOCUMENTATION (OFFICIAL N8N DOCS)\nHere are relevant documentation snippets to ensure you use correct node parameters:\n{docs}\n"

    skills_context = ""
    if custom_skills:
        skills_context = f"\n# GLOBAL AI SKILLS & INSTRUCTIONS\nThe user has provided the following custom instructions that you MUST obey:\n{custom_skills}\n"

    system_message = f"""You are an elite n8n Workflow Architect and Data Engineer. You are chatting interactively with the user.

# YOUR GOALS
1. **Chat and Suggest**: Converse naturally. Answer questions about n8n. Suggest workflow ideas based on the user's existing portfolio.
2. **Prompt Enhancing**: If the user asks for a simple workflow (e.g. "make a telegram bot"), silently enhance it using your engineering knowledge. Formulate a robust architecture (error handling, data mapping, database persistence) before building it.
3. **Build Workflows**: When the user explicitly or implicitly requests to build/generate a workflow, output a raw, valid n8n JSON object wrapped EXACTLY in ```json ... ``` blocks. 

# USER'S EXISTING N8N PORTFOLIO (FOR KNOWLEDGE & SUGGESTIONS)
{KNOWLEDGE_INDEX}
{template_context}
{skills_context}

# WORKFLOW GENERATION RULES (ONLY IF GENERATING A WORKFLOW)
If you decide to output a workflow:
1. **Chain of Thought**: You must first think step-by-step about the architecture, the nodes needed, and the data mapping. Output your thoughts inside a `<thought>` XML block BEFORE the JSON block.
2. **Data Mapping**: Use n8n expressions like `={{{{ $json.fieldName }}}}`.
3. **Node Types**: Use modern n8n nodes (e.g. `n8n-nodes-base.httpRequest`, `n8n-nodes-base.webhook`).
4. **JSON Output**: Output the JSON block wrapped in ```json ... ```.

# KNOWN CREDENTIALS
If the workflow requires any of these services, attach these EXACT credentials based on the user's active n8n instance:
{CREDENTIAL_INDEX}

# JSON STRUCTURE
```json
{{
  "name": "Generated Workflow",
  "nodes": [
    {{
      "parameters": {{}},
      "id": "generate-a-unique-uuid-here",
      "name": "HTTP Request",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [0, 0]
    }}
  ],
  "connections": {{
    "Previous Node Name": {{
      "main": [
        [
          {{
            "node": "Next Node Name",
            "type": "main",
            "index": 0
          }}
        ]
      ]
    }}
  }}
}}
```
CRITICAL: Ensure `connections` perfectly matches the `name` of the nodes."""

    api_messages = [{"role": "system", "content": system_message}]
    for msg in messages:
        api_messages.append({"role": msg["role"], "content": msg["content"]})

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=0.4
            )
            
            content = response.choices[0].message.content.strip()
            workflow_json = None
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            
            if json_match:
                try:
                    workflow_json = json.loads(json_match.group(1).strip())
                    
                    # Validate JSON structure
                    if "nodes" not in workflow_json or "connections" not in workflow_json:
                        error_msg = f"Your JSON is missing required 'nodes' or 'connections' arrays. Please fix it."
                        api_messages.append({"role": "assistant", "content": content})
                        api_messages.append({"role": "user", "content": error_msg})
                        print(f"[llm_generator] Validation failed on attempt {attempt+1}: {error_msg}")
                        continue # Retry

                    # If successful, clean the content
                    content = content.replace(json_match.group(0), "").strip()
                except Exception as e:
                    error_msg = f"Invalid JSON generated: {e}. Please ensure you output valid JSON."
                    api_messages.append({"role": "assistant", "content": content})
                    api_messages.append({"role": "user", "content": error_msg})
                    print(f"[llm_generator] JSON parse failed on attempt {attempt+1}: {e}")
                    continue # Retry

            # Format the conversational output nicely
            content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL).strip()
            if not content and workflow_json:
                content = "Here is the generated workflow based on your requirements:"

            return {"success": True, "message": content, "workflow": workflow_json}

        except Exception as e:
            # We catch connection errors and give a better message
            error_str = str(e).lower()
            if "connection" in error_str or "timeout" in error_str or "503" in error_str:
                print(f"[llm_generator] Connection error with model {model}: {e}")
                if attempt < max_retries - 1:
                    continue # Retry on connection errors
                return {"error": f"Failed to connect to the AI Provider ({model}). Please check your .env keys (like HUGGINGFACE_API_TOKEN, OPENROUTER_API_KEY) or ensure your local Ollama is running. Raw error: {str(e)}"}
            return {"error": f"Failed to process request: {str(e)}"}
            
    return {"error": "Failed to generate valid n8n JSON after 3 attempts. The model may be struggling with complex structures."}

if __name__ == "__main__":
    # Test script locally
    res = generate_workflow([{"role": "user", "content": "Create a simple workflow with a webhook trigger that sends an HTTP GET request to example.com"}])
    print(json.dumps(res, indent=2))
