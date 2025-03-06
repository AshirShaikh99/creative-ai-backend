# Installation Guide

This guide provides quick installation instructions for the Creative AI Voice Agent.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- LiveKit account (for audio streaming)
- Groq API key (for AI response generation)
- Qdrant instance (for memory storage)

## Quick Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/creative-ai-backend.git
cd creative-ai-backend
```

### 2. Create and activate a virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Linux/macOS
source venv/bin/activate

# Activate on Windows
# venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy the sample environment file and edit it with your credentials:

```bash
cp env.sample .env
```

Edit the `.env` file with your credentials:

```
# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_WS_URL=wss://your-livekit-server.livekit.cloud

# Groq API
GROQ_API_KEY=your_groq_api_key

# Qdrant Configuration
QDRANT_URL=https://your-qdrant-instance.com
QDRANT_API_KEY=your_qdrant_api_key

# Speech-to-Text Settings
WHISPER_MODEL=base
USE_CUDA=0
```

### 5. Start the application

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000.

## Testing the Installation

### Test with the provided script

```bash
# Run the test script in text mode
python scripts/test_voice_agent.py --mode text

# Test with audio recording
python scripts/test_voice_agent.py --mode audio
```

### Test latency performance

```bash
python scripts/latency_test.py
```

## Troubleshooting

### Common Issues

1. **Missing dependencies**:
   ```
   pip install -r requirements.txt --upgrade
   ```

2. **LiveKit connection issues**:
   - Verify your LiveKit API key and secret are correct
   - Ensure your LiveKit server is accessible from your machine

3. **Model loading errors**:
   - Check that you have sufficient disk space for the Whisper model
   - Try using a smaller model by setting `WHISPER_MODEL=tiny` in your `.env` file

4. **Audio device not found**:
   - Ensure your microphone is connected and enabled
   - Try running test scripts with the `--api-url` parameter if your server is not on localhost

## Next Steps

For more detailed information, see the following docs:

- [Full Architecture Overview](docs/architecture.md)
- [Deployment Guide](docs/deployment.md)
- [Next.js Integration](docs/nextjs-integration.md)
