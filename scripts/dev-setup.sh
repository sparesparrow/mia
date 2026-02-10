#!/bin/bash
# AI-SERVIS Development Setup Script

set -e

echo "Setting up AI-SERVIS Universal development environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from template. Please update API keys and secrets."
fi

# Install Python dependencies (if running locally)
if command -v python3 &> /dev/null; then
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
    pip3 install -r requirements-dev.txt
fi

# Setup pre-commit hooks
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo "Pre-commit hooks installed."
fi

# Create necessary directories
mkdir -p logs volumes

echo "Development environment setup complete!"
echo "Run 'docker-compose -f docker-compose.dev.yml up' to start the development environment."
