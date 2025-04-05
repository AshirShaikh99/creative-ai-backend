# Docker Deployment Guide for Creative AI Backend

This guide provides instructions for deploying the Creative AI Backend using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Access to required API keys:
  - Groq API key
  - Qdrant URL and API key
  - LiveKit API key and secret
  - Deepgram API key
  - ElevenLabs API key

## Deployment Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/creative-ai-backend.git
cd creative-ai-backend
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory based on the `env.sample` template:

```bash
cp env.sample .env
```

Edit the `.env` file with your actual configuration values:

```
# Core API Keys
GROQ_API_KEY=your_groq_api_key_here
QDRANT_URL=your_qdrant_url_here
QDRANT_API_KEY=your_qdrant_api_key_here

# Model Settings
FAST_LLM=groq:mixtral-8x7b-32768
SMART_LLM=groq:mixtral-8x7b-32768
STRATEGIC_LLM=groq:mixtral-8x7b-32768
EMBEDDING=text-embedding-3-small

# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key_here
LIVEKIT_API_SECRET=your_livekit_api_secret_here
LIVEKIT_WS_URL=wss://your-livekit-server.livekit.cloud

# Deepgram and ElevenLabs Configuration
DEEPGRAM_API_KEY=your_deepgram_api_key_here
DEEPGRAM_MODEL=nova-2
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=Antoni

# Redis Configuration (if using Redis)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Database Configuration (if using a database)
NEON_DB_URL=postgresql://username:password@host:port/database

# Audio processing settings
AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_SIZE=4096
```

### 3. Build and Start the Docker Containers

```bash
docker-compose up -d
```

This command will:
- Build the Docker image for the Creative AI Backend
- Start the backend service and Redis (if configured)
- Make the API available at http://localhost:8000

### 4. Verify the Deployment

Check if the containers are running:

```bash
docker-compose ps
```

Check the logs:

```bash
docker-compose logs -f
```

Test the API:

```bash
curl http://localhost:8000/
```

You should see a welcome message: `{"message": "Welcome to Creative AI Chatbot"}`

## Managing the Deployment

### Stopping the Services

```bash
docker-compose down
```

### Restarting the Services

```bash
docker-compose restart
```

### Updating the Application

When you need to update the application:

```bash
git pull  # Get the latest code
docker-compose build  # Rebuild the image
docker-compose up -d  # Restart the containers
```

## Cloud Deployment

### AWS Elastic Container Service (ECS)

1. Push your Docker image to Amazon ECR:

```bash
aws ecr get-login-password --region your-region | docker login --username AWS --password-stdin your-account-id.dkr.ecr.your-region.amazonaws.com
docker tag creative-ai-backend:latest your-account-id.dkr.ecr.your-region.amazonaws.com/creative-ai-backend:latest
docker push your-account-id.dkr.ecr.your-region.amazonaws.com/creative-ai-backend:latest
```

2. Create an ECS cluster, task definition, and service using the AWS Console or CLI.

### Google Cloud Run

1. Push your Docker image to Google Container Registry:

```bash
gcloud auth configure-docker
docker tag creative-ai-backend:latest gcr.io/your-project-id/creative-ai-backend:latest
docker push gcr.io/your-project-id/creative-ai-backend:latest
```

2. Deploy to Cloud Run:

```bash
gcloud run deploy creative-ai-backend \
  --image gcr.io/your-project-id/creative-ai-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure Container Instances

1. Push your Docker image to Azure Container Registry:

```bash
az acr login --name YourRegistryName
docker tag creative-ai-backend:latest yourregistryname.azurecr.io/creative-ai-backend:latest
docker push yourregistryname.azurecr.io/creative-ai-backend:latest
```

2. Deploy to Azure Container Instances:

```bash
az container create \
  --resource-group YourResourceGroup \
  --name creative-ai-backend \
  --image yourregistryname.azurecr.io/creative-ai-backend:latest \
  --dns-name-label creative-ai-backend \
  --ports 8000
```

## Troubleshooting

### Container Fails to Start

Check the logs:

```bash
docker-compose logs creative-ai-backend
```

Common issues:
- Missing environment variables
- Invalid API keys
- Network connectivity issues to external services

### API Not Responding

Check if the container is running:

```bash
docker ps
```

Check the health of the container:

```bash
docker inspect --format='{{json .State.Health}}' creative-ai-backend
```

### Redis Connection Issues

If you're using Redis and experiencing connection issues:

```bash
docker-compose exec redis redis-cli ping
```

Should return `PONG` if Redis is working correctly.

## Security Considerations

- Never commit your `.env` file to version control
- Use Docker secrets or environment variables for sensitive information in production
- Consider using a reverse proxy like Nginx for SSL termination
- Implement proper network security rules in your cloud environment
- Regularly update the Docker image with security patches
