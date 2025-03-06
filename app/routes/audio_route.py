from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List

from app.models.audio_models import (
    AudioStreamRequest,
    LiveKitTokenRequest,
    LiveKitTokenResponse,
    TranscriptionResult,
    AIResponse
)
from app.utils.livekit_auth import create_livekit_token
from app.service.voice_agent_service import (
    initialize_voice_agent,
    terminate_voice_agent,
    active_conversations
)
from app.service.livekit_service import get_room_token, create_room

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/token", response_model=LiveKitTokenResponse)
async def generate_token(request: LiveKitTokenRequest):
    """Generate a LiveKit token for joining a room."""
    try:
        # Create room if it doesn't exist
        await create_room(request.room_name)
        
        # Generate token
        token = create_livekit_token(
            user_id=request.user_id,
            room_name=request.room_name,
            metadata=request.metadata,
            can_publish=request.can_publish,
            can_subscribe=request.can_subscribe,
            ttl=request.ttl
        )
        
        return {
            "token": token,
            "room_name": request.room_name,
            "user_id": request.user_id
        }
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {str(e)}"
        )


@router.post("/initialize", status_code=status.HTTP_201_CREATED)
async def initialize_stream(request: AudioStreamRequest):
    """Initialize a voice agent session."""
    try:
        # Define the response callback for handling AI responses
        async def response_callback(text: str, audio_bytes: bytes, session_id: str):
            # This function will handle sending AI responses back through LiveKit
            # The implementation depends on how you want to send the audio back to the client
            logger.info(f"AI response for session {session_id}: {text[:50]}...")
        
        # Initialize the voice agent
        session_info = await initialize_voice_agent(
            user_id=request.user_id,
            room_name=request.room_name,
            response_callback=response_callback
        )
        
        return {
            "status": "success",
            "message": "Voice agent session initialized",
            "session_id": session_info["session_id"],
            "room_name": session_info["room_name"],
            "token": session_info["token"]
        }
        
    except Exception as e:
        logger.error(f"Error initializing stream: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize stream: {str(e)}"
        )


@router.delete("/terminate/{session_id}", status_code=status.HTTP_200_OK)
async def terminate_stream(session_id: str):
    """Terminate a voice agent session."""
    try:
        success = await terminate_voice_agent(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found or already terminated"
            )
        
        return {
            "status": "success",
            "message": f"Session {session_id} terminated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating stream: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to terminate stream: {str(e)}"
        )


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for bidirectional communication with the voice agent."""
    await websocket.accept()
    
    try:
        # Check if session exists
        if session_id not in active_conversations:
            await websocket.send_json({
                "type": "error",
                "message": f"Session {session_id} not found"
            })
            await websocket.close()
            return
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to voice agent"
        })
        
        # Define message handlers
        async def handle_text_message(data):
            """Handle text messages from client."""
            if "text" not in data:
                return
            
            # Process the text as if it were a transcription
            conversation = active_conversations[session_id]
            if "transcription_buffer" not in conversation:
                conversation["transcription_buffer"] = ""
            
            conversation["transcription_buffer"] = data["text"]
            
            # Process the utterance
            from app.service.voice_agent_service import process_utterance
            await process_utterance(session_id)
        
        # Listen for messages from client
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type", "")
                
                if message_type == "text":
                    await handle_text_message(message)
                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
