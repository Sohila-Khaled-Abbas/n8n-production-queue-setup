import json

# Load raw JSON (PowerShell output is UTF-16)
try:
    with open('workflow_nodes_raw.json', 'r', encoding='utf-16') as f:
        nodes = json.load(f)
except Exception:
    with open('workflow_nodes_raw.json', 'r', encoding='utf-8') as f:
        nodes = json.load(f)

modified_count = 0
for node in nodes:
    if node.get('type') == '@n8n/n8n-nodes-langchain.lmChatOllama':
        print(f"Modifying node: {node.get('name')}")
        
        # Ensure model is qwen2.5:1.5b
        node['parameters']['model'] = 'qwen2.5:1.5b'
        
        # Add numCtx to options
        options = node['parameters'].get('options', {})
        options['numCtx'] = 2048
        node['parameters']['options'] = options
        modified_count += 1

print(f"Modified {modified_count} nodes.")

# Save modified JSON in standard UTF-8 format
with open('workflow_nodes_modified.json', 'w', encoding='utf-8') as f:
    json.dump(nodes, f, ensure_ascii=False)
