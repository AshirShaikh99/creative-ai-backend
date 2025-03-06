import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable

from app.service.speech_to_text import transcribe_audio_chunk
from app.service.response_generator import generate_response, stream_response
from app.service.text_to_speech import text_to_speech, stream_text_to_speech
from app.service.livekit_service import (
    create_room, 
    get_room_token,
    setup_audio_processor,
    close_session
)

logger = logging.getLogger(__name__)

# Store active conversations
active_conversations: Dict[str, Dict[str, Any]] = {}


async def handle_transcription(audio_data: bytes, session_id: str):
    """
    Handle transcription of audio data.
    
    Args:
        audio_data: Audio data bytes
        session_id: Session identifier
    """
    if session_id not in active_conversations:
        logger.warning(f"Session {session_id} not found for transcription")
        return
    
    # Transcribe the audio
    text, confidence = await transcribe_audio_chunk(audio_data)
    
    if not text or confidence < 0.6:  # Threshold for confidence
        return
    
    # Store the transcription
    conversation = active_conversations[session_id]
    if "transcription_buffer" not in conversation:
        conversation["transcription_buffer"] = ""
    
    conversation["transcription_buffer"] += text + " "
    
    # Check if the transcription contains a stopping pattern (like silence or end of sentence)
    if "." in text or "?" in text or "!" in text or len(conversation["transcription_buffer"]) > 200:
        # Process the complete utterance
        await process_utterance(session_id)


async def process_utterance(session_id: str):
    """
    Process a complete user utterance.
    
    Args:
        session_id: Session identifier
    """
    if session_id not in active_conversations:
        logger.warning(f"Session {session_id} not found for utterance processing")
        return
    
    conversation = active_conversations[session_id]
    transcription = conversation.get("transcription_buffer", "").strip()
    
    if not transcription:
        return
    
    # Reset the buffer
    conversation["transcription_buffer"] = ""
    
    # Add to conversation history
    if "history" not in conversation:
        conversation["history"] = []
    
    conversation["history"].append({"role": "user", "content": transcription})
    
    # Generate AI response
    response = await generate_response(
        query=transcription,
        conversation_history=conversation["history"],
        session_id=session_id
    )
    
    # Add to conversation history
    conversation["history"].append({"role": "assistant", "content": response})
    
    # Convert to speech
    audio_bytes, sample_rate = await text_to_speech(response)
    
    # Send the audio response back through LiveKit
    if "response_callback" in conversation:
        await conversation["response_callback"](response, audio_bytes, session_id)


async def initialize_voice_agent(
    user_id: str,
    room_name: Optional[str] = None,
    response_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Initialize a voice agent session.
    
    Args:
        user_id: User identifier
        room_name: Optional room name (generates one if not provided)
        response_callback: Callback for handling AI responses
        
    Returns:
        Session information including session_id, room_name, and token
    """
    # Generate a session ID
    session_id = str(uuid.uuid4())
    
    # Generate a room name if not provided
    if not room_name:
        room_name = f"voice-agent-{session_id[:8]}"
    
    # Create the LiveKit room
    await create_room(room_name)
    
    # Generate a token for the user
    token = await get_room_token(
        user_id=user_id,
        room_name=room_name,
        metadata={"session_id": session_id}
    )
    
    # Store the conversation context
    active_conversations[session_id] = {
        "user_id": user_id,
        "room_name": room_name,
        "history": [],
        "transcription_buffer": "",
        "response_callback": response_callback
    }
    
    # Set up the audio processor
    await setup_audio_processor(
        session_id=session_id,
        room_name=room_name,
        transcription_callback=handle_transcription,
        response_callback=response_callback
    )
    
    return {
        "session_id": session_id,
        "room_name": room_name,
        "token": token
    }


async def terminate_voice_agent(session_id: str) -> bool:
    """
    Terminate a voice agent session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        True if successful, False otherwise
    """
    success = await close_session(session_id)
    
    if success and session_id in active_conversations:
        del active_conversations[session_id]
        return True
    
    return False
