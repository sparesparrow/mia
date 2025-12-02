FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including PostgreSQL headers for psycopg2-binary)
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY core-orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared MCP framework
COPY mcp_framework.py ./mcp_framework.py

# Copy application code
COPY core-orchestrator/ .

# Expose port
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "main.py"]
