"""
vdak-host/run.py — Single command to launch SEVA AI Kiosk
Sets all required Windows env vars before starting services.

Usage:
    python run.py           # Real mode (needs VM running)
    python run.py --demo    # Demo mode — no hardware, no VM needed
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
logger = logging.getLogger("seva.run")

HERE      = Path(__file__).parent
API_PORT  = int(os.getenv("HOST_PORT",   "8000"))
UI_PORT   = int(os.getenv("GRADIO_PORT", "7860"))
UI_URL    = f"http://localhost:{UI_PORT}"


def _base_env(demo: bool) -> dict:
    """Build the environment dict for child processes with all required fixes."""
    env = os.environ.copy()
    # FIX: loopback proxy bypass (prevents Gradio → FastAPI connection issues)
    env["NO_PROXY"]                      = "localhost,127.0.0.1,::1"
    env["no_proxy"]                      = "localhost,127.0.0.1,::1"
    # FIX: Windows symlink privilege (WinError 1314)
    env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    env["HF_HUB_ENABLE_HF_TRANSFER"]       = "0"
    env["TRANSFORMERS_OFFLINE"]             = "0"
    if demo:
        env["DEMO_MODE"] = "true"
    return env


def start_fastapi(demo: bool) -> subprocess.Popen:
    env = _base_env(demo)
    cmd = [sys.executable, "-m", "uvicorn", "main:app",
           "--host", "0.0.0.0", "--port", str(API_PORT), "--log-level", "info"]
    logger.info(f"[FastAPI] Starting on :{API_PORT} {'(DEMO)' if demo else ''}")
    return subprocess.Popen(cmd, cwd=str(HERE), env=env)


def start_gradio() -> subprocess.Popen:
    env = _base_env(False)
    env["GRADIO_PORT"] = str(UI_PORT)
    cmd = [sys.executable, str(HERE / "ui" / "gradio_app.py")]
    logger.info(f"[Gradio] Starting on :{UI_PORT}")
    return subprocess.Popen(cmd, cwd=str(HERE), env=env)


def _open_browser():
    time.sleep(5)
    webbrowser.open(UI_URL)


def main():
    parser = argparse.ArgumentParser(description="SEVA AI Kiosk")
    parser.add_argument("--demo", action="store_true", help="Run without VM or hardware")
    args = parser.parse_args()

    print("\n" + "=" * 62)
    print("  🏛️  SEVA AI — Vernacular Digital Assistance Kiosk")
    print("  Eureka! Juniors 2026 · Zero cost to citizens")
    print("=" * 62)
    if args.demo:
        print("  ⚡ DEMO MODE — No hardware or VM required")
    print(f"  🌐 Kiosk UI  →  {UI_URL}")
    print(f"  ⚙️  Backend  →  http://localhost:{API_PORT}")
    print("  Press Ctrl+C to stop")
    print("=" * 62 + "\n")

    procs = []
    try:
        api = start_fastapi(args.demo)
        procs.append(api)
        time.sleep(2)

        ui = start_gradio()
        procs.append(ui)

        threading.Thread(target=_open_browser, daemon=True).start()

        while all(p.poll() is None for p in procs):
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SEVA AI] Shutting down...")
    finally:
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        print("[SEVA AI] All services stopped.")


if __name__ == "__main__":
    main()
