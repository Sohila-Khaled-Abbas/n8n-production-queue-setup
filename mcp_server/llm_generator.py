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
        raise ValueError("No AI providers found in .env (Need HUGGINGFACE_API_TOKEN, OLLAMA_HOST, or OPENROUTER_API_KEY)")

    is_complex = any(word in prompt.lower() for word in ["advanced", "complex", "production", "agent", "memory", "tools", "langchain"])

    # Priority 1: OpenRouter (best for complex tasks if available)
    if "openrouter" in providers and is_complex:
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_TOKEN")
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        return client, "anthropic/claude-3.5-sonnet" # or another strong model

    # Priority 2: HuggingFace (great balance of speed/quality via v1 router)
    if "huggingface" in providers:
        client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HUGGINGFACE_API_TOKEN")
        )
        if is_complex:
            return client, "meta-llama/Meta-Llama-3-70B-Instruct"
        else:
            return client, "openai/gpt-oss-20b:groq"

    # Priority 3: Local Ollama (fallback for simple tasks or local preference)
    if "ollama" in providers:
        ollama_host = os.getenv("OLLAMA_HOST").replace("host.docker.internal", "localhost")
        if not ollama_host.startswith("http"):
            ollama_host = f"http://{ollama_host}"
        client = OpenAI(base_url=f"{ollama_host}/v1", api_key="ollama")
        return client, "llama3"

    raise ValueError("Failed to select a valid AI provider.")


import re

def generate_workflow(prompt: str) -> dict:
    """
    Generates an n8n JSON workflow based on the user's prompt using advanced prompt engineering.
    """
    client, model = get_client_and_model(prompt)
    print(f"[llm_generator] Routing request to model: {model}")

    system_message = """You are an elite n8n Workflow Architect and Data Engineer.
Your objective is to design production-grade n8n workflow JSONs based on the user's request.

# CORE RULES
1. **Chain of Thought**: You must first think step-by-step about the architecture, the nodes needed, and the data mapping. Output your thoughts inside a `<thought>` XML block.
2. **JSON Output**: After your `<thought>` block, you MUST output a raw, valid n8n JSON object wrapped in ```json ... ```. Do NOT output anything after the JSON block.
3. **Data Mapping**: Use expressions like `={{ $json.fieldName }}` to reference data from previous nodes.
4. **Node Types**: Use exact, modern n8n node types (e.g., `n8n-nodes-base.httpRequest`, `@n8n/n8n-nodes-langchain.agent`, `n8n-nodes-base.webhook`, `n8n-nodes-base.code`).

# KNOWN CREDENTIALS (USE THESE EXACTLY IF NEEDED)
If the user's workflow requires any of these services, you MUST attach these exact credential objects to the node's `"credentials"` property:
- **Telegram**: `"credentials": { "telegramApi": { "id": "tDyw6EwwmhJnMKu5", "name": "ETL Bot" } }`
- **Ollama**: `"credentials": { "ollamaApi": { "id": "wDe9MCIO6q1M7Gau", "name": "Ollama account" } }`
- **Postgres**: `"credentials": { "postgres": { "id": "5617978f-0b85-4382-8768-f84e14ee6223", "name": "PostgreSQL — n8n Stack" } }`
- **Notion**: `"credentials": { "notionApi": { "id": "WTrWPkXdnXFPfOi9", "name": "Notion account 2" } }`
- **OpenRouter**: `"credentials": { "openRouterApi": { "id": "Wfnk5q7gswurynsI", "name": "OpenRouter account 2" } }`
- **Qdrant**: `"credentials": { "qdrantApi": { "id": "bH2hk1EtEFghgicV", "name": "Qdrant account" } }`
- **Google Drive**: `"credentials": { "googleDriveOAuth2Api": { "id": "Q8F6AF4nNReCfLij", "name": "Google Drive account" } }`

# JSON STRUCTURE
The extracted JSON must strictly follow this format:
```json
{
  "name": "Generated Workflow",
  "nodes": [
    {
      "parameters": {
        "method": "POST",
        "url": "https://api.example.com",
        "sendHeaders": true,
        "headerParameters": { "parameters": [ { "name": "Authorization", "value": "Bearer token" } ] }
      },
      "id": "generate-a-unique-uuid-here",
      "name": "HTTP Request",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [0, 0]
    }
  ],
  "connections": {
    "Previous Node Name": {
      "main": [
        [
          {
            "node": "Next Node Name",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```
CRITICAL: Ensure the `connections` object perfectly matches the `name` of the nodes in the `nodes` array."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        
        # Regex to extract JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # Fallback in case they didn't wrap it
            json_str = content.split("</thought>")[-1].strip()
            if json_str.startswith("{"):
                pass
            else:
                return {"error": "Failed to parse JSON from LLM output. Ensure it outputs valid JSON."}
                
        return json.loads(json_str)
        
    except Exception as e:
        return {"error": f"Failed to generate workflow: {str(e)}"}

if __name__ == "__main__":
    # Test script locally
    res = generate_workflow("Create a simple workflow with a webhook trigger that sends an HTTP GET request to example.com")
    print(json.dumps(res, indent=2))
