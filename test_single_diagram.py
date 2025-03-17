import requests
import json
import uuid
import re

# API endpoint
base_url = "http://localhost:8000"
api_prefix = "/api/v1"
diagram_url = f"{base_url}{api_prefix}/diagram"

# User ID for authentication
user_id = str(uuid.uuid4())

# Test just one diagram
test_prompt = "Create a software architecture diagram for a microservice-based e-commerce platform with user service, product catalog, order management, and payment processing."

# Prepare request
headers = {
    "Content-Type": "application/json",
    "user-id": user_id
}

payload = {
    "message": test_prompt,
    "options": {}
}

# Make the request
print(f"Sending request with prompt: {test_prompt[:50]}...")
try:
    response = requests.post(diagram_url, headers=headers, json=payload)
    response.raise_for_status()
    
    # Process response
    result = response.json()
    
    print(f"Response received - Status: {response.status_code}")
    print(f"Diagram Type: {result.get('diagram_type')}")
    print(f"Description: {result.get('description')}")
    
    # Print the Mermaid syntax
    syntax = result.get('syntax', '')
    
    # If software architecture, check for nodes
    if result.get('diagram_type') == 'software_architecture' and result.get('nodes'):
        node_count = len(result.get('nodes', []))
        connection_count = len(result.get('connections', []))
        cluster_count = len(result.get('clusters', []))
        
        print(f"\nNumber of nodes: {node_count}")
        print(f"Number of connections: {connection_count}")
        print(f"Number of clusters: {cluster_count}")
    
    print("\n--- MERMAID SYNTAX ---\n")
    print(syntax)
    
except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}") 