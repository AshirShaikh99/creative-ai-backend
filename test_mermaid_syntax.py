"""
Test script to validate Mermaid syntax for different node types
"""

def test_node_syntax():
    """Generate sample Mermaid syntax for each node type and validate it"""
    
    # Basic flowchart header
    diagram = "flowchart TD\n"
    
    # Test different node types with proper syntax
    nodes = [
        # Basic rectangle
        {"id": "rect1", "shape": "rectangle", "label": "Basic Rectangle", "code": 'rect1["Basic Rectangle"]'},
        
        # Round edges
        {"id": "round1", "shape": "round", "label": "Round Edges", "code": 'round1("Round Edges")'},
        
        # Stadium shape
        {"id": "stadium1", "shape": "stadium", "label": "Stadium", "code": 'stadium1(["Stadium"])'},
        
        # Subroutine shape
        {"id": "subroutine1", "shape": "subroutine", "label": "Subroutine", "code": 'subroutine1[["Subroutine"]]'},
        
        # Cylindrical shape (database)
        {"id": "cylinder1", "shape": "cylinder", "label": "Database", "code": 'cylinder1[("Database")]'},
        
        # Circle shape
        {"id": "circle1", "shape": "circle", "label": "Circle", "code": 'circle1(("Circle"))'},
        
        # Asymmetric shape (UI)
        {"id": "ui1", "shape": "asymmetric", "label": "User Interface", "code": 'ui1>"User Interface"]'},
        
        # Rhombus (diamond) shape
        {"id": "rhombus1", "shape": "rhombus", "label": "Decision", "code": 'rhombus1{"Decision"}'},
        
        # Hexagon shape
        {"id": "hexagon1", "shape": "hexagon", "label": "Hexagon", "code": 'hexagon1{{"Hexagon"}}'},
        
        # Parallelogram (left to right)
        {"id": "parallel1", "shape": "parallelogram1", "label": "Parallelogram 1", "code": 'parallel1[/"Parallelogram 1"/]'},
        
        # Parallelogram (right to left)
        {"id": "parallel2", "shape": "parallelogram2", "label": "Parallelogram 2", "code": 'parallel2[\"Parallelogram 2"\]'},
        
        # Trapezoid (top wide)
        {"id": "trap1", "shape": "trapezoid1", "label": "Trapezoid 1", "code": 'trap1[/"Trapezoid 1"\]'},
        
        # Trapezoid (bottom wide)
        {"id": "trap2", "shape": "trapezoid2", "label": "Trapezoid 2", "code": 'trap2[\"Trapezoid 2"/]'}
    ]
    
    # Add each node to the diagram
    for node in nodes:
        diagram += f"    {node['code']}\n"
    
    # Add some connections to show relationships
    diagram += """
    rect1 --> round1
    round1 --> stadium1
    stadium1 --> subroutine1
    subroutine1 --> cylinder1
    cylinder1 --> circle1
    circle1 --> ui1
    ui1 --> rhombus1
    rhombus1 -->|Yes| hexagon1
    rhombus1 -->|No| parallel1
    hexagon1 --> parallel2
    parallel1 --> trap1
    parallel2 --> trap2
    """
    
    # Save to file for testing
    with open("mermaid_syntax_test.mmd", "w") as f:
        f.write(diagram)
    
    print("Generated Mermaid syntax test file: mermaid_syntax_test.mmd")
    print("Copy this to https://mermaid.live/ to validate")
    
    return diagram

# Test the syntax
if __name__ == "__main__":
    syntax = test_node_syntax()
    print("\nGenerated syntax:\n")
    print(syntax) 