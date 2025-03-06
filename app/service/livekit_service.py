import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List
from livekit import rtc
from livekit.rtc import Room
from app.config.config import get_settings
from app.utils.livekit_auth import create_livekit_token

settings = get_settings()
logger = logging.getLogger(__name__)

# Store active sessions
active_sessions: Dict[str, Any] = {}


class AudioProcessor:
    """
    Helper class for processing audio in LiveKit sessions.
    """
    
    def __init__(self, session_id: str, transcription_callback, response_callback):
        self.session_id = session_id
        self.transcription_callback = transcription_callback
        self.response_callback = response_callback
        self.audio_buffer = bytearray()
        self.chunk_size = settings.AUDIO_CHUNK_SIZE
        self.room = None
        self.task = None
    
    async def start(self, room_name: str, token: str):
        """Start processing audio in a LiveKit room."""
        try:
            # Connect to the room
            self.room = Room()
            await self.room.connect(settings.LIVEKIT_WS_URL, token)
            logger.info(f"Connected to room {room_name} as {self.room.local_participant.identity}")
            
            # Set up listeners for participants
            self.room.on(rtc.RoomEvent.ParticipantConnected, self._on_participant_connected)
            self.room.on(rtc.RoomEvent.ParticipantDisconnected, self._on_participant_disconnected)
            
            # With newer LiveKit SDK, we don't need to manually register existing participants
            # The participant_connected event will be fired for each participant
            
            return True
        except Exception as e:
            logger.error(f"Error starting audio processor: {str(e)}")
            return False
    
    async def stop(self):
        """Stop the audio processor."""
        try:
            if self.task:
                self.task.cancel()
                
            if self.room:
                await self.room.disconnect()
                
            return True
        except Exception as e:
            logger.error(f"Error stopping audio processor: {str(e)}")
            return False
    
    def _on_participant_connected(self, participant):
        """Handle new participant connection."""
        asyncio.create_task(self._setup_participant(participant))
    
    def _on_participant_disconnected(self, participant):
        """Handle participant disconnection."""
        logger.info(f"Participant {participant.identity} disconnected")
    
    async def _setup_participant(self, participant):
        """Set up listeners for participant's audio tracks."""
        logger.info(f"Setting up participant {participant.identity}")
        
        # Instead of using participant.on(), directly process available tracks
        # and set up room event handlers to catch future track subscriptions
        
        # Process any existing tracks
        for publication in participant.tracks.values():
            if publication.subscribed and publication.track:
                await self._process_track(publication.track, publication, participant)
        
        # Make sure room has event handlers for future track subscriptions
        if not hasattr(self, '_track_subscription_handler_set'):
            self.room.on(rtc.RoomEvent.TrackSubscribed, self._on_track_subscribed)
            self._track_subscription_handler_set = True
    
    def _on_track_subscribed(self, track, publication, participant):
        """Handle new track subscription."""
        asyncio.create_task(self._process_track(track, publication, participant))
    
    async def _process_track(self, track, publication, participant):
        """Process a track after subscription."""
        if track.kind == rtc.TrackKind.AUDIO:
            logger.info(f"Processing audio track from {participant.identity}")
            # Set up data handler for audio track
            # Note: The Python SDK may have a different way to handle audio data
            # Instead of track.on("data"), we need to use the appropriate SDK method
            # This depends on the specific version of the LiveKit Python SDK
            try:
                track.add_data_listener(self._process_audio_data)
                logger.info(f"Added data listener for track from {participant.identity}")
            except AttributeError as e:
                logger.error(f"Error adding data listener: {str(e)}. The SDK may not support this method.")
                # Alternative approach - check SDK documentation for the correct method
    
    def _process_audio_data(self, data):
        """Process incoming audio data."""
        self.audio_buffer.extend(data)
        
        # Process when we have enough data
        if len(self.audio_buffer) >= self.chunk_size:
            # Pass to transcription callback - handle as async
            buffer_copy = bytes(self.audio_buffer)
            self.audio_buffer.clear()
            
            # Call the transcription callback in an async-safe way
            asyncio.create_task(self._safe_transcription_callback(buffer_copy))
    
    async def _safe_transcription_callback(self, audio_data):
        """Safely call the transcription callback."""
        try:
            if asyncio.iscoroutinefunction(self.transcription_callback):
                await self.transcription_callback(audio_data, self.session_id)
            else:
                self.transcription_callback(audio_data, self.session_id)
        except Exception as e:
            logger.error(f"Error in transcription callback: {str(e)}")
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to the room."""
        if not self.room or not self.room.local_participant:
            logger.error("Cannot send audio - no active room connection")
            return False
        
        try:
            # Create a local audio track if needed
            if not hasattr(self, 'audio_track'):
                # Get the local participant
                local_participant = self.room.local_participant
                
                # Create an audio track
                track_options = rtc.LocalTrackOptions(name="ai-voice")
                self.audio_track = await local_participant.create_audio_track(track_options)
            
            # Send the audio data
            await self.audio_track.write_data(audio_data)
            return True
        except Exception as e:
            logger.error(f"Error sending audio: {str(e)}")
            return False


async def create_room(room_name: str) -> str:
    """
    Create a LiveKit room or return an existing one.
    
    Args:
        room_name: Name of the room to create
        
    Returns:
        Room name (same as input if successful)
    """
    try:
        # For demo purposes, we'll just return the room name 
        # without actually creating it on the LiveKit server
        # The LiveKit token will still work for client connections
        logger.info(f"Using LiveKit room: {room_name}")
        return room_name
        
    except Exception as e:
        logger.error(f"Error creating LiveKit room: {str(e)}")
        raise


async def get_room_token(
    user_id: str,
    room_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    can_publish: bool = True,
    can_subscribe: bool = True,
    ttl: int = 3600  # 1 hour in seconds
) -> str:
    """
    Get a token for a LiveKit room.
    
    Args:
        user_id: Unique identifier for the user
        room_name: Name of the LiveKit room
        metadata: Additional metadata to include in the token
        can_publish: Whether the user can publish media
        can_subscribe: Whether the user can subscribe to others' media
        ttl: Token time-to-live in seconds
        
    Returns:
        JWT token string
    """
    token = create_livekit_token(
        user_id=user_id,
        room_name=room_name,
        metadata=metadata,
        can_publish=can_publish,
        can_subscribe=can_subscribe,
        ttl=ttl
    )
    
    return token


async def setup_audio_processor(
    session_id: str,
    room_name: str,
    transcription_callback,
    response_callback
) -> bool:
    """
    Set up an audio processor in a LiveKit room.
    
    Args:
        session_id: Unique identifier for the session
        room_name: Name of the LiveKit room
        transcription_callback: Callback function for transcription
        response_callback: Callback function for AI responses
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create an agent token
        agent_token = create_livekit_token(
            user_id=f"agent-{session_id}",
            room_name=room_name,
            can_publish=True,
            can_subscribe=True
        )
        
        # Create the audio processor
        processor = AudioProcessor(
            session_id=session_id,
            transcription_callback=transcription_callback,
            response_callback=response_callback
        )
        
        # Start the processor
        success = await processor.start(room_name, agent_token)
        
        if success:
            # Store in active sessions
            active_sessions[session_id] = {
                "processor": processor,
                "room_name": room_name
            }
            
            logger.info(f"Set up audio processor for session {session_id} in room {room_name}")
            return True
        else:
            logger.error(f"Failed to start audio processor for session {session_id}")
            return False
        
    except Exception as e:
        logger.error(f"Error setting up audio processor: {str(e)}")
        return False


async def close_session(session_id: str) -> bool:
    """
    Close a LiveKit session.
    
    Args:
        session_id: Unique identifier for the session
        
    Returns:
        True if successful, False otherwise
    """
    if session_id in active_sessions:
        try:
            # Get the processor
            processor = active_sessions[session_id]["processor"]
            
            # Stop the processor
            await processor.stop()
            
            # Remove from active sessions
            del active_sessions[session_id]
            
            logger.info(f"Closed session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {str(e)}")
    
    return False


async def send_audio_to_room(session_id: str, audio_data: bytes) -> bool:
    """
    Send audio data to a LiveKit room.
    
    Args:
        session_id: Unique identifier for the session
        audio_data: Audio data bytes to send
        
    Returns:
        True if successful, False otherwise
    """
    if session_id not in active_sessions:
        logger.warning(f"Session {session_id} not found for sending audio")
        return False
    
    try:
        processor = active_sessions[session_id]["processor"]
        return await processor.send_audio(audio_data)
    except Exception as e:
        logger.error(f"Error sending audio to room: {str(e)}")
        return False
