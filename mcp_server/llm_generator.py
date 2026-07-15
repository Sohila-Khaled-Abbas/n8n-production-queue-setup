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


def generate_workflow(prompt: str) -> dict:
    """
    Generates an n8n JSON workflow based on the user's prompt.
    """
    client, model = get_client_and_model(prompt)
    print(f"[llm_generator] Routing request to model: {model}")

    system_message = """You are an expert n8n workflow architect. 
Your task is to output ONLY a raw, valid JSON object representing an n8n workflow.
The JSON must follow this exact structure:
{
  "name": "Generated Workflow Name",
  "nodes": [
    {
      "parameters": {},
      "id": "unique-uuid",
      "name": "Node Name",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [0, 0]
    }
  ],
  "connections": {
    "Node Name": {
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
Do NOT wrap the JSON in markdown code blocks. Output nothing but the valid JSON."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean up markdown if the LLM hallucinated it
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        return json.loads(content)
        
    except Exception as e:
        return {"error": f"Failed to generate workflow: {str(e)}"}

if __name__ == "__main__":
    # Test script locally
    res = generate_workflow("Create a simple workflow with a webhook trigger that sends an HTTP GET request to example.com")
    print(json.dumps(res, indent=2))
