from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AudioStreamRequest(BaseModel):
    """Request model for initiating an audio stream."""
    user_id: str
    room_name: Optional[str] = None
    session_id: Optional[str] = None


class LiveKitTokenRequest(BaseModel):
    """Request model for generating a LiveKit token."""
    user_id: str
    room_name: str
    metadata: Optional[Dict[str, Any]] = None
    can_publish: bool = True
    can_subscribe: bool = True
    ttl: int = 3600  # Token time-to-live in seconds (1 hour)


class LiveKitTokenResponse(BaseModel):
    """Response model for LiveKit token generation."""
    token: str
    room_name: str
    user_id: str


class TranscriptionResult(BaseModel):
    """Model for speech-to-text transcription results."""
    text: str
    confidence: float
    is_final: bool
    session_id: str


class AIResponse(BaseModel):
    """Model for AI-generated response."""
    text: str
    audio_url: Optional[str] = None
    session_id: str
