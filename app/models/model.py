from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4


class Message(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    role: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatSession(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    messages: List[Message] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)



class ChatRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None

class ChatResponse(BaseModel):
    message: str
    session_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    role: str = "assistant"