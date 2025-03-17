import requests
import json
import uuid
import re

# API endpoint
base_url = "http://localhost:8000"  # Change if your API is running on a different port
api_prefix = "/api/v1"  # This matches the API_V1_STR in your config
diagram_url = f"{base_url}{api_prefix}/diagram"

# User ID for authentication (you might need to change this)
user_id = str(uuid.uuid4())

# Test prompts
test_prompts = [
    {
        "name": "RAG Architecture Simple",
        "prompt": "Draw an AI architecture for a RAG system with basic components."
    },
    {
        "name": "Simple Flowchart",
        "prompt": "Create a flowchart for a user authentication process with email verification."
    },
    {
        "name": "Sequence Diagram",
        "prompt": "Create a sequence diagram for user login process."
    }
]

def clean_mermaid_syntax(syntax):
    """Clean up any text around the mermaid code and return just the diagram code."""
    # If there are ```mermaid blocks, extract just the diagram code
    if "```mermaid" in syntax:
        match = re.search(r"```mermaid\n(.*?)```", syntax, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # If there are code blocks but not specifically marked as mermaid
    elif "```" in syntax:
        match = re.search(r"```(?:.*?)\n(.*?)```", syntax, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # Remove any unnecessary intro text
    lines = syntax.split('\n')
    clean_lines = []
    found_diagram = False
    
    for line in lines:
        if found_diagram or line.strip().startswith("graph ") or line.strip().startswith("flowchart ") or line.strip().startswith("sequenceDiagram"):
            found_diagram = True
            clean_lines.append(line)
    
    if clean_lines:
        return "\n".join(clean_lines)
    
    # If we couldn't find a specific diagram syntax, return the original
    return syntax

# Test each prompt
for test in test_prompts:
    print(f"\n\n======= Testing: {test['name']} =======")
    
    # Prepare request
    headers = {
        "Content-Type": "application/json",
        "user-id": user_id
    }
    
    payload = {
        "message": test["prompt"],
        "options": {}
    }
    
    # Make the request
    print(f"Sending request with prompt: {test['prompt'][:50]}...")
    try:
        response = requests.post(diagram_url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Process response
        result = response.json()
        
        print(f"Response received - Status: {response.status_code}")
        print(f"Diagram Type: {result.get('diagram_type')}")
        print(f"Description: {result.get('description')}")
        
        # Clean and save Mermaid syntax to file
        syntax = result.get('syntax', '')
        clean_syntax = clean_mermaid_syntax(syntax)
        
        mermaid_filename = f"{test['name'].lower().replace(' ', '_')}_diagram.mmd"
        with open(mermaid_filename, "w") as f:
            f.write(clean_syntax)
        print(f"Mermaid syntax saved to {mermaid_filename}")
        
        # Print excerpt of the syntax
        preview_length = min(200, len(clean_syntax))
        print(f"\nSyntax Preview (first {preview_length} chars):\n{clean_syntax[:preview_length]}...")
        
        # If AI architecture, print node count
        if result.get('diagram_type') == 'ai_architecture' and result.get('nodes'):
            print(f"\nNumber of nodes: {len(result.get('nodes'))}")
            print(f"Number of connections: {len(result.get('connections', []))}")
            print(f"Number of clusters: {len(result.get('clusters', []))}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        
print("\n\nTesting completed!") 