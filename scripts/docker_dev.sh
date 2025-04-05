#!/bin/bash

# Script to help with Docker development tasks
# Usage: ./scripts/docker_dev.sh [command]

set -e

# Default command
COMMAND=${1:-help}

case "$COMMAND" in
  build)
    echo "Building Docker image..."
    docker-compose build
    ;;
    
  up)
    echo "Starting Docker containers..."
    docker-compose up -d
    echo "Containers started. API available at http://localhost:8000"
    ;;
    
  down)
    echo "Stopping Docker containers..."
    docker-compose down
    ;;
    
  logs)
    echo "Showing logs..."
    docker-compose logs -f
    ;;
    
  restart)
    echo "Restarting Docker containers..."
    docker-compose restart
    ;;
    
  shell)
    echo "Opening shell in the backend container..."
    docker-compose exec creative-ai-backend bash
    ;;
    
  test)
    echo "Running tests in Docker container..."
    docker-compose exec creative-ai-backend pytest
    ;;
    
  clean)
    echo "Cleaning Docker resources..."
    docker-compose down -v
    docker system prune -f
    ;;
    
  prod-build)
    echo "Building production Docker image..."
    docker-compose -f docker-compose.prod.yml build
    ;;
    
  prod-up)
    echo "Starting production Docker containers..."
    docker-compose -f docker-compose.prod.yml up -d
    echo "Production containers started. API available at http://localhost:8000"
    ;;
    
  prod-down)
    echo "Stopping production Docker containers..."
    docker-compose -f docker-compose.prod.yml down
    ;;
    
  help|*)
    echo "Docker Development Helper Script"
    echo ""
    echo "Usage: ./scripts/docker_dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  build       - Build Docker image"
    echo "  up          - Start Docker containers"
    echo "  down        - Stop Docker containers"
    echo "  logs        - Show container logs"
    echo "  restart     - Restart Docker containers"
    echo "  shell       - Open shell in backend container"
    echo "  test        - Run tests in Docker container"
    echo "  clean       - Clean Docker resources"
    echo "  prod-build  - Build production Docker image"
    echo "  prod-up     - Start production Docker containers"
    echo "  prod-down   - Stop production Docker containers"
    echo "  help        - Show this help message"
    ;;
esac
