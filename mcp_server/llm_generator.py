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
    if os.getenv("HUGGINGFACE_API_TOKEN"):
        providers.append("huggingface")
    if os.getenv("OLLAMA_HOST"):
        providers.append("ollama")
    if os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_TOKEN"):
        providers.append("openrouter")
    return providers

def get_client_and_model(prompt: str):
    """
    Selects the best available API and model based on prompt complexity
    and available environment keys.
    """
    providers = get_available_providers()
    if not providers:
        raise ValueError("No AI API keys found. Please set OPENROUTER_API_KEY, HUGGINGFACE_API_TOKEN, or OLLAMA_HOST in the .env file.")

    if "openrouter" in providers:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        return client, "anthropic/claude-3.5-sonnet:beta"

    if "huggingface" in providers:
        client = OpenAI(
            base_url="https://api-inference.huggingface.co/v1/",
            api_key=os.getenv("HUGGINGFACE_API_TOKEN")
        )
        # Using a solid code generation model on HF
        return client, "meta-llama/Meta-Llama-3-8B-Instruct"

    if "ollama" in providers:
        ollama_host = os.getenv("OLLAMA_HOST").replace("host.docker.internal", "localhost")
        if not ollama_host.startswith("http"):
            ollama_host = f"http://{ollama_host}"
        client = OpenAI(base_url=f"{ollama_host}/v1", api_key="ollama")
        return client, "llama3"

    raise ValueError("Failed to select a valid AI provider.")

# Pre-load local n8n knowledge base to save context limits
KNOWLEDGE_INDEX = ""
try:
    docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "data.json")
    if os.path.exists(docs_path):
        with open(docs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            workflows = data.get("workflows", [])
            lines = []
            for wf in workflows:
                name = wf.get("name", "Unknown Workflow")
                desc = wf.get("description") or "No description"
                tags = [t.get("name") for t in wf.get("tags", [])]
                lines.append(f"- {name}: {desc} (Tags: {', '.join(tags)})")
            
            KNOWLEDGE_INDEX = "\n".join(lines[:100]) # limit to 100 to save tokens
except Exception as e:
    print(f"[llm_generator] Warning: Failed to load local knowledge index from docs/data.json: {e}")


def generate_workflow(messages: list) -> dict:
    """
    Generates a conversational response and an optional n8n JSON workflow based on the chat history.
    """
    # Extract the last user message to determine model routing
    last_prompt = messages[-1]["content"] if messages else ""
    client, model = get_client_and_model(last_prompt)
    print(f"[llm_generator] Routing conversational request to model: {model}")

    system_message = f"""You are an elite n8n Workflow Architect and Data Engineer. You are chatting interactively with the user.

# YOUR GOALS
1. **Chat and Suggest**: Converse naturally. Answer questions about n8n. Suggest workflow ideas based on the user's existing portfolio.
2. **Prompt Enhancing**: If the user asks for a simple workflow (e.g. "make a telegram bot"), silently enhance it using your engineering knowledge. Formulate a robust architecture (error handling, data mapping, database persistence) before building it.
3. **Build Workflows**: When the user explicitly or implicitly requests to build/generate a workflow, output a raw, valid n8n JSON object wrapped EXACTLY in ```json ... ``` blocks. 

# USER'S EXISTING N8N PORTFOLIO (FOR KNOWLEDGE & SUGGESTIONS)
{KNOWLEDGE_INDEX if KNOWLEDGE_INDEX else "(No local portfolio found)"}

# WORKFLOW GENERATION RULES (ONLY IF GENERATING A WORKFLOW)
If you decide to output a workflow:
1. **Chain of Thought**: You must first think step-by-step about the architecture, the nodes needed, and the data mapping. Output your thoughts inside a `<thought>` XML block BEFORE the JSON block.
2. **Data Mapping**: Use n8n expressions like `={{{{ $json.fieldName }}}}`.
3. **Node Types**: Use modern n8n nodes (e.g. `n8n-nodes-base.httpRequest`, `n8n-nodes-base.webhook`).
4. **JSON Output**: Output the JSON block wrapped in ```json ... ```.

# KNOWN CREDENTIALS
If the workflow requires any of these services, attach these EXACT credentials:
- Telegram: `"credentials": {{ "telegramApi": {{ "id": "tDyw6EwwmhJnMKu5", "name": "ETL Bot" }} }}`
- Ollama: `"credentials": {{ "ollamaApi": {{ "id": "wDe9MCIO6q1M7Gau", "name": "Ollama account" }} }}`
- Postgres: `"credentials": {{ "postgres": {{ "id": "5617978f-0b85-4382-8768-f84e14ee6223", "name": "PostgreSQL — n8n Stack" }} }}`
- Notion: `"credentials": {{ "notionApi": {{ "id": "WTrWPkXdnXFPfOi9", "name": "Notion account 2" }} }}`
- OpenRouter: `"credentials": {{ "openRouterApi": {{ "id": "Wfnk5q7gswurynsI", "name": "OpenRouter account 2" }} }}`
- Qdrant: `"credentials": {{ "qdrantApi": {{ "id": "bH2hk1EtEFghgicV", "name": "Qdrant account" }} }}`
- Google Drive: `"credentials": {{ "googleDriveOAuth2Api": {{ "id": "Q8F6AF4nNReCfLij", "name": "Google Drive account" }} }}`

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

    try:
        # Prepare history for OpenAI API
        # Remove any internal workflowObj metadata from previous messages
        api_messages = [{"role": "system", "content": system_message}]
        for msg in messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=0.4
        )
        
        content = response.choices[0].message.content.strip()
        
        # Regex to extract JSON block
        workflow_json = None
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                workflow_json = json.loads(json_match.group(1).strip())
                # Remove the JSON block from the conversational content
                content = content.replace(json_match.group(0), "").strip()
            except Exception as e:
                pass # If it fails to parse, workflow_json remains None
                
        # Format the conversational output nicely (remove raw <thought> blocks from the user's view if you want, or leave them)
        content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL).strip()
        
        if not content and workflow_json:
            content = "Here is the generated workflow based on your requirements:"

        return {"success": True, "message": content, "workflow": workflow_json}
        
    except Exception as e:
        return {"error": f"Failed to process request: {str(e)}"}

if __name__ == "__main__":
    # Test script locally
    res = generate_workflow([{"role": "user", "content": "Create a simple workflow with a webhook trigger that sends an HTTP GET request to example.com"}])
    print(json.dumps(res, indent=2))
