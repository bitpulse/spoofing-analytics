#!/usr/bin/env python3
"""
Run the Spoofing Analytics API Server
"""

import uvicorn
from src.api.spoofing_api import app
from loguru import logger
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Start the API server"""
    logger.info("Starting Spoofing Analytics API Server...")
    
    # Configure server
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    
    logger.info(f"Server will run on {host}:{port}")
    logger.info(f"Auto-reload: {reload}")
    logger.info("API documentation available at http://localhost:8000/docs")
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=reload,
        access_log=True
    )


if __name__ == "__main__":
    main()