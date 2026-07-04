import json

with open('workflow_nodes_raw.json', 'r', encoding='utf-16') as f:
    raw_content = f.read().strip()

nodes = json.loads(raw_content)

for node in nodes:
    if node.get('type') == '@n8n/n8n-nodes-langchain.lmChatOllama':
        print(f"=== Node: {node.get('name')} ===")
        print(json.dumps(node, indent=2))
        print()
