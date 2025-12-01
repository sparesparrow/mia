FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for GPIO and MQTT
RUN apt-get update && apt-get install -y \
    libgpiod-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy shared MCP framework from parent directory (when context is modules/hardware-bridge)
COPY ../mcp_framework.py ./mcp_framework.py || true

# Expose port for hardware bridge API
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import paho.mqtt.client as mqtt; print('OK')" || exit 1

# Run the hardware bridge
CMD ["python", "-m", "hardware_bridge.mcp_bridge"]
