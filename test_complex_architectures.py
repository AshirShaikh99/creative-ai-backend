"""
Test script for complex software architecture diagram prompts
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
test_dir = f"complex_architecture_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(test_dir, exist_ok=True)

# Test prompts for various complex architecture types
test_prompts = [
    {
        "name": "Hexagonal_Architecture",
        "prompt": "Create a software architecture diagram for a hexagonal (ports and adapters) architecture for an insurance claims processing system with domain core, application services, and various adapters for UI, database, and external services."
    },
    {
        "name": "Saga_Pattern",
        "prompt": "Design a microservice architecture implementing the Saga pattern for a travel booking system handling flight, hotel, car rental, and payment transactions with compensation for failures."
    },
    {
        "name": "CQRS_Event_Sourcing",
        "prompt": "Create a detailed architecture diagram for an e-commerce system using CQRS and Event Sourcing patterns with event store, read models, projections, and eventual consistency."
    },
    {
        "name": "Service_Mesh",
        "prompt": "Design a service mesh architecture for a cloud-native application with sidecars, control plane, data plane, service discovery, and traffic management components like Istio or Linkerd."
    },
    {
        "name": "BFF_Pattern",
        "prompt": "Create a software architecture using the Backend-for-Frontend (BFF) pattern for a multi-channel e-commerce platform with web, mobile, and IoT clients, each with dedicated backend services."
    },
    {
        "name": "Streaming_Data_Pipeline",
        "prompt": "Design a real-time streaming data pipeline architecture for processing IoT sensor data, including ingestion, stream processing, analytics, storage, and visualization components."
    },
    {
        "name": "Domain_Driven_Design",
        "prompt": "Create a detailed architecture diagram for a healthcare system based on Domain-Driven Design with bounded contexts, aggregates, entities, value objects, domain services, and anti-corruption layers."
    },
    {
        "name": "Strangler_Pattern",
        "prompt": "Design an architecture showing the Strangler Pattern for incrementally migrating a monolithic legacy system to microservices, including the facade, routing, and service migration components."
    },
    {
        "name": "Data_Mesh",
        "prompt": "Create a data mesh architecture for a large enterprise with domain-oriented data ownership, data as a product, self-serve data infrastructure, and federated computational governance."
    },
    {
        "name": "Microfrontend_Architecture",
        "prompt": "Design a micro-frontend architecture for a complex web application with shell application, multiple independent frontend modules, shared libraries, and backend service integration."
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
print(f"Starting complex architecture diagram tests - saving results to {test_dir}")
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
        print(f"Description: {result.get('description', '')[:150]}...")
        
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