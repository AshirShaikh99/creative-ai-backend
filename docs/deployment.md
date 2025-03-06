# Deployment Guide

This guide provides instructions for deploying the Real-Time Voice Agent system to a production environment.

## Prerequisites

- Python 3.8+ installed on the target server
- Docker (optional, for containerized deployment)
- A LiveKit server (self-hosted or cloud)
- Groq API access
- Qdrant instance (cloud or self-hosted)

## Deployment Options

### Option 1: Direct Server Deployment

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/creative-ai-backend.git
cd creative-ai-backend
```

#### 2. Set Up a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

Create a `.env` file in the root directory based on the `env.sample` template:

```bash
cp env.sample .env
```

Edit the `.env` file with your actual configuration values:

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

# STT & TTS Settings
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large-v1, large-v2, large-v3
USE_CUDA=0  # Set to 1 to use GPU acceleration
AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_SIZE=4096

# FastAPI Server
HOST=0.0.0.0
PORT=8000
```

#### 5. Run with Production Server

```bash
# Install Uvicorn with Gunicorn
pip install "uvicorn[standard]" gunicorn

# Start the server
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 app.main:app
```

### Option 2: Docker Deployment

#### 1. Create a Dockerfile

Create a Dockerfile in the root directory:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 8000

# Run the application with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Create a Docker Compose File

Create a `docker-compose.yml` file for easier management:

```yaml
version: '3'

services:
  voice-agent:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./models:/app/models
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

#### 3. Build and Run with Docker Compose

```bash
docker-compose up -d
```

### Option 3: Kubernetes Deployment

#### 1. Create Kubernetes Deployment File

Create a file named `kubernetes/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voice-agent
  labels:
    app: voice-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: voice-agent
  template:
    metadata:
      labels:
        app: voice-agent
    spec:
      containers:
      - name: voice-agent
        image: yourdockerregistry/voice-agent:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2"
        env:
        - name: LIVEKIT_API_KEY
          valueFrom:
            secretKeyRef:
              name: voice-agent-secrets
              key: livekit-api-key
        - name: LIVEKIT_API_SECRET
          valueFrom:
            secretKeyRef:
              name: voice-agent-secrets
              key: livekit-api-secret
        - name: LIVEKIT_WS_URL
          value: "wss://your-livekit-server.livekit.cloud"
        - name: GROQ_API_KEY
          valueFrom:
            secretKeyRef:
              name: voice-agent-secrets
              key: groq-api-key
        - name: QDRANT_URL
          value: "https://your-qdrant-instance.com"
        - name: QDRANT_API_KEY
          valueFrom:
            secretKeyRef:
              name: voice-agent-secrets
              key: qdrant-api-key
        - name: WHISPER_MODEL
          value: "base"
        - name: USE_CUDA
          value: "0"
```

#### 2. Create Kubernetes Service File

Create a file named `kubernetes/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: voice-agent-service
spec:
  selector:
    app: voice-agent
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### 3. Create Kubernetes Secrets

```bash
kubectl create secret generic voice-agent-secrets \
  --from-literal=livekit-api-key=your_livekit_api_key \
  --from-literal=livekit-api-secret=your_livekit_api_secret \
  --from-literal=groq-api-key=your_groq_api_key \
  --from-literal=qdrant-api-key=your_qdrant_api_key
```

#### 4. Deploy to Kubernetes

```bash
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
```

## Production Considerations

### 1. SSL/TLS Configuration

For security, enable HTTPS using a reverse proxy such as Nginx or use a cloud provider's load balancer with SSL termination.

Example Nginx configuration:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/ssl/certificate.crt;
    ssl_certificate_key /path/to/ssl/private.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/audio/ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Model Caching

For better performance, cache models in a persistent volume:

```bash
# Create a directory for models
mkdir -p models
```

Update your `.env` file to use the models directory:

```
WHISPER_MODEL_DIR=/path/to/models
```

### 3. Monitoring and Logging

Implement proper monitoring and logging for production:

1. **Logging Configuration**

Create a `logging_config.py` file:

```python
import logging
import os
from logging.handlers import RotatingFileHandler

def configure_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "voice_agent.log"),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers to root logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
```

2. **Prometheus Metrics**

Install Prometheus support:

```bash
pip install prometheus-client
```

Add metrics to your FastAPI app:

```python
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import FastAPI, Response

app = FastAPI()

# Define metrics
http_requests_total = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])
stt_processing_time = Histogram('stt_processing_time_seconds', 'STT processing time in seconds')
tts_processing_time = Histogram('tts_processing_time_seconds', 'TTS processing time in seconds')
active_sessions = Counter('active_sessions', 'Number of active voice sessions')

@app.get('/metrics')
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 4. Load Testing

Before full production deployment, perform load testing to ensure your system can handle the expected load:

```bash
# Install locust for load testing
pip install locust

# Create a locustfile.py for testing WebSocket connections
```

```python
# locustfile.py
import time
import json
import websocket
from locust import User, task, between

class WebSocketClient:
    def __init__(self, host):
        self.host = host
        self.ws = None
    
    def connect(self, session_id):
        ws_url = f"{self.host.replace('http://', 'ws://')}/api/audio/ws/{session_id}"
        self.ws = websocket.create_connection(ws_url)
    
    def send(self, message):
        self.ws.send(message)
    
    def receive(self):
        return self.ws.recv()
    
    def disconnect(self):
        if self.ws:
            self.ws.close()

class VoiceAgentUser(User):
    wait_time = between(1, 5)
    
    def on_start(self):
        # Initialize session through REST API
        response = self.client.post(
            "/api/audio/initialize",
            json={"user_id": f"loadtest-{self.user_id}"}
        )
        self.session_info = response.json()
        self.session_id = self.session_info["session_id"]
        self.ws_client = WebSocketClient(self.host)
        self.ws_client.connect(self.session_id)
    
    def on_stop(self):
        self.ws_client.disconnect()
        self.client.delete(f"/api/audio/terminate/{self.session_id}")
    
    @task
    def send_audio(self):
        # Load audio sample
        with open("sample_audio.wav", "rb") as f:
            audio_data = f.read()
        
        # Send audio data
        self.ws_client.send(audio_data)
        
        # Wait for response
        response = self.ws_client.receive()
        data = json.loads(response)
        
        if data.get("type") == "transcription":
            # Wait for AI response
            response = self.ws_client.receive()
```

Run the load test:

```bash
locust -f locustfile.py
```

### 5. CI/CD Pipeline

Set up a CI/CD pipeline for automated testing and deployment.

Example GitHub Actions workflow (`.github/workflows/main.yml`):

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-asyncio
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    - name: Test with pytest
      run: |
        pytest
  
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v2
    - name: Build and push Docker image
      uses: docker/build-push-action@v2
      with:
        context: .
        push: true
        tags: yourdockerregistry/voice-agent:latest
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to production
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.SSH_HOST }}
        username: ${{ secrets.SSH_USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /path/to/deployment
          docker-compose pull
          docker-compose up -d
```
