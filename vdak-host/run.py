"""
vdak-host/run.py
Single entry point — starts FastAPI backend + Gradio UI together.

Usage:
    python run.py           # Full mode (connects to VM)
    python run.py --demo    # Demo mode (no hardware, no VM needed)
"""

import argparse
import logging
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vdak.run")

HERE       = Path(__file__).parent
HOST_PORT  = int(os.getenv("HOST_PORT",  "8000"))
UI_PORT    = int(os.getenv("GRADIO_PORT","7860"))
UI_URL     = f"http://localhost:{UI_PORT}"


def start_fastapi(demo: bool):
    env = os.environ.copy()
    if demo:
        env["DEMO_MODE"] = "true"
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", str(HOST_PORT),
        "--log-level", "info",
    ]
    logger.info(f"[FastAPI] Starting on port {HOST_PORT} {'(DEMO MODE)' if demo else ''}")
    proc = subprocess.Popen(cmd, cwd=str(HERE), env=env)
    return proc


def start_gradio():
    env = os.environ.copy()
    env["GRADIO_PORT"] = str(UI_PORT)
    cmd = [sys.executable, "-m", "ui.gradio_app"]
    logger.info(f"[Gradio] Starting on port {UI_PORT}")
    proc = subprocess.Popen(cmd, cwd=str(HERE), env=env)
    return proc


def open_browser():
    time.sleep(4)
    logger.info(f"[Browser] Opening {UI_URL}")
    webbrowser.open(UI_URL)


def main():
    parser = argparse.ArgumentParser(description="V-DAK Kiosk Runner")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode (no VM/hardware)")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  🏛️  V-DAK — Vernacular Digital Assistance Kiosk")
    print("  Eureka Juniors 2026")
    print("="*60)
    if args.demo:
        print("  ⚡ DEMO MODE — No hardware or VM required")
    print(f"  🌐 UI:      {UI_URL}")
    print(f"  ⚙️  Backend: http://localhost:{HOST_PORT}")
    print("  Press Ctrl+C to stop all services")
    print("="*60 + "\n")

    procs = []
    try:
        api_proc = start_fastapi(args.demo)
        procs.append(api_proc)
        time.sleep(2)   # Wait for FastAPI to be ready

        ui_proc = start_gradio()
        procs.append(ui_proc)

        # Open browser automatically
        threading.Thread(target=open_browser, daemon=True).start()

        # Wait for either process to exit
        while all(p.poll() is None for p in procs):
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[V-DAK] Shutting down...")
    finally:
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                p.kill()
        print("[V-DAK] All services stopped. Goodbye!")


if __name__ == "__main__":
    main()
