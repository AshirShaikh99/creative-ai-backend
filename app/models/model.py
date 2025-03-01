# File: app/models/model.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

class Message(BaseModel):
    content: str
    role: str
    timestamp: datetime = datetime.now()

class ChatSession(BaseModel):
    id: UUID = uuid4()
    user_id: str
    messages: List[Message] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None
    deep_research: bool = False
    collection_name: Optional[str] = None  # Add this field

class ChatResponse(BaseModel):
    message: str
    session_id: UUID

class ResearchResult(BaseModel):
    topic: str
    findings: List[Dict[str, Any]] = []  # Add default empty list
    sources: List[str] = []  # Add default empty list
    confidence_score: float = 0.0  # Add default value
    metadata: Dict[str, Any] = {}  # Add default empty dict

class ResearchTopic(BaseModel):
    query: str
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class DiagramRequest(BaseModel):
    message: str
    options: Optional[Dict[str, Any]] = None

class DiagramResponse(BaseModel):
    diagram_type: str
    syntax: str
    description: str
    metadata: Optional[Dict[str, Any]] = None