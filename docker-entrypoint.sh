#!/bin/bash
set -e

# Function to wait for a service
wait_for_service() {
  local host="$1"
  local port="$2"
  local service="$3"
  local timeout="${4:-30}"

  echo "Waiting for $service at $host:$port..."
  for i in $(seq 1 $timeout); do
    if nc -z "$host" "$port"; then
      echo "$service is available after $i seconds"
      return 0
    fi
    sleep 1
  done
  echo "Timeout: $service at $host:$port is not available after $timeout seconds"
  return 1
}

# Wait for Redis if configured
if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
  wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" 60
fi

# Run database migrations if needed
# Uncomment if you have database migrations to run
# python -m alembic upgrade head

# Create necessary directories
mkdir -p /app/logs
mkdir -p /app/models
mkdir -p /app/docs

# Check if we need to process documents
if [ -d "/app/docs" ] && [ "$(ls -A /app/docs)" ]; then
  echo "Processing documents in /app/docs..."
  python -m scripts.process_docs
fi

# Execute the main command
exec "$@"
