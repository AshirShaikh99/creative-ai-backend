import os
import tempfile
import numpy as np
from typing import Dict, Any, Tuple
import asyncio
import soundfile as sf
from app.config.config import get_settings
import logging
from deepgram import Deepgram, DeepgramClientOptions
from io import BytesIO
from pydub import AudioSegment

settings = get_settings()
logger = logging.getLogger(__name__)

# Global variable to store the Deepgram client
_deepgram_client = None


def get_deepgram_client():
    """
    Initialize and cache the Deepgram client.
    """
    global _deepgram_client
    if _deepgram_client is None:
        logger.info("Initializing Deepgram client")
        api_key = settings.DEEPGRAM_API_KEY
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY not found in environment variables or settings")
        
        options = DeepgramClientOptions(api_key=api_key)
        _deepgram_client = Deepgram(options)
    
    return _deepgram_client


async def transcribe_audio_chunk(audio_data: bytes) -> Tuple[str, float]:
    """
    Transcribe an audio chunk using Deepgram.
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        Tuple containing transcribed text and confidence score
    """
    client = get_deepgram_client()
    
    # Create a temporary file to save the audio data
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
        temp_filename = temp_file.name
        
        try:
            # Convert bytes to audio segment
            audio = AudioSegment.from_file(BytesIO(audio_data))
            
            # Export to WAV format
            audio.export(temp_filename, format="wav")
            
            # Read the audio file
            with open(temp_filename, "rb") as audio_file:
                audio_bytes = audio_file.read()
            
            # Configure transcription options for Deepgram SDK 3.2.0
            options = {
                "smart_format": True,
                "model": settings.DEEPGRAM_MODEL,
                "language": "en",
                "diarize": False,
                "punctuate": True,
                "utterances": True
            }
            
            # Run transcription using Deepgram's updated API
            response = await client.transcription.prerecorded.transcribe(
                {"buffer": audio_bytes},
                options
            )
            
            # Extract transcription from the response
            try:
                # Access the transcript from the response
                transcription = response["results"]["channels"][0]["alternatives"][0]["transcript"]
                
                # Get confidence (if available)
                confidence = 0.0
                if "confidence" in response["results"]["channels"][0]["alternatives"][0]:
                    confidence = response["results"]["channels"][0]["alternatives"][0]["confidence"]
                
                return transcription, confidence
            except (KeyError, IndexError) as e:
                logger.error(f"Error parsing Deepgram response: {str(e)}")
                return "", 0.0
            
        except Exception as e:
            logger.error(f"Error transcribing audio with Deepgram: {str(e)}")
            return "", 0.0


async def process_streaming_audio(audio_stream):
    """
    Process streaming audio data from WebSocket.
    
    Args:
        audio_stream: Async generator yielding audio chunks
        
    Yields:
        Transcription results
    """
    buffer = bytearray()
    chunk_size = settings.AUDIO_CHUNK_SIZE
    
    async for chunk in audio_stream:
        buffer.extend(chunk)
        
        # Process when we have enough data
        if len(buffer) >= chunk_size:
            text, confidence = await transcribe_audio_chunk(bytes(buffer))
            buffer.clear()
            
            if text:
                yield {
                    "text": text,
                    "confidence": confidence,
                    "is_final": True
                }
