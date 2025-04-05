# Real-Time Voice Agent with LiveKit, FastAPI, and Groq

This real-time audio streaming system allows users to interact with an AI-powered voice agent with low latency for natural conversational flow.

## Features

- **Live Audio Streaming**: Uses LiveKit to stream audio input from users and output AI-generated responses in real-time
- **Speech-to-Text (STT)**: Utilizes Faster Whisper for efficient, open-source speech transcription
- **AI-Powered Response Generation**: Uses Groq inference for fast, creative response generation
- **Text-to-Speech (TTS)**: Implements Kokoro-82M for natural-sounding speech synthesis
- **WebSocket-Based Communication**: Enables real-time interaction using FastAPI WebSockets
- **JWT Authentication**: Secures the audio stream using LiveKit's token-based authentication
- **Memory & Context Retention**: Uses Qdrant for storing conversation context

## System Architecture

The system follows this processing pipeline:

1. **Audio Input**: User audio is captured and streamed to the server via LiveKit
2. **Speech Recognition**: Faster Whisper converts speech to text
3. **AI Processing**: Groq API processes the text and generates a response
4. **Speech Synthesis**: Kokoro-82M converts the response to natural-sounding audio
5. **Audio Output**: The synthesized speech is streamed back to the user via LiveKit

## Setup

### Prerequisites

- Python 3.8+
- LiveKit account or self-hosted LiveKit server
- Groq API access
- Qdrant instance (cloud or self-hosted)
- Docker (optional, for containerized deployment)

### Installation

#### Option 1: Direct Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `env.sample` to `.env` and fill in your API keys and configuration settings

#### Option 2: Docker Installation

1. Clone the repository
2. Copy `env.sample` to `.env` and fill in your API keys and configuration settings
3. Build and run with Docker:
   ```
   docker-compose build
   docker-compose up -d
   ```

#### Option 3: Cloud Deployment

This repository is configured for easy deployment to cloud platforms that support Nixpacks:

1. Make sure your repository contains the following files:

   - `Procfile` - Specifies the command to start the application
   - `runtime.txt` - Specifies the Python version
   - `nixpacks.toml` - Provides build instructions

2. Deploy to your cloud platform of choice that supports Nixpacks

3. Set all required environment variables in your cloud platform's dashboard

### Configuration

Key configuration settings in your `.env` file:

```
# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_WS_URL=wss://your-livekit-server.livekit.cloud

# Groq API
GROQ_API_KEY=your_groq_api_key

# STT & TTS Settings
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large-v1, large-v2, large-v3
USE_CUDA=0  # Set to 1 to use GPU acceleration
```

## API Endpoints

### Authentication

- `POST /api/audio/token`: Generate a LiveKit token for accessing a room
  ```json
  {
    "user_id": "user123",
    "room_name": "my-voice-room"
  }
  ```

### Voice Sessions

- `POST /api/audio/initialize`: Initialize a new voice agent session

  ```json
  {
    "user_id": "user123",
    "room_name": "optional-room-name"
  }
  ```

- `DELETE /api/audio/terminate/{session_id}`: Terminate a voice agent session

### WebSocket Communication

- `WebSocket /api/audio/ws/{session_id}`: Real-time communication with the voice agent

## Integration with Next.js Frontend

To integrate with a Next.js frontend:

1. Use LiveKit's client SDK to connect to a room
2. Create audio tracks for microphone input
3. Subscribe to remote audio tracks for agent responses
4. Use the REST API to initialize sessions and manage authentication

## Best Practices

- Use efficient audio encoding (16-bit PCM, 16kHz sample rate) for optimal STT performance
- Implement a push-to-talk mechanism to reduce background noise and processing overhead
- Use WebRTC for best real-time audio quality
- Implement proper error handling for network and service disruptions

## Why Faster Whisper vs OpenAI Whisper?

This implementation uses Faster Whisper instead of OpenAI Whisper because:

1. **Speed**: Faster Whisper offers up to 4x faster inference using CTranslate2
2. **Open Source**: Fully open-source solution with no API costs or rate limits
3. **Local Processing**: Can run entirely on-premise for privacy and reduced latency
4. **Resource Efficiency**: More efficient CPU/GPU utilization

## License

[MIT License](LICENSE)
