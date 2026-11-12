"""Serve the existing API and static UI on a single origin.
Run: python -m uvicorn serve_frontend:app --port 8001 --no-access-log
"""
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from main import app

# Register this after API routes. Keep SameSite=Strict refresh cookies intact.
app.mount('/', StaticFiles(directory=Path(__file__).resolve().parent / 'frontend', html=True), name='frontend')
