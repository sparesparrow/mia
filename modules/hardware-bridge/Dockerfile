FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for GPIO and MQTT
RUN apt-get update && apt-get install -y \
    libgpiod-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY hardware-bridge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared MCP framework (if it exists in modules directory)
COPY mcp_framework.py ./mcp_framework.py

# Copy hardware bridge application code
COPY hardware-bridge/ .

# Expose port for hardware bridge API
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import paho.mqtt.client as mqtt; print('OK')" || exit 1

# Run the hardware bridge
CMD ["python", "-c", "from hardware_bridge import mcp_bridge; print('Hardware bridge module loaded')"]
