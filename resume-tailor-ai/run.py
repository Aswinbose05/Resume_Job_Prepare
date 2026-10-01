"""
Entry point to launch the AI Career Intelligence Platform.
Runs FastAPI with Uvicorn on http://localhost:8000
"""
import uvicorn
import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(base_dir, "resume-tailor-ai")):
    sys.path.insert(0, os.path.join(base_dir, "resume-tailor-ai"))
else:
    sys.path.insert(0, base_dir)

# Ensure data directory expected by CrewAI / Chroma exists
try:
    os.makedirs(os.path.expanduser("~/.local/share/app"), exist_ok=True)
except Exception:
    pass

from core.config import settings
from core.logger import logger

def main():
    print("=======================================================")
    print(f"Launching {settings.APP_NAME} v{settings.APP_VERSION}")
    port = int(os.environ.get("PORT", settings.PORT))
    print(f"Modern Dashboard: http://localhost:{port}")
    print("Multi-Agent Engine: CrewAI + Deterministic ATS")
    print("=======================================================\n")
    
    uvicorn.run(
        "api.routes:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )

if __name__ == "__main__":
    main()
