#!/usr/bin/env python
"""
Generate test audio files for testing the voice agent.
This script creates synthetic speech audio files using Google TTS or a local TTS engine.
"""

import os
import argparse
import tempfile
import numpy as np
import soundfile as sf

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


def create_test_audio_gtts(text, output_file, lang="en"):
    """Generate test audio using Google Text-to-Speech."""
    if not GTTS_AVAILABLE:
        raise ImportError("gTTS is not installed. Install it with: pip install gtts")
    
    print(f"Generating audio for text: '{text}'")
    tts = gTTS(text=text, lang=lang, slow=False)
    
    # Save as temporary MP3 (gTTS only outputs MP3)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_filename = temp_file.name
    
    tts.save(temp_filename)
    
    # Convert to WAV if needed
    if output_file.endswith(".wav"):
        try:
            from pydub import AudioSegment
            sound = AudioSegment.from_mp3(temp_filename)
            sound = sound.set_frame_rate(16000)  # Set to 16kHz
            sound = sound.set_channels(1)  # Mono
            sound = sound.set_sample_width(2)  # 16-bit
            sound.export(output_file, format="wav")
        except ImportError:
            print("Warning: pydub not installed, keeping MP3 format")
            output_file = output_file.replace(".wav", ".mp3")
            os.rename(temp_filename, output_file)
    else:
        os.rename(temp_filename, output_file)
    
    print(f"Audio saved to: {output_file}")
    return output_file


def create_test_audio_pyttsx3(text, output_file):
    """Generate test audio using pyttsx3 (offline TTS)."""
    if not PYTTSX3_AVAILABLE:
        raise ImportError("pyttsx3 is not installed. Install it with: pip install pyttsx3")
    
    print(f"Generating audio for text: '{text}'")
    engine = pyttsx3.init()
    
    # Configure voice properties
    engine.setProperty('rate', 150)  # Speed
    engine.setProperty('volume', 0.9)  # Volume (0 to 1)
    
    # Get available voices
    voices = engine.getProperty('voices')
    if voices:
        # Try to find an English voice
        english_voices = [v for v in voices if 'en' in v.languages]
        if english_voices:
            engine.setProperty('voice', english_voices[0].id)
    
    # Create temp file for initial save
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_filename = temp_file.name
    
    # Save to file
    engine.save_to_file(text, temp_filename)
    engine.runAndWait()
    
    # Convert to 16kHz mono 16-bit WAV
    try:
        import wave
        with wave.open(temp_filename, 'rb') as wf:
            framerate = wf.getframerate()
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
        
        # Convert to numpy array
        audio = np.frombuffer(frames, dtype=np.int16)
        
        # Resample to 16kHz if needed
        if framerate != 16000 or channels != 1:
            try:
                from scipy import signal
                if channels == 2:
                    # Convert stereo to mono by averaging channels
                    audio = audio.reshape(-1, 2).mean(axis=1).astype(np.int16)
                
                if framerate != 16000:
                    # Resample to 16kHz
                    audio = signal.resample_poly(audio, 16000, framerate).astype(np.int16)
            except ImportError:
                print("Warning: scipy not installed, keeping original sample rate")
        
        # Save processed audio
        sf.write(output_file, audio, 16000, 'PCM_16')
    except Exception as e:
        print(f"Warning: Error converting audio: {e}")
        # Fallback: just copy the file
        import shutil
        shutil.copy(temp_filename, output_file)
    
    # Clean up temp file
    os.unlink(temp_filename)
    
    print(f"Audio saved to: {output_file}")
    return output_file


def create_synthetic_audio(output_file, duration=5, frequency=440):
    """Generate a synthetic audio tone for testing."""
    print(f"Generating synthetic audio tone of {duration}s at {frequency}Hz")
    
    # Generate tone
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Add fade-in and fade-out
    fade_duration = 0.1  # seconds
    fade_samples = int(fade_duration * sample_rate)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    
    tone[:fade_samples] *= fade_in
    tone[-fade_samples:] *= fade_out
    
    # Add some silence
    silence_duration = 0.5  # seconds
    silence_samples = int(silence_duration * sample_rate)
    audio = np.concatenate((np.zeros(silence_samples), tone, np.zeros(silence_samples)))
    
    # Convert to int16
    audio = (audio * 32767).astype(np.int16)
    
    # Save to file
    sf.write(output_file, audio, sample_rate, 'PCM_16')
    
    print(f"Audio saved to: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Generate test audio files for voice agent testing")
    parser.add_argument("--output", default="test_audio.wav", help="Output audio file path")
    parser.add_argument("--text", default="Hello, this is a test of the voice agent system. Can you understand me?", 
                      help="Text to convert to speech")
    parser.add_argument("--method", choices=["gtts", "pyttsx3", "synthetic"], default="gtts", 
                      help="Method to generate audio")
    parser.add_argument("--duration", type=float, default=5, 
                      help="Duration in seconds (for synthetic audio)")
    parser.add_argument("--frequency", type=float, default=440, 
                      help="Frequency in Hz (for synthetic audio)")
    parser.add_argument("--lang", default="en", help="Language code (for gTTS)")
    
    args = parser.parse_args()
    
    try:
        if args.method == "gtts":
            if not GTTS_AVAILABLE:
                print("gTTS not available. Install with: pip install gtts")
                if PYTTSX3_AVAILABLE:
                    print("Falling back to pyttsx3")
                    args.method = "pyttsx3"
                else:
                    print("Falling back to synthetic audio")
                    args.method = "synthetic"
        
        if args.method == "pyttsx3":
            if not PYTTSX3_AVAILABLE:
                print("pyttsx3 not available. Install with: pip install pyttsx3")
                if GTTS_AVAILABLE:
                    print("Falling back to gTTS")
                    args.method = "gtts"
                else:
                    print("Falling back to synthetic audio")
                    args.method = "synthetic"
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Generate audio based on method
        if args.method == "gtts":
            create_test_audio_gtts(args.text, args.output, args.lang)
        elif args.method == "pyttsx3":
            create_test_audio_pyttsx3(args.text, args.output)
        elif args.method == "synthetic":
            create_synthetic_audio(args.output, args.duration, args.frequency)
        
        print(f"Test audio generated successfully: {args.output}")
    
    except Exception as e:
        print(f"Error generating test audio: {str(e)}")


if __name__ == "__main__":
    main()
