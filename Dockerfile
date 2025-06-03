# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# system deps for Chromium + pillow, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
      python3-dev \
      build-essential \
      chromium-driver chromium \
      libglib2.0-0 libnss3 libgdk-pixbuf2.0-0 libgtk-3-0 \
      && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements.txt \
                               -r requirements-dev.txt

# Copy your code
COPY . .

# Expose Flask port
EXPOSE 5000

ENV PYTHONUNBUFFERED=1

# Default: do nothing until overridden
ENTRYPOINT []
