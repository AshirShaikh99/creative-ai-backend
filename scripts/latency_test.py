#!/usr/bin/env python
"""
Latency testing script for the voice agent system.
This script measures the latency of various components of the voice agent.
"""

import asyncio
import argparse
import time
import os
import sys
import aiohttp
import json
import tempfile
import numpy as np
from pydub import AudioSegment
from pydub.playback import play
import sounddevice as sd
import soundfile as sf
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


class LatencyTester:
    def __init__(self, api_url, user_id):
        self.api_url = api_url
        self.user_id = user_id
        self.session_id = None
        self.results = {
            "stt_latency": [],
            "ai_response_latency": [],
            "tts_latency": [],
            "total_latency": []
        }
    
    async def initialize_session(self):
        """Initialize a voice agent session."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/api/audio/initialize",
                json={"user_id": self.user_id}
            ) as response:
                if response.status == 201:
                    response_data = await response.json()
                    self.session_id = response_data["session_id"]
                    return response_data
                else:
                    error = await response.text()
                    raise Exception(f"Failed to initialize session: {error}")
    
    async def terminate_session(self):
        """Terminate a voice agent session."""
        if not self.session_id:
            return
            
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.api_url}/api/audio/terminate/{self.session_id}"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    raise Exception(f"Failed to terminate session: {error}")
    
    async def test_latency(self, audio_file, iterations=5):
        """Test latency of the voice agent system."""
        if not self.session_id:
            raise ValueError("Session not initialized")
        
        ws_url = f"{self.api_url.replace('http://', 'ws://').replace('https://', 'wss://')}/api/audio/ws/{self.session_id}"
        
        for i in range(iterations):
            print(f"\nTest iteration {i+1}/{iterations}")
            
            async with websockets.connect(ws_url) as websocket:
                # Wait for connection message
                response = await websocket.recv()
                print(f"Connected to voice agent: {response}")
                
                # Read audio file
                with open(audio_file, "rb") as f:
                    audio_data = f.read()
                
                # Record start time
                start_time = time.time()
                send_time = start_time
                
                # Send audio data
                await websocket.send(audio_data)
                print(f"Audio sent at: {send_time - start_time:.3f}s")
                
                # Wait for transcription
                response = await websocket.recv()
                transcription_time = time.time()
                response_data = json.loads(response)
                
                if response_data.get("type") == "transcription":
                    print(f"Transcription received: {response_data.get('text')}")
                    print(f"STT latency: {transcription_time - send_time:.3f}s")
                    self.results["stt_latency"].append(transcription_time - send_time)
                
                # Wait for AI response
                response = await websocket.recv()
                ai_response_time = time.time()
                response_data = json.loads(response)
                
                if response_data.get("type") == "response":
                    print(f"AI response received: {response_data.get('text')}")
                    print(f"AI response latency: {ai_response_time - transcription_time:.3f}s")
                    self.results["ai_response_latency"].append(ai_response_time - transcription_time)
                
                # If audio response is included
                if response_data.get("audio_data"):
                    tts_time = time.time()
                    print(f"TTS latency: {tts_time - ai_response_time:.3f}s")
                    self.results["tts_latency"].append(tts_time - ai_response_time)
                
                end_time = time.time()
                total_latency = end_time - start_time
                print(f"Total latency: {total_latency:.3f}s")
                self.results["total_latency"].append(total_latency)
            
            # Wait between iterations
            if i < iterations - 1:
                await asyncio.sleep(1)
    
    def print_results(self):
        """Print latency test results."""
        print("\n==== LATENCY TEST RESULTS ====")
        
        # STT Latency
        if self.results["stt_latency"]:
            avg_stt = np.mean(self.results["stt_latency"])
            std_stt = np.std(self.results["stt_latency"])
            min_stt = np.min(self.results["stt_latency"])
            max_stt = np.max(self.results["stt_latency"])
            print(f"Speech-to-Text Latency:")
            print(f"  Average: {avg_stt:.3f}s")
            print(f"  Std Dev: {std_stt:.3f}s")
            print(f"  Min: {min_stt:.3f}s")
            print(f"  Max: {max_stt:.3f}s")
        
        # AI Response Latency
        if self.results["ai_response_latency"]:
            avg_ai = np.mean(self.results["ai_response_latency"])
            std_ai = np.std(self.results["ai_response_latency"])
            min_ai = np.min(self.results["ai_response_latency"])
            max_ai = np.max(self.results["ai_response_latency"])
            print(f"AI Response Generation Latency:")
            print(f"  Average: {avg_ai:.3f}s")
            print(f"  Std Dev: {std_ai:.3f}s")
            print(f"  Min: {min_ai:.3f}s")
            print(f"  Max: {max_ai:.3f}s")
        
        # TTS Latency
        if self.results["tts_latency"]:
            avg_tts = np.mean(self.results["tts_latency"])
            std_tts = np.std(self.results["tts_latency"])
            min_tts = np.min(self.results["tts_latency"])
            max_tts = np.max(self.results["tts_latency"])
            print(f"Text-to-Speech Latency:")
            print(f"  Average: {avg_tts:.3f}s")
            print(f"  Std Dev: {std_tts:.3f}s")
            print(f"  Min: {min_tts:.3f}s")
            print(f"  Max: {max_tts:.3f}s")
        
        # Total Latency
        if self.results["total_latency"]:
            avg_total = np.mean(self.results["total_latency"])
            std_total = np.std(self.results["total_latency"])
            min_total = np.min(self.results["total_latency"])
            max_total = np.max(self.results["total_latency"])
            print(f"Total End-to-End Latency:")
            print(f"  Average: {avg_total:.3f}s")
            print(f"  Std Dev: {std_total:.3f}s")
            print(f"  Min: {min_total:.3f}s")
            print(f"  Max: {max_total:.3f}s")
        
        print("=============================")


async def record_audio(duration=5):
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


async def main():
    parser = argparse.ArgumentParser(description="Test latency of the voice agent system")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API URL")
    parser.add_argument("--user-id", default="latency-tester", help="User ID")
    parser.add_argument("--iterations", type=int, default=5, help="Number of test iterations")
    parser.add_argument("--audio-file", help="Path to audio file for testing (will record if not provided)")
    parser.add_argument("--record-duration", type=int, default=5, help="Duration to record in seconds")
    
    args = parser.parse_args()
    
    # Record audio if no file provided
    audio_file = args.audio_file
    if not audio_file:
        audio_file = await record_audio(args.record_duration)
        print(f"Audio recorded and saved to {audio_file}")
    
    try:
        # Initialize tester
        tester = LatencyTester(args.api_url, args.user_id)
        
        # Initialize session
        print(f"Initializing session for user {args.user_id}...")
        await tester.initialize_session()
        print(f"Session initialized: {tester.session_id}")
        
        # Run latency tests
        print(f"Running latency test with {args.iterations} iterations...")
        await tester.test_latency(audio_file, args.iterations)
        
        # Print results
        tester.print_results()
        
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        # Clean up
        if tester.session_id:
            print("Terminating session...")
            await tester.terminate_session()
            print("Session terminated")
        
        # Delete temp audio file if we created it
        if not args.audio_file and audio_file and os.path.exists(audio_file):
            os.unlink(audio_file)


if __name__ == "__main__":
    asyncio.run(main())
