# Cloud Deployment Guide

This guide provides instructions for deploying the Creative AI Backend to cloud platforms using Nixpacks.

## What is Nixpacks?

Nixpacks is a build system that automatically detects the language and framework of your application and builds a container image for it. It's used by several cloud platforms for easy deployment of applications.

## Prerequisites

- A GitHub repository with your Creative AI Backend code
- An account on a cloud platform that supports Nixpacks (like Render, Railway, etc.)
- All required API keys and credentials for your application

## Deployment Files

The following files are included in the repository to support cloud deployment:

### 1. Procfile

The `Procfile` tells the cloud platform how to run your application:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

This command starts the FastAPI application using Uvicorn, binding to all network interfaces and using the port specified by the cloud platform.

### 2. runtime.txt

The `runtime.txt` file specifies the Python version to use:

```
python-3.9.18
```

This ensures that the cloud platform uses Python 3.9 to run your application.

### 3. nixpacks.toml

The `nixpacks.toml` file provides explicit build instructions:

```toml
[phases.setup]
aptPkgs = ["python3", "python3-pip", "python3-venv", "ffmpeg", "libsndfile1"]

[phases.install]
cmds = [
  "python -m venv --copies /opt/venv",
  ". /opt/venv/bin/activate && pip install --upgrade pip",
  ". /opt/venv/bin/activate && pip install -r requirements.txt"
]

[start]
cmd = "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
```

This configuration:
- Installs necessary system packages (Python, ffmpeg, libsndfile1)
- Creates a virtual environment and installs dependencies
- Specifies how to start the application

## Deployment Steps

### 1. Prepare Your Repository

Make sure your repository includes:
- All application code
- `requirements.txt` with all dependencies
- `Procfile`, `runtime.txt`, and `nixpacks.toml` as described above

### 2. Connect to Your Cloud Platform

1. Log in to your cloud platform
2. Create a new web service
3. Connect to your GitHub repository
4. Select the branch to deploy (usually `main`)

### 3. Configure Environment Variables

Set all required environment variables in your cloud platform's dashboard:

- `GROQ_API_KEY`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `LIVEKIT_WS_URL`
- `DEEPGRAM_API_KEY`
- `ELEVENLABS_API_KEY`
- Any other variables specified in your `.env.sample` file

### 4. Deploy Your Application

1. Trigger a deployment in your cloud platform's dashboard
2. Wait for the build and deployment to complete
3. Access your application at the provided URL

## Troubleshooting

### Build Failures

If your build fails, check the build logs for errors:

1. **Missing dependencies**: Make sure all required packages are in `requirements.txt`
2. **System dependencies**: Ensure `nixpacks.toml` includes all necessary system packages
3. **Python version**: Verify that the Python version in `runtime.txt` is supported by your cloud platform

### Runtime Errors

If your application fails to start:

1. **Environment variables**: Check that all required environment variables are set
2. **Port configuration**: Ensure your application is listening on the port specified by the `PORT` environment variable
3. **Logs**: Review the application logs for specific error messages

### Performance Issues

If your application is running but experiencing performance issues:

1. **Resource allocation**: Check if your application has enough CPU and memory resources
2. **Database connections**: Ensure your database connections are properly configured
3. **Scaling**: Consider scaling your application horizontally if it's receiving high traffic

## Platform-Specific Instructions

### Render

1. Create a new Web Service
2. Connect your GitHub repository
3. Select "Python" as the runtime
4. Set the build command to `./build.sh` (if you have a custom build script) or leave empty to use Nixpacks
5. Set the start command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add all environment variables
7. Click "Create Web Service"

### Railway

1. Create a new project
2. Connect your GitHub repository
3. Railway will automatically detect the Nixpacks configuration
4. Add environment variables in the Variables section
5. Deploy your application

### Heroku

1. Create a new app
2. Connect your GitHub repository
3. Add the Python buildpack
4. Add all environment variables in the Settings tab
5. Deploy your application

## Monitoring and Maintenance

After deployment, regularly monitor your application:

1. **Logs**: Check application logs for errors or warnings
2. **Performance**: Monitor CPU, memory, and network usage
3. **Updates**: Keep dependencies updated by redeploying when necessary
4. **Scaling**: Adjust resources based on usage patterns

## Security Considerations

1. **Environment variables**: Never commit sensitive information to your repository
2. **API keys**: Regularly rotate API keys and update them in your cloud platform
3. **HTTPS**: Ensure your application is served over HTTPS
4. **Access control**: Implement proper authentication and authorization
