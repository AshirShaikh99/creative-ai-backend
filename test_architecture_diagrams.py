"""
Test script for various software architecture diagram prompts
"""

import requests
import json
import uuid
import re
import os
from datetime import datetime

# API endpoint
base_url = "http://localhost:8000"  # Change if your API is running on a different port
api_prefix = "/api/v1"  # This matches the API_V1_STR in your config
diagram_url = f"{base_url}{api_prefix}/diagram"

# User ID for authentication
user_id = str(uuid.uuid4())

# Create test directory
test_dir = f"diagram_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(test_dir, exist_ok=True)

# Test prompts for various architecture types
test_prompts = [
    {
        "name": "Microservice_Architecture",
        "prompt": "Create a software architecture diagram for a microservice-based e-commerce platform with user service, product catalog, order management, and payment processing."
    },
    {
        "name": "Event_Driven_Architecture",
        "prompt": "Design an event-driven architecture for a real-time analytics system with producers, event bus, consumers, and data processing pipelines."
    },
    {
        "name": "API_Gateway_Pattern",
        "prompt": "Create a software architecture diagram showing API Gateway pattern with authentication, rate limiting, and service routing."
    },
    {
        "name": "CQRS_Architecture",
        "prompt": "Design a software architecture following the CQRS (Command Query Responsibility Segregation) pattern with separate read and write models."
    },
    {
        "name": "Serverless_Architecture",
        "prompt": "Create a serverless architecture diagram for a photo processing application with cloud functions, object storage, and managed database."
    },
    {
        "name": "Message_Queue_Architecture",
        "prompt": "Design a system architecture with message queues for an order processing system handling high volume of transactions."
    }
]

def clean_mermaid_syntax(syntax):
    """Clean up any text around the mermaid code and return just the diagram code."""
    # If there are ```mermaid blocks, extract just the diagram code
    if "```mermaid" in syntax:
        pattern = r"```mermaid\n(.*?)```"
        match = re.search(pattern, syntax, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # If there are code blocks but not specifically marked as mermaid
    elif "```" in syntax:
        pattern = r"```(?:.*?)\n(.*?)```"
        match = re.search(pattern, syntax, re.DOTALL)
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
print(f"Starting architecture diagram tests - saving results to {test_dir}")
results = []

for test in test_prompts:
    print(f"\n\n======= Testing: {test['name']} =======")
    test_result = {
        "name": test["name"],
        "prompt": test["prompt"],
        "status": "pending"
    }
    
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
        
        test_result["status"] = "success"
        test_result["diagram_type"] = result.get("diagram_type")
        test_result["description"] = result.get("description")
        
        print(f"Response received - Status: {response.status_code}")
        print(f"Diagram Type: {result.get('diagram_type')}")
        print(f"Description: {result.get('description')}")
        
        # Clean and save Mermaid syntax to file
        syntax = result.get('syntax', '')
        clean_syntax = clean_mermaid_syntax(syntax)
        
        mermaid_filename = f"{test_dir}/{test['name'].lower()}_diagram.mmd"
        with open(mermaid_filename, "w") as f:
            f.write(clean_syntax)
        print(f"Mermaid syntax saved to {mermaid_filename}")
        
        # Also save the raw data for debugging
        raw_filename = f"{test_dir}/{test['name'].lower()}_raw.json"
        with open(raw_filename, "w") as f:
            json.dump(result, f, indent=2)
        
        # If software architecture, check for nodes
        if result.get('diagram_type') == 'software_architecture' and result.get('nodes'):
            node_count = len(result.get('nodes', []))
            connection_count = len(result.get('connections', []))
            cluster_count = len(result.get('clusters', []))
            
            test_result["node_count"] = node_count
            test_result["connection_count"] = connection_count
            test_result["cluster_count"] = cluster_count
            
            print(f"\nNumber of nodes: {node_count}")
            print(f"Number of connections: {connection_count}")
            print(f"Number of clusters: {cluster_count}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        test_result["status"] = "error"
        test_result["error"] = str(e)
    
    results.append(test_result)

# Save overall results summary
summary_file = f"{test_dir}/test_summary.json"
with open(summary_file, "w") as f:
    json.dump(results, f, indent=2)

print(f"\n\nTesting completed! Summary saved to {summary_file}")
print("\nTip: Copy the contents of any .mmd file and paste into https://mermaid.live/ to view the diagram") 