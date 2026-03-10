"""Entry point: python run.py"""
import sys
import os

# Add backend parent to path so 'app' package is importable
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
