#!/usr/bin/env python3
"""
FastAPI Server Main Entry Point
Run from apps/rpi-backend/py-api with: python -m api
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
