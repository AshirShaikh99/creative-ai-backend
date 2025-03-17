from fastapi import APIRouter, HTTPException, Header, Depends
from app.models.model import ChatRequest, ChatResponse, DiagramRequest, DiagramResponse
from app.core.chatbot import chatbot
from app.core.diagram_chat import diagram, DiagramType
from uuid import UUID
from typing import List, Dict, Any, Optional
from app.config.config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Header(..., description="User ID for authentication and session management")
):
    """
    Process a chat message and return a response
    """
    try:
        logger.info(f"Processing chat request for user: {user_id}, deep_research: {request.deep_research}")
        
        session = await chatbot.process_message(
            user_id=user_id,
            message=request.message,
            session_id=request.session_id,
            deep_research=request.deep_research
        )
        
        return ChatResponse(
            message=session.messages[-1].content,
            session_id=session.id
        )
    except Exception as e:
        logger.error(f"Chat error for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )

@router.post("/diagram", response_model=DiagramResponse)
async def generate_diagram(
    request: DiagramRequest,
    user_id: str = Header(..., description="User ID for the diagram generation")
):
    """
    Generate a diagram based on the user's message.
    For complex architecture diagrams (AI or software), returns structured data that can be 
    used for dynamic visualization on the frontend.
    """
    try:
        logger.info(f"Generating diagram for user: {user_id}, message: {request.message[:50]}...")
        
        diagram_response = await diagram.generate_diagram(
            message=request.message,
            options=request.options
        )
        
        # For architecture diagrams, extract structured data for frontend rendering
        if diagram_response.diagram_type in [DiagramType.AI_ARCHITECTURE.value, DiagramType.SOFTWARE_ARCHITECTURE.value]:
            try:
                if diagram_response.metadata and "raw_data" in diagram_response.metadata:
                    raw_data = diagram_response.metadata["raw_data"]
                    diagram_response.nodes = raw_data.get("nodes", [])
                    diagram_response.connections = raw_data.get("connections", [])
                    diagram_response.clusters = raw_data.get("clusters", [])
                    diagram_response.raw_structure = raw_data
            except Exception as e:
                logger.error(f"Error extracting architecture data: {str(e)}", exc_info=True)
        
        return diagram_response
    except Exception as e:
        logger.error(f"Diagram generation error for user {user_id}: {str(e)}", exc_info=True)
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
