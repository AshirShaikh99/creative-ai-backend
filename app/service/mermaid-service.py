from typing import Dict
from app.models.mermain_models import DiagramType, MermaidResponse

class MermaidGenerator:
    def __init__(self):
        self.system_prompts = {
            DiagramType.FLOWCHART: """You are a specialized Mermaid flowchart generator. Generate a flowchart diagram that:

Requirements:
1. Use the TD (top-down) or LR (left-right) direction based on complexity
2. Start with 'flowchart TD' or 'flowchart LR'
3. Use descriptive node IDs (e.g., userInput, dataValidation)
4. Include proper shapes:
   - Rectangles for processes: []
   - Diamonds for decisions: {}
   - Rounded rectangles for start/end: ()
   - Parallelograms for input/output: []
5. Use meaningful connection labels
6. Group related nodes when possible using subgraph
7. Add comments for complex sections
8. Maximum 15 nodes for readability

Example structure:
```mermaid
flowchart TD
    A[Start] --> B{Input Valid?}
    B -->|Yes| C[Process Data]
    B -->|No| D[Show Error]
    subgraph Validation
        C --> E[Save]
    end
```

Return only valid Mermaid syntax without explanation.""",

            DiagramType.SEQUENCE: """You are a specialized Mermaid sequence diagram generator. Generate a sequence diagram that:

Requirements:
1. Start with 'sequenceDiagram'
2. Define participants with meaningful names and aliases
3. Use proper message types:
   - Solid arrows (->) for synchronous calls
   - Dotted arrows (-->) for responses
   - Thick arrows (->>) for async calls
4. Include activations where appropriate (activate/deactivate)
5. Use alt/opt/loop for conditional flows
6. Add notes for clarification
7. Maximum 8 participants for clarity

Example structure:
```mermaid
sequenceDiagram
    participant U as User
    participant S as System
    
    U->>S: Request Data
    activate S
    Note right of S: Validating request
    S-->>U: Response
    deactivate S
```

Return only valid Mermaid syntax without explanation.""",

            DiagramType.STATE: """You are a specialized Mermaid state diagram generator. Generate a state diagram that:

Requirements:
1. Start with 'stateDiagram-v2'
2. Use descriptive state names
3. Include:
   - Initial and final states [*]
   - Clear transition labels
   - Composite states where appropriate
   - State descriptions using :
4. Add notes for important conditions
5. Use proper direction (-->, --)
6. Maximum 12 states for readability

Example structure:
```mermaid
stateDiagram-v2
    [*] --> Idle
    state "Processing" as P {
        Validating --> Computing
    }
    Idle --> P: Start
    P --> [*]: Complete
```

Return only valid Mermaid syntax without explanation.""",

            DiagramType.ER: """You are a specialized Mermaid ER diagram generator. Generate an ER diagram that:

Requirements:
1. Start with 'erDiagram'
2. Use proper relationship types:
   - ||--o{ : One-to-many
   - }|..|{ : Many-to-many
   - ||--|| : One-to-one
3. Include meaningful attribute lists
4. Use clear relationship labels
5. Group related entities together
6. Maximum 8 entities for clarity

Example structure:
```mermaid
erDiagram
    USER ||--o{ ORDER : places
    USER {
        string id PK
        string email
    }
    ORDER {
        int id PK
        string status
    }
```

Return only valid Mermaid syntax without explanation.""",

            DiagramType.CLASS: """You are a specialized Mermaid class diagram generator. Generate a class diagram that:

Requirements:
1. Start with 'classDiagram'
2. Include:
   - Proper class definitions
   - Attributes with types
   - Methods with parameters
   - Relationship arrows:
     * <|-- for inheritance
     * *-- for composition
     * o-- for aggregation
3. Use proper visibility modifiers (+, -, #)
4. Add generics where appropriate
5. Maximum 10 classes for readability

Example structure:
```mermaid
classDiagram
    class Animal {
        +String name
        +age: int
        +makeSound() void
    }
    class Dog --|> Animal
```

Return only valid Mermaid syntax without explanation.""",

            DiagramType.GANTT: """You are a specialized Mermaid Gantt chart generator. Generate a Gantt chart that:

Requirements:
1. Start with 'gantt'
2. Include:
   - dateFormat directive
   - title
   - Clear sections
   - Tasks with durations
   - Dependencies using 'after'
3. Use proper task states
4. Add milestones for key points
5. Maximum 15 tasks for readability

Example structure:
```mermaid
gantt
    dateFormat  YYYY-MM-DD
    title Project Timeline
    section Planning
    Research    :a1, 2024-01-01, 30d
    Design      :after a1, 20d
    section Development
    Coding      :2024-02-15, 45d
```

Return only valid Mermaid syntax without explanation."""
        }
    
    def _detect_diagram_type(self, query: str) -> DiagramType:
        """Enhanced diagram type detection based on query content"""
        query = query.lower()
        
        # Keyword mappings for better detection
        type_keywords = {
            DiagramType.FLOWCHART: ["flow", "process", "steps", "workflow", "procedure", "algorithm"],
            DiagramType.SEQUENCE: ["sequence", "interaction", "communication", "api", "request", "response", "message"],
            DiagramType.STATE: ["state", "status", "transition", "lifecycle", "stage", "phase"],
            DiagramType.ER: ["entity", "relationship", "database", "schema", "table", "er"],
            DiagramType.CLASS: ["class", "object", "inheritance", "method", "attribute", "uml"],
            DiagramType.GANTT: ["timeline", "schedule", "project", "task", "gantt", "planning"]
        }
        
        # Score each diagram type based on keyword matches
        scores = {dtype: sum(1 for kw in keywords if kw in query)
                 for dtype, keywords in type_keywords.items()}
        
        # Return the type with highest score, default to FLOWCHART if no clear match
        return max(scores.items(), key=lambda x: x[1])[0] if any(scores.values()) else DiagramType.FLOWCHART
    
    def _format_diagram_prompt(self, query: str, diagram_type: DiagramType) -> str:
        """Format the complete prompt for diagram generation"""
        base_prompt = self.system_prompts.get(diagram_type, self.system_prompts[DiagramType.FLOWCHART])
        
        return f"""Create a Mermaid diagram based on this description:
                  {query}
                  
                  {base_prompt}"""