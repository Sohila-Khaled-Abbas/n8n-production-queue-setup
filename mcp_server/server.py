import json
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
        prompt: A description of the desired n8n workflow. (e.g. "Create a workflow that triggers every hour, fetches data from a weather API, and sends an email.")
    """
    print(f"[Tool Call] create_n8n_workflow called with prompt: {prompt}")
    
    try:
        workflow_json = generate_workflow(prompt)
        
        if "error" in workflow_json:
            return f"Error generating workflow: {workflow_json['error']}"
            
        return json.dumps(workflow_json, indent=2)
        
    except Exception as e:
        return f"Unexpected error during workflow generation: {str(e)}"

if __name__ == "__main__":
    # Start the server using SSE (Server-Sent Events) transport
    # This allows it to be hosted online and accessed over HTTP.
    print("Starting n8n Workflow Generator MCP Server on port 8000...")
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
