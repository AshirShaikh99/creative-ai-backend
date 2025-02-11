from pydantic import BaseModel
from enum import Enum
from dataclasses import dataclass

class DiagramType(Enum):
    FLOWCHART = "flowchart"
    SEQUENCE = "sequenceDiagram"
    CLASS = "classDiagram"
    STATE = "stateDiagram-v2"
    ER = "erDiagram"
    GANTT = "gantt"

class DiagramRequest(BaseModel):
    user_id: str
    message: str

@dataclass
class MermaidResponse:
    diagram_type: DiagramType
    syntax: str
    description: str

# File: app/service/mermaid_service.py
from typing import Dict
from app.models.mermain_models import DiagramType, MermaidResponse

class MermaidGenerator:
    def __init__(self):
        self.system_prompts = {
            DiagramType.FLOWCHART: """Generate a Mermaid flowchart diagram syntax based on the user's description.
                                    Focus on clear node connections and logical flow.""",
            DiagramType.SEQUENCE: """Create a Mermaid sequence diagram showing interaction between components.
                                   Include proper actor definitions and message flows.""",
            DiagramType.STATE: """Design a Mermaid state diagram showing state transitions and conditions.
                                Use clear state definitions and transition labels."""
        }
    
    def _detect_diagram_type(self, query: str) -> DiagramType:
        """Detect the most appropriate diagram type based on user query"""
        query = query.lower()
        
        if any(keyword in query for keyword in ["flow", "process", "steps", "workflow"]):
            return DiagramType.FLOWCHART
        elif any(keyword in query for keyword in ["sequence", "interaction", "communication"]):
            return DiagramType.SEQUENCE
        elif any(keyword in query for keyword in ["state", "status", "transition"]):
            return DiagramType.STATE
        
        return DiagramType.FLOWCHART
    
    def _format_diagram_prompt(self, query: str, diagram_type: DiagramType) -> str:
        """Format the prompt for diagram generation"""
        base_prompt = self.system_prompts.get(diagram_type, self.system_prompts[DiagramType.FLOWCHART])
        
        return f"""Based on this description, generate valid Mermaid diagram syntax:
                  Description: {query}
                  
                  Requirements:
                  1. Use {diagram_type.value} syntax
                  2. Include only valid Mermaid syntax
                  3. Make the diagram clear and readable
                  4. Add appropriate labels and descriptions
                  5. Use proper indentation
                  
                  Generate only the Mermaid syntax without any additional text or explanations."""
