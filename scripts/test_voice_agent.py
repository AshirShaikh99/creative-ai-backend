#!/usr/bin/env python
"""
Test script for the voice agent system.
This script creates a voice agent session and allows testing through command line input.
"""

import asyncio
import argparse
import json
import os
import sys
import aiohttp
from pydub import AudioSegment
from pydub.playback import play
import sounddevice as sd
import soundfile as sf
import tempfile
import numpy as np
from dotenv import load_dotenv
import websockets

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Default API url
DEFAULT_API_URL = "http://localhost:8000"

# Audio recording parameters
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.5  # seconds
RECORD_DURATION = 5  # seconds


async def record_audio(duration=RECORD_DURATION):
    """Record audio from microphone."""
    print(f"Recording for {duration} seconds...")
    
    # Calculate frames
    frames = int(SAMPLE_RATE * duration)
    
    # Record audio
    recording = sd.rec(frames, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32')
    sd.wait()
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_filename = temp_file.name
        sf.write(temp_filename, recording, SAMPLE_RATE)
    
    print("Recording complete!")
    return temp_filename


async def play_audio_file(file_path):
    """Play audio file."""
    audio = AudioSegment.from_file(file_path)
    play(audio)


async def initialize_session(api_url, user_id):
    """Initialize a voice agent session."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{api_url}/api/audio/initialize",
            json={"user_id": user_id}
        ) as response:
            if response.status == 201:
                return await response.json()
            else:
                error = await response.text()
                raise Exception(f"Failed to initialize session: {error}")


async def terminate_session(api_url, session_id):
    """Terminate a voice agent session."""
    async with aiohttp.ClientSession() as session:
        async with session.delete(
            f"{api_url}/api/audio/terminate/{session_id}"
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.text()
                raise Exception(f"Failed to terminate session: {error}")


async def send_audio_to_agent(api_url, session_id, audio_file):
    """Connect to WebSocket and send audio to agent."""
    ws_url = f"{api_url.replace('http://', 'ws://').replace('https://', 'wss://')}/api/audio/ws/{session_id}"
    
    async with websockets.connect(ws_url) as websocket:
        # Wait for connection message
        response = await websocket.recv()
        print(f"Connected to voice agent: {response}")
        
        # Read audio file
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        # Send audio data (in a real app, you would chunk this)
        await websocket.send(audio_data)
        
        # Wait for response
        response = await websocket.recv()
        response_data = json.loads(response)
        
        if response_data.get("type") == "transcription":
            print(f"Transcription: {response_data.get('text')}")
        
        # Wait for AI response
        response = await websocket.recv()
        response_data = json.loads(response)
        
        if response_data.get("type") == "response":
            print(f"AI Response: {response_data.get('text')}")
            
            # If there's audio, save it to temp file and play
            if response_data.get("audio_data"):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_filename = temp_file.name
                    temp_file.write(response_data.get("audio_data").encode("latin1"))
                
                await play_audio_file(temp_filename)
                os.unlink(temp_filename)


async def text_mode(api_url, session_id):
    """Test the voice agent using text input."""
    ws_url = f"{api_url.replace('http://', 'ws://').replace('https://', 'wss://')}/api/audio/ws/{session_id}"
    
    async with websockets.connect(ws_url) as websocket:
        # Wait for connection message
        response = await websocket.recv()
        print(f"Connected to voice agent: {response}")
        
        while True:
            # Get text input
            text = input("You: ")
            if text.lower() in ["exit", "quit", "q"]:
                break
            
            # Send text
            await websocket.send(json.dumps({
                "type": "text",
                "text": text
            }))
            
            # Wait for AI response
            response = await websocket.recv()
            try:
                response_data = json.loads(response)
                
                if response_data.get("type") == "response":
                    print(f"AI: {response_data.get('text')}")
            except json.JSONDecodeError:
                print(f"Received non-JSON response: {response}")


async def main():
    parser = argparse.ArgumentParser(description="Test the voice agent system")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API URL")
    parser.add_argument("--user-id", default="test-user", help="User ID")
    parser.add_argument("--mode", choices=["audio", "text"], default="text", 
                        help="Test mode: audio (record and send) or text (text input)")
    
    args = parser.parse_args()
    
    try:
        # Initialize session
        print(f"Initializing session for user {args.user_id}...")
        session_info = await initialize_session(args.api_url, args.user_id)
        session_id = session_info["session_id"]
        print(f"Session initialized: {session_id}")
        
        try:
            if args.mode == "audio":
                # Record audio
                audio_file = await record_audio()
                
                # Send to agent
                await send_audio_to_agent(args.api_url, session_id, audio_file)
                
                # Clean up temp file
                os.unlink(audio_file)
            else:
                # Text mode
                await text_mode(args.api_url, session_id)
        
        finally:
            # Terminate session
            print("Terminating session...")
            await terminate_session(args.api_url, session_id)
            print("Session terminated")
    
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
