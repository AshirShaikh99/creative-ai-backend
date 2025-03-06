# Real-Time Voice Agent - System Architecture

## Overview

The real-time voice agent is built on a robust architecture designed for low-latency audio streaming and processing. The system uses FastAPI for the backend, LiveKit for real-time audio transmission, Faster Whisper for speech-to-text, Groq for AI response generation, and Kokoro-82M for text-to-speech.

## Architecture Diagram

```
┌─────────────┐        ┌─────────────────────────────────────────────┐
│             │        │                                             │
│  Next.js    │◄──────►│  LiveKit Server                             │
│  Frontend   │        │  (Real-time Audio Transmission)             │
│             │        │                                             │
└─────┬───────┘        └───────────────────┬─────────────────────────┘
      │                                    │
      │                                    │
      │                                    ▼
      │                 ┌─────────────────────────────────────────────┐
      │                 │                                             │
      │                 │  FastAPI Backend                            │
      └────────────────►│  (Audio Processing Pipeline)                │
                        │                                             │
                        └───┬─────────────┬────────────────┬──────────┘
                            │             │                │
                            ▼             ▼                ▼
                ┌───────────────┐ ┌───────────────┐ ┌────────────────┐
                │               │ │               │ │                │
                │ Faster Whisper│ │   Groq API    │ │   Kokoro-82M   │
                │    (STT)      │ │  (AI Engine)  │ │     (TTS)      │
                │               │ │               │ │                │
                └───────────────┘ └───────┬───────┘ └────────────────┘
                                          │
                                          ▼
                                  ┌───────────────┐
                                  │               │
                                  │    Qdrant     │
                                  │  (Memory DB)  │
                                  │               │
                                  └───────────────┘
```

## Components

### 1. FastAPI Backend

The core of the system is a FastAPI application that coordinates all the components:

- **WebSocket Handlers**: Manage real-time communication with clients
- **Audio Processing Pipeline**: Coordinates the flow of audio data through the system
- **Session Management**: Maintains state for active voice agent sessions
- **Authentication**: Handles JWT token generation for LiveKit

### 2. LiveKit Integration

LiveKit provides the real-time audio streaming infrastructure:

- **Room Management**: Creates and manages audio rooms for each session
- **Track Publishing/Subscribing**: Handles audio track transmission
- **Token Authentication**: Secures access to audio rooms
- **WebRTC Capabilities**: Provides low-latency audio transmission

### 3. Speech-to-Text (Faster Whisper)

Converts user speech to text for processing:

- **Audio Chunking**: Processes audio in manageable chunks
- **Voice Activity Detection**: Filters out silence for better transcription
- **Language Detection**: Automatically detects and processes the spoken language
- **Confidence Scoring**: Provides confidence levels for transcriptions

### 4. AI Response Generation (Groq)

Processes text input and generates intelligent responses:

- **Context Awareness**: Maintains conversation context for natural responses
- **Creative Response Generation**: Creates engaging and contextually relevant replies
- **Stream Processing**: Supports streaming responses for faster user feedback
- **Memory Integration**: Works with Qdrant to store and retrieve conversation history

### 5. Text-to-Speech (Kokoro-82M)

Converts AI-generated text responses to natural-sounding speech:

- **Voice Synthesis**: Generates high-quality speech audio
- **Audio Streaming**: Supports streaming synthesis for faster playback
- **Voice Customization**: Allows for different voice characteristics

### 6. Memory System (Qdrant)

Provides persistent storage for conversation context:

- **Vector Storage**: Efficiently stores and retrieves conversation embeddings
- **Session Management**: Organizes memory by session for context continuity
- **Metadata Filtering**: Allows querying based on session IDs and timestamps

## Data Flow

1. **User Input**:
   - User speaks into their microphone
   - Audio is captured and streamed to the LiveKit server
   - The server routes the audio to the FastAPI backend

2. **Speech Processing**:
   - FastAPI receives audio chunks from LiveKit
   - Audio is accumulated until sufficient for processing
   - Faster Whisper converts speech to text
   - The transcription is sent to the Groq AI engine

3. **AI Processing**:
   - Groq processes the transcription with conversation context
   - The system generates a contextually relevant response
   - The response is sent to Kokoro-82M for speech synthesis
   - Context is stored in Qdrant for future reference

4. **Response Delivery**:
   - Synthesized speech is streamed back through LiveKit
   - The user hears the AI response with minimal latency
   - Text representations of both input and output are sent to the frontend

## Performance Considerations

- **Audio Chunk Size**: Balances latency vs. accuracy (currently 4096 samples)
- **Whisper Model Size**: Smaller models are faster but less accurate
- **GPU Acceleration**: Optional GPU support for faster processing
- **Streaming Responses**: Incremental responses reduce perceived latency
- **WebRTC Optimization**: Uses LiveKit's optimized WebRTC for low-latency audio

## Security Implementation

- **JWT Authentication**: Secures LiveKit room access
- **API Key Management**: All external service credentials stored in environment variables
- **Input Validation**: Validates all user inputs through Pydantic models
- **CORS Configuration**: Controls which origins can access the API

## Scaling Considerations

- **Stateless Design**: Core components are designed to be stateless for horizontal scaling
- **LiveKit Clustering**: LiveKit supports clustering for high-availability deployments
- **Worker Processes**: Multiple worker processes can handle concurrent sessions
- **Load Balancing**: FastAPI supports standard load balancing techniques
- **Queue Management**: Long-running tasks can be offloaded to background workers

## Future Enhancements

- **Multi-user Conversations**: Supporting multiple users in a single conversation
- **Emotion Detection**: Analyzing voice for emotional content
- **Custom Voice Cloning**: Creating personalized voices for the AI
- **Multilingual Support**: Expanding language capabilities beyond English
- **Noise Reduction**: Adding advanced noise cancellation for clearer audio
