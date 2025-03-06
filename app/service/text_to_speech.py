import os
import tempfile
import asyncio
import logging
from pathlib import Path
import soundfile as sf
import numpy as np
from typing import Dict, Any, Optional, Tuple

from kokoro.trainer import KokoroTTS
from app.config.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Global variable to store the loaded TTS model
_tts_model = None


def get_tts_model():
    """
    Load and cache the Kokoro TTS model.
    """
    global _tts_model
    if _tts_model is None:
        logger.info(f"Loading TTS model: {settings.TTS_MODEL_PATH}")
        _tts_model = KokoroTTS.from_pretrained(settings.TTS_MODEL_PATH)
    return _tts_model


async def text_to_speech(text: str, voice_id: str = "default") -> Tuple[bytes, int]:
    """
    Convert text to speech using Kokoro-82M.
    
    Args:
        text: The text to convert to speech
        voice_id: Voice identifier (if model supports multiple voices)
        
    Returns:
        Tuple containing audio data as bytes and sample rate
    """
    model = get_tts_model()
    
    try:
        # Generate audio
        result = await asyncio.to_thread(
            model.generate,
            text,
            speaker=voice_id if voice_id != "default" else None
        )
        
        audio_array = result["audio"]
        sample_rate = result["sampling_rate"]
        
        # Convert audio array to bytes
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
            sf.write(temp_file.name, audio_array, sample_rate, format='WAV')
            temp_file.seek(0)
            audio_bytes = temp_file.read()
        
        return audio_bytes, sample_rate
        
    except Exception as e:
        logger.error(f"Error in text-to-speech conversion: {str(e)}")
        # Return empty audio in case of error
        return bytes(), settings.AUDIO_SAMPLE_RATE


async def stream_text_to_speech(text: str, chunk_size: int = 1024, voice_id: str = "default"):
    """
    Stream audio data from text-to-speech conversion.
    
    Args:
        text: The text to convert to speech
        chunk_size: The size of audio chunks to stream
        voice_id: Voice identifier
        
    Yields:
        Audio data chunks
    """
    audio_bytes, _ = await text_to_speech(text, voice_id)
    
    # Stream the audio in chunks
    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i+chunk_size]
        yield chunk
        # Add a small delay to simulate real-time streaming
        await asyncio.sleep(0.01)
