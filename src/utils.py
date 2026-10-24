"""Paths shared by the application entry point and API host."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = PROJECT_ROOT / "src" / "frontend" / "dist"
