"""Run the built frontend and API together: python src/main.py."""
import os
from pathlib import Path
import sys

# Direct script execution puts src/, rather than the repository root, on sys.path.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import FRONTEND_DIST


def main():
    if not (FRONTEND_DIST / "index.html").is_file():
        raise SystemExit("Frontend build missing. Run: npm --prefix src/frontend install && npm --prefix src/frontend run build")
    import uvicorn
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()
