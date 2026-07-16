import os
import requests

def get_n8n_headers():
    api_key = os.getenv("N8N_API_KEY")
    if not api_key:
        return None
    return {"X-N8N-API-KEY": api_key, "Accept": "application/json"}

def get_n8n_host():
    host = os.getenv("N8N_HOST", "http://localhost:5678")
    return host.rstrip('/')

def fetch_local_workflows():
    headers = get_n8n_headers()
    host = get_n8n_host()
    if not headers:
        return None
    try:
        response = requests.get(f"{host}/api/v1/workflows", headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("data", [])
    except Exception as e:
        print(f"[n8n_client] Error fetching workflows: {e}")
    return None

def fetch_local_credentials():
    headers = get_n8n_headers()
    host = get_n8n_host()
    if not headers:
        return None
    try:
        response = requests.get(f"{host}/api/v1/credentials", headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("data", [])
    except Exception as e:
        print(f"[n8n_client] Error fetching credentials: {e}")
    return None

def build_knowledge_index():
    workflows = fetch_local_workflows()
    if not workflows:
        return None
        
    lines = []
    for wf in workflows:
        name = wf.get("name", "Unknown Workflow")
        lines.append(f"- {name}")
    
    return "\n".join(lines[:100])

def build_credential_index():
    creds = fetch_local_credentials()
    if not creds:
        return None
    
    lines = []
    for cred in creds:
        name = cred.get("name", "Unknown")
        cred_id = cred.get("id", "")
        type_str = cred.get("type", "")
        lines.append(f'- {name} ({type_str}): `"credentials": {{ "{type_str}": {{ "id": "{cred_id}", "name": "{name}" }} }}`')
    
    return "\n".join(lines)
