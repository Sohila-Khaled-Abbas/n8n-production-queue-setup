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

from n8n_client import build_knowledge_index, build_credential_index

# Pre-load local n8n knowledge base to save context limits
# If API fails, we fallback to empty strings
KNOWLEDGE_INDEX = build_knowledge_index() or "(No local portfolio found from API)"
CREDENTIAL_INDEX = build_credential_index() or "(No local credentials found from API)"

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
{KNOWLEDGE_INDEX}

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
            return {"error": f"Failed to process request: {str(e)}"}
            
    return {"error": "Failed to generate valid n8n JSON after 3 attempts. The model may be struggling with complex structures."}

if __name__ == "__main__":
    # Test script locally
    res = generate_workflow([{"role": "user", "content": "Create a simple workflow with a webhook trigger that sends an HTTP GET request to example.com"}])
    print(json.dumps(res, indent=2))
