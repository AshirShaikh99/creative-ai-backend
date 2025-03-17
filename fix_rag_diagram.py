"""
Fix RAG Architecture Diagram Syntax
This script takes a Mermaid diagram input and fixes syntax issues
"""

import json
import re

def fix_mermaid_syntax(input_file, output_file):
    """
    Read a Mermaid diagram file, fix syntax issues, and save to a new file
    """
    with open(input_file, 'r') as f:
        content = f.read()
    
    # First, extract just the diagram code if it's in markdown format
    if "```mermaid" in content:
        pattern = r"```mermaid\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            content = match.group(1).strip()
    elif "```" in content:
        pattern = r"```(?:.*?)\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            content = match.group(1).strip()
    
    # Fix common syntax issues
    
    # 1. Fix UI node syntax - {["Text"]} to >"Text"]
    content = re.sub(r'(\w+)\{*\[\s*"([^"]+)"\s*\]\}*', r'\1>"\2"]', content)
    
    # 2. Fix database node syntax - [(Text)] to [("Text")]
    content = re.sub(r'(\w+)\[\(\s*([^")]+)\s*\)\]', r'\1[("\2")]', content)
    
    # 3. Fix agent node syntax - hexagons
    content = re.sub(r'(\w+)\["([^"]+)"\]\s+%agent', r'\1{"\2"}', content)
    
    # 4. Fix LLM syntax - stadium shape
    content = re.sub(r'(\w+)\[/"([^"]+)"\\]', r'\1(["\2"])', content)
    
    # 5. Fix subgraph syntax
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        if line.strip().startswith('subgraph') and not '[' in line and i+1 < len(lines):
            # If this is a subgraph line without proper label syntax
            subgraph_id = line.strip().split()[1]
            next_line = lines[i+1].strip()
            fixed_lines.append(f'subgraph {subgraph_id}["{next_line}"]')
            # Skip the next line (which was the label)
            i += 1
            continue
        else:
            fixed_lines.append(line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    # Save the fixed content
    with open(output_file, 'w') as f:
        f.write(fixed_content)
    
    print(f"Fixed Mermaid syntax saved to {output_file}")
    return fixed_content

if __name__ == "__main__":
    # Fix the RAG architecture diagram
    input_file = "rag_architecture_simple_diagram.mmd"
    output_file = "fixed_rag_diagram.mmd"
    
    try:
        fixed_content = fix_mermaid_syntax(input_file, output_file)
        print("\nFixed content preview:")
        print(fixed_content[:300] + "...")
    except Exception as e:
        print(f"Error fixing diagram: {str(e)}")
        
    print("\nTip: Copy the contents of the fixed file and paste into https://mermaid.live/ to verify it renders correctly.") 