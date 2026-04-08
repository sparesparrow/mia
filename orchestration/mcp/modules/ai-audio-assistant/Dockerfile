FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio and PyAudio build
RUN apt-get update && apt-get install -y \
    curl \
    alsa-utils \
    pulseaudio \
    pipewire \
    build-essential \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ai-audio-assistant/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared MCP framework and application code
COPY shared/ ./shared/
COPY ai-audio-assistant/ .

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8082), 2).close()" || exit 1

# Run the application
CMD ["python", "main.py"]
