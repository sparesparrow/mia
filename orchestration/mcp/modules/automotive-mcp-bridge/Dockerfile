# Multi-stage build for automotive MCP bridge
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies for automotive systems
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    alsa-utils \
    pulseaudio-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r aiuser && useradd -r -g aiuser aiuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY main.py .
COPY requirements.txt .

# Create directories for automotive data
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R aiuser:aiuser /app

# Automotive-specific environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    AUTOMOTIVE_MODE=true \
    EDGE_OPTIMIZATION=true \
    VOICE_TIMEOUT_MS=500 \
    LOG_LEVEL=INFO

# Health check for automotive reliability
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8084/health || exit 1

# Expose ports
EXPOSE 8084

# Switch to non-root user
USER aiuser

# Start the automotive MCP bridge
CMD ["python", "main.py"]