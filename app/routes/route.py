from fastapi import APIRouter, HTTPException, Header, Depends
from app.models.model import ChatRequest, ChatResponse, DiagramRequest, DiagramResponse
from app.core.chatbot import chatbot
from app.core.diagram_chat import diagram
from uuid import UUID
from typing import List
from app.config.config import get_settings

settings = get_settings()
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Header(..., description="User ID for the chat session")
):
    try:
        session = await chatbot.process_message(
            user_id=user_id,
            message=request.message,
            session_id=request.session_id
        )
        
        return ChatResponse(
            message=session.messages[-1].content,
            session_id=session.id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/diagram", response_model=DiagramResponse)
async def generate_diagram(
    request: DiagramRequest,
    user_id: str = Header(..., description="User ID for the diagram generation")
):
    try:
        return await diagram.generate_diagram(
            message=request.message,
            options=request.options
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}", response_model=List[dict])
async def get_chat_history(
    session_id: UUID,
    user_id: str = Header(..., description="User ID for authentication")
):
    if session_id not in chatbot.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chatbot.sessions[session_id]
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    return session.messages
