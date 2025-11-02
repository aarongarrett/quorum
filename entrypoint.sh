#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI app using Uvicorn
echo "Starting web server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
