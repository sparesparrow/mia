# GPIO Hardware Simulator Container
FROM node:18-alpine

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    build-base \
    linux-headers

# Create app user
RUN addgroup -g 1000 gpio && \
    adduser -D -s /bin/sh -u 1000 -G gpio gpio && \
    mkdir -p /app && \
    chown -R gpio:gpio /app

WORKDIR /app

# Copy package.json first for better caching
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY src/ ./src/
COPY public/ ./public/
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p /app/{state,logs,configs} && \
    chown -R gpio:gpio /app

# Switch to app user
USER gpio

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:9000/health || exit 1

# Expose ports
EXPOSE 9000 9001

# Default command
CMD ["node", "src/gpio-simulator.js"]