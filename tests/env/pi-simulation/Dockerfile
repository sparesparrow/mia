# Raspberry Pi Gateway Simulation Container
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    # GPIO simulation dependencies
    libgpiod-dev \
    gpiod \
    # I2C and SPI simulation
    i2c-tools \
    # Networking tools
    iproute2 \
    net-tools \
    # Development tools
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 pi && \
    mkdir -p /app && \
    chown -R pi:pi /app

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional Pi-specific packages
RUN pip install --no-cache-dir \
    RPi.GPIO \
    gpiozero \
    adafruit-circuitpython-motor \
    adafruit-circuitpython-servo \
    paho-mqtt \
    flask \
    flask-socketio \
    redis

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x scripts/*.sh

# Create necessary directories
RUN mkdir -p /app/{logs,data,state} && \
    chown -R pi:pi /app

# Switch to app user
USER pi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose ports
EXPOSE 8080 8081 8082

# Default command
CMD ["python", "-m", "src.pi_gateway_simulator"]