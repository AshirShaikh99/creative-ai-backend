import os
import tempfile
import numpy as np
from faster_whisper import WhisperModel
from pydub import AudioSegment
from typing import Dict, Any, Tuple
import asyncio
import soundfile as sf
from app.config.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

# Global variable to store the loaded model
_whisper_model = None


def get_whisper_model():
    """
    Load and cache the Faster Whisper model.
    """
    global _whisper_model
    if _whisper_model is None:
        logger.info(f"Loading Faster Whisper model: {settings.WHISPER_MODEL}")
        # Use CUDA if available, otherwise CPU
        device = "cuda" if os.environ.get("USE_CUDA", "0") == "1" else "cpu"
        compute_type = "float16" if device == "cuda" else "float32"
        
        _whisper_model = WhisperModel(
            model_size_or_path=settings.WHISPER_MODEL,
            device=device,
            compute_type=compute_type
        )
    return _whisper_model


async def transcribe_audio_chunk(audio_data: bytes) -> Tuple[str, float]:
    """
    Transcribe an audio chunk using Faster Whisper.
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        Tuple containing transcribed text and confidence score
    """
    model = get_whisper_model()
    
    # Create a temporary file to save the audio data
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
        temp_filename = temp_file.name
        
        try:
            # Save raw audio bytes to file
            with open(temp_filename, "wb") as f:
                f.write(audio_data)
            
            # Load the audio file using pydub
            audio = AudioSegment.from_file(temp_filename)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(temp_filename, format="wav")
            
            # Run transcription using Faster Whisper
            segments, info = await asyncio.to_thread(
                model.transcribe,
                temp_filename,
                language="en",
                vad_filter=True,  # Voice activity detection for better results
                vad_parameters=dict(min_silence_duration_ms=500)  # Adjust for your needs
            )
            
            # Extract text and confidence
            text_parts = []
            confidence_values = []
            
            # Process segments - compatible with both generator and async iterator
            # The newer version of faster-whisper returns a regular generator, not an async iterator
            for segment in segments:
                text_parts.append(segment.text)
                confidence_values.append(segment.avg_logprob)  # logprob as confidence
            
            # Join all text parts
            transcription = " ".join(text_parts).strip()
            
            # Calculate average confidence (convert from log probabilities)
            avg_confidence = np.exp(np.mean(confidence_values)) if confidence_values else 0.0
            
            return transcription, float(avg_confidence)
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
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
