# Multi-stage build: Build React frontend, then FastAPI backend

# Stage 1: Build React frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app

# Copy package files from frontend directory
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# Copy all frontend source
COPY frontend/ ./
# Set VITE_API_URL to empty string for same-origin deployment
ENV VITE_API_URL=""
RUN npm run build

# Debug: List what was built
RUN ls -la /app/
RUN ls -la /app/dist/ || echo "No dist directory found!"

# Stage 2: FastAPI backend
FROM python:3.11-slim

WORKDIR /app

# Set PYTHONPATH so Python can find modules in /app
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create frontend directory and copy React build from frontend stage
RUN mkdir -p ./frontend
COPY --from=frontend-build /app/dist/ ./frontend/build/

# Debug: Verify the copy worked
RUN ls -la ./frontend/build/
RUN ls -la ./frontend/build/assets/ || echo "No assets directory!"

# Expose port
EXPOSE 8000

# Run entrypoint script (runs migrations, then starts uvicorn)
CMD ["./entrypoint.sh"]