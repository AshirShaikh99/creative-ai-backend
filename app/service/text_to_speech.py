import os
import tempfile
import asyncio
import logging
from pathlib import Path
import soundfile as sf
import numpy as np
from typing import Dict, Any, Optional, Tuple
import io

from elevenlabs import generate, save, set_api_key, Voice, VoiceSettings
from elevenlabs.api import Models
from app.config.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize the ElevenLabs API key
api_key = settings.ELEVENLABS_API_KEY
if api_key:
    set_api_key(api_key)
else:
    logger.warning("ELEVENLABS_API_KEY not set in settings or environment variables")

# Default voice settings for natural, mentor-like speech
default_voice_settings = VoiceSettings(
    stability=0.75,
    similarity_boost=0.75,
    style=0.0,
    use_speaker_boost=True
)


async def text_to_speech(text: str, voice_id: str = None) -> Tuple[bytes, int]:
    """
    Convert text to speech using ElevenLabs.
    
    Args:
        text: The text to convert to speech
        voice_id: ElevenLabs voice ID or name (uses default from settings if not specified)
        
    Returns:
        Tuple containing audio data as bytes and sample rate
    """
    voice_id = voice_id or settings.ELEVENLABS_VOICE_ID
    
    if not api_key:
        logger.error("ELEVENLABS_API_KEY not available. Cannot generate speech.")
        return bytes(), settings.AUDIO_SAMPLE_RATE
    
    try:
        # Generate audio using ElevenLabs API
        audio_data = await asyncio.to_thread(
            generate,
            text=text,
            voice=voice_id,
            model=Models.ELEVEN_MULTILINGUAL_V2,  # Using their multilingual v2 model for better quality
            output_format="wav",
            voice_settings=default_voice_settings
        )
        
        # Save to a temporary file to get the proper WAV format
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
            await asyncio.to_thread(save, audio_data, temp_file.name)
            
            # Read wav file to get proper format and sample rate
            audio, sample_rate = sf.read(temp_file.name)
            
            # Convert back to bytes for streaming
            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format='WAV')
            buffer.seek(0)
            wav_bytes = buffer.read()
            
            return wav_bytes, sample_rate
        
    except Exception as e:
        logger.error(f"Error in ElevenLabs text-to-speech conversion: {str(e)}")
        # Return empty audio in case of error
        return bytes(), settings.AUDIO_SAMPLE_RATE


async def stream_text_to_speech(text: str, chunk_size: int = 1024, voice_id: str = None):
    """
    Stream audio data from text-to-speech conversion.
    
    Args:
        text: The text to convert to speech
        chunk_size: The size of audio chunks to stream
        voice_id: ElevenLabs voice ID or name (uses default from settings if not specified)
        
    Yields:
        Audio data chunks
    """
    voice_id = voice_id or settings.ELEVENLABS_VOICE_ID
    audio_bytes, _ = await text_to_speech(text, voice_id)
    
    # Stream the audio in chunks
    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i+chunk_size]
        yield chunk
        # Add a small delay to simulate real-time streaming
        await asyncio.sleep(0.01)
