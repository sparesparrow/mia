#!/usr/bin/env python3
"""
FastAPI Server Main Entry Point
Run with: python -m rpi.api
"""

import uvicorn
from .server import app

if __name__ == "__main__":
    uvicorn.run(
        "rpi.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )