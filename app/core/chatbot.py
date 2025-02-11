from typing import Dict, Optional, List, Union
from app.models.model import Message, ChatSession, DiagramResponse
from uuid import UUID
from groq import AsyncGroq
from app.config.config import get_settings
from app.service.qdrant_service import QdrantService
from functools import lru_cache
import hashlib
from enum import Enum

class DiagramType(Enum):
    FLOWCHART = "flowchart"
    SEQUENCE = "sequenceDiagram"
    STATE = "stateDiagram-v2"
    CLASS = "classDiagram"
    ER = "erDiagram"
    GANTT = "gantt"

class CreativeAIChatbot:
    def __init__(self):
        self.sessions: Dict[UUID, ChatSession] = {}
        settings = get_settings()
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.qdrant_client = QdrantService.get_instance()
        
        # System prompts for different diagram types
        self.diagram_prompts = {
            DiagramType.FLOWCHART: "Generate a Mermaid flowchart diagram syntax.",
            DiagramType.SEQUENCE: "Create a Mermaid sequence diagram syntax.",
            DiagramType.STATE: "Design a Mermaid state diagram syntax.",
            DiagramType.CLASS: "Create a Mermaid class diagram syntax.",
            DiagramType.ER: "Generate a Mermaid ER diagram syntax.",
            DiagramType.GANTT: "Create a Mermaid Gantt chart syntax."
        }

    def _detect_diagram_type(self, query: str) -> DiagramType:
        query = query.lower()
        if any(word in query for word in ["flow", "process", "workflow"]):
            return DiagramType.FLOWCHART
        elif any(word in query for word in ["sequence", "interaction"]):
            return DiagramType.SEQUENCE
        elif any(word in query for word in ["state", "status"]):
            return DiagramType.STATE
        elif any(word in query for word in ["class", "object"]):
            return DiagramType.CLASS
        elif any(word in query for word in ["entity", "database", "er"]):
            return DiagramType.ER
        elif any(word in query for word in ["timeline", "schedule", "gantt"]):
            return DiagramType.GANTT
        return DiagramType.FLOWCHART

    async def generate_diagram(self, message: str, options: Optional[Dict] = None) -> DiagramResponse:
        try:
            diagram_type = self._detect_diagram_type(message)
            system_prompt = self.diagram_prompts[diagram_type]
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            completion = await self.groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=messages,
                temperature=0.7
            )
            
            syntax = completion.choices[0].message.content.strip()
            
            # Generate description
            description_prompt = f"Briefly describe this diagram in one sentence:\n{syntax}"
            description = await self._generate_description(description_prompt)
            
            return DiagramResponse(
                diagram_type=diagram_type.value,
                syntax=syntax,
                description=description,
                metadata={
                    "options": options or {},
                    "model": "mixtral-8x7b-32768",
                    "tokens": completion.usage.total_tokens
                }
            )
        except Exception as e:
            raise Exception(f"Error generating diagram: {str(e)}")

    async def _generate_description(self, prompt: str) -> str:
        completion = await self.groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return completion.choices[0].message.content.strip()

    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[UUID] = None,
        generate_diagram: bool = False
    ) -> Union[ChatSession, DiagramResponse]:
        if generate_diagram:
            return await self.generate_diagram(message)
            
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
        else:
            session = ChatSession(user_id=user_id)
            self.sessions[session.id] = session
        
        user_message = Message(content=message, role="user")
        session.messages.append(user_message)
        
        try:
            completion = await self.groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": m.role, "content": m.content} for m in session.messages],
                temperature=0.7
            )
            
            response = completion.choices[0].message.content
            
            assistant_message = Message(content=response, role="assistant")
            session.messages.append(assistant_message)
            
            return session
        except Exception as e:
            raise Exception(f"Error processing message: {str(e)}")

# Create singleton instance
chatbot = CreativeAIChatbot()