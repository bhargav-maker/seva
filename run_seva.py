"""
run_seva.py - Unified Launcher for SEVA AI Kiosk Platform
Starts the FastAPI backend daemon, Playwright browser sandbox, and serves the touch kiosk UI.
"""

import os
import sys
from pathlib import Path

# Ensure Windows terminal supports UTF-8 Devanagari output
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add workspace directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import uvicorn
from backend.config import HOST, PORT

def main():
    print("=" * 65)
    print("🏛️  SEVA AI - Vernacular Digital Assistance Kiosk Platform")
    print("    Maharashtra Citizen Public Services (Setu Kendra / Gram Panchayat)")
    print("=" * 65)
    print(f"[*] Starting FastAPI daemon on http://{HOST}:{PORT}")
    print(f"[*] Kiosk Web UI:          http://localhost:{PORT}/")
    print(f"[*] CDP Video Stream:      http://localhost:{PORT}/api/stream")
    print(f"[*] Interactive API Docs:  http://localhost:{PORT}/docs")
    print("=" * 65)
    print("Press Ctrl+C to stop the kiosk server.\n")

    uvicorn.run(
        "backend.app:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
