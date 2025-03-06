#!/usr/bin/env python
"""
Unit tests for Speech-to-Text functionality.
"""

import os
import sys
import pytest
import asyncio
import numpy as np
import tempfile
import soundfile as sf
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import STT module
from app.service.speech_to_text import transcribe_audio_chunk, get_whisper_model


@pytest.fixture
def sample_audio_file():
    """Create a sample audio file for testing."""
    # Create a simple sine wave audio file
    sample_rate = 16000
    duration = 2.0  # seconds
    frequency = 440.0  # Hz
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Convert to int16
    audio = (audio * 32767).astype(np.int16)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_filename = temp_file.name
        sf.write(temp_filename, audio, sample_rate, 'PCM_16')
    
    yield temp_filename
    
    # Clean up
    if os.path.exists(temp_filename):
        os.unlink(temp_filename)


@pytest.mark.asyncio
async def test_get_whisper_model():
    """Test that the whisper model is loaded correctly."""
    model = get_whisper_model()
    assert model is not None, "Whisper model should not be None"


@pytest.mark.asyncio
async def test_transcribe_empty_audio():
    """Test transcription with empty audio bytes."""
    # Create an empty audio file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_filename = temp_file.name
        # Write an empty WAV file (just header)
        sf.write(temp_filename, np.array([]), 16000, 'PCM_16')
    
    try:
        # Read the file as bytes
        with open(temp_filename, "rb") as f:
            audio_data = f.read()
        
        # Transcribe
        text, confidence = await transcribe_audio_chunk(audio_data)
        
        # Should get empty string with low confidence for empty audio
        assert text == "", "Empty audio should result in empty transcription"
        assert confidence <= 0.1, "Empty audio should have low confidence"
    
    finally:
        # Clean up
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)


@pytest.mark.asyncio
async def test_transcribe_with_synthetic_audio(sample_audio_file):
    """Test transcription with synthetic audio."""
    # Read the file as bytes
    with open(sample_audio_file, "rb") as f:
        audio_data = f.read()
    
    # Transcribe
    text, confidence = await transcribe_audio_chunk(audio_data)
    
    # For a sine wave, we don't expect meaningful transcription
    # But the function should run without errors
    assert isinstance(text, str), "Transcription should return a string"
    assert isinstance(confidence, float), "Confidence should be a float"


@pytest.mark.skipif(
    "CI" in os.environ, 
    reason="Skipping text audio generation in CI environment"
)
@pytest.mark.asyncio
async def test_transcribe_with_speech_audio():
    """Test transcription with real speech audio."""
    # This test requires real speech audio, which we generate
    # Skip this test if we're in a CI environment
    
    try:
        # Try to import text-to-speech library
        from gtts import gTTS
        
        # Create test speech audio
        text_to_speak = "This is a test of the speech recognition system"
        tts = gTTS(text=text_to_speak, lang="en", slow=False)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_mp3 = temp_file.name
        
        tts.save(temp_mp3)
        
        # Convert MP3 to WAV
        try:
            from pydub import AudioSegment
            sound = AudioSegment.from_mp3(temp_mp3)
            sound = sound.set_frame_rate(16000)  # Set to 16kHz
            sound = sound.set_channels(1)  # Mono
            temp_wav = temp_mp3.replace(".mp3", ".wav")
            sound.export(temp_wav, format="wav")
        except ImportError:
            pytest.skip("pydub not installed, cannot convert MP3 to WAV")
            return
        
        # Read the file as bytes
        with open(temp_wav, "rb") as f:
            audio_data = f.read()
        
        # Transcribe
        text, confidence = await transcribe_audio_chunk(audio_data)
        
        # The transcription should contain some of the original words
        words = text_to_speak.lower().split()
        transcribed_words = text.lower().split()
        
        # Check at least some words match (allowing for some errors in transcription)
        common_words = set(words).intersection(set(transcribed_words))
        assert len(common_words) > 0, "Transcription should contain some of the original words"
        
        # Check confidence
        assert confidence > 0.5, "Confidence for clear speech should be high"
        
        # Clean up
        if os.path.exists(temp_mp3):
            os.unlink(temp_mp3)
        if os.path.exists(temp_wav):
            os.unlink(temp_wav)
            
    except ImportError:
        pytest.skip("gtts not installed, cannot generate speech audio")


if __name__ == "__main__":
    # Run all tests
    pytest.main(["-xvs", __file__])
