import os
import json

def compile_docs_data():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflows_dir = os.path.join(project_root, 'workflows')
    docs_dir = os.path.join(project_root, 'docs')
    output_path = os.path.join(docs_dir, 'data.json')
    
    print(f"Project Root: {project_root}")
    print(f"Scanning workflows in: {workflows_dir}")
    print(f"Scanning markdown guides in: {docs_dir}")
    
    # 1. Compile Workflows
    compiled_workflows = []
    if os.path.exists(workflows_dir):
        for filename in sorted(os.listdir(workflows_dir)):
            if filename.endswith('.json'):
                file_path = os.path.join(workflows_dir, filename)
                try:
                    # Read JSON, support multiple encodings
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    except UnicodeDecodeError:
                        with open(file_path, 'r', encoding='utf-16') as f:
                            data = json.load(f)
                    
                    nodes = data.get('nodes', [])
                    node_count = len(nodes)
                    
                    # Extract triggers
                    triggers = []
                    for node in nodes:
                        node_type = node.get('type', '')
                        if 'Trigger' in node_type or node_type.endswith('Trigger') or 'webhook' in node_type.lower():
                            # Clean node type name for readability
                            clean_type = node_type.replace('n8n-nodes-base.', '').replace('@n8n/n8n-nodes-langchain.', '')
                            triggers.append({
                                'name': node.get('name'),
                                'type': clean_type
                            })
                    
                    # If no explicit triggers, check if it's manual
                    if not triggers:
                        for node in nodes:
                            if 'manual' in node.get('type', '').lower() or 'onclickingexecute' in node.get('type', '').lower():
                                triggers.append({'name': node.get('name'), 'type': 'Manual'})
                    
                    # Unique node types in this workflow
                    node_types = sorted(list(set(node.get('type', '').replace('n8n-nodes-base.', '').replace('@n8n/n8n-nodes-langchain.', '') for node in nodes)))
                    
                    compiled_workflows.append({
                        'id': data.get('id', filename.replace('.json', '')),
                        'name': data.get('name', filename.replace('.json', '')),
                        'active': data.get('active', False),
                        'nodeCount': node_count,
                        'triggers': triggers,
                        'nodeTypes': node_types,
                        'description': data.get('description') or f"Automated workflow containing {node_count} nodes.",
                        'rawJson': json.dumps(data, indent=2, ensure_ascii=False)
                    })
                except Exception as e:
                    print(f"Error parsing workflow file {filename}: {e}")
    
    # 2. Compile Markdown Guides
    compiled_guides = {}
    guide_files = {
        'architecture': 'architecture.md',
        'production_guide': 'production_guide.md',
        'scripts': 'scripts.md',
        'troubleshooting': 'troubleshooting.md'
    }
    
    for key, filename in guide_files.items():
        file_path = os.path.join(docs_dir, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    compiled_guides[key] = f.read()
            except Exception as e:
                print(f"Error reading guide {filename}: {e}")
                compiled_guides[key] = f"Error loading guide: {e}"
        else:
            print(f"Warning: Guide file {filename} not found.")
            compiled_guides[key] = f"Guide {filename} is missing."
            
    # 3. Save Compiled Data
    output_data = {
        'workflows': compiled_workflows,
        'guides': compiled_guides,
        'stats': {
            'totalWorkflows': len(compiled_workflows),
            'activeWorkflows': sum(1 for w in compiled_workflows if w['active']),
            'totalNodesCount': sum(w['nodeCount'] for w in compiled_workflows)
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully generated database at: {output_path}")
    print(f"Total Workflows Compiled: {len(compiled_workflows)}")

if __name__ == '__main__':
    compile_docs_data()
