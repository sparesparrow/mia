FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by the security scanner (docker, psutil, etc.)
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
    iproute2 \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy automotive security scanner code
COPY ../security-scanner/automotive_security.py ./automotive_security.py

# Install minimal Python dependencies for automotive_security.py
# (Keep this light to avoid heavy image, extend as needed)
RUN pip install --no-cache-dir aiohttp docker psutil

# Default command just prints help; extend to real service later
CMD ["python", "automotive_security.py", "--help"]

