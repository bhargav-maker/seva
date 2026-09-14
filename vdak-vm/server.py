"""
vdak-vm/server.py — Production rewrite with live screen streaming
Sends Base64 JPEG browser frames to host UI at 4 FPS.
"""

import asyncio
import base64
import json
import logging
import os

import websockets
from dotenv import load_dotenv

from agent import VDAKAgent, build_llm

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vdak.vm.server")

API_KEY  = os.getenv("OPENROUTER_API_KEY")
MODEL    = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct:free")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
PORT     = int(os.getenv("HOST_WS_PORT", "8765"))

_resume_event: asyncio.Event = asyncio.Event()
_active_page  = None   # Shared reference to current Playwright page
_streaming    = False  # Whether to send viewport frames


# ─────────────────────────────────────────────────────────────────────────────
#  Live Browser Viewport Streaming
# ─────────────────────────────────────────────────────────────────────────────

async def stream_viewport(websocket):
    """
    Captures Playwright browser screenshots at 4 FPS and sends Base64 JPEG
    frames to the host UI via WebSocket as BROWSER_FRAME events.
    """
    global _active_page, _streaming
    _streaming = True
    logger.info("[STREAM] Viewport streaming started.")
    while _streaming:
        try:
            if _active_page and not _active_page.is_closed():
                shot = await _active_page.screenshot(type="jpeg", quality=55)
                b64  = base64.b64encode(shot).decode("utf-8")
                await websocket.send(json.dumps({
                    "event": "BROWSER_FRAME",
                    "data":  b64,
                }))
        except Exception as e:
            logger.debug(f"[STREAM] Frame skip: {e}")
        await asyncio.sleep(0.25)   # 4 FPS
    logger.info("[STREAM] Viewport streaming stopped.")


# ─────────────────────────────────────────────────────────────────────────────
#  Connection Handler
# ─────────────────────────────────────────────────────────────────────────────

async def handle_connection(websocket):
    global _resume_event, _active_page, _streaming
    logger.info(f"[VM] Host connected: {websocket.remote_address}")
    await websocket.send(json.dumps({"event": "READY"}))

    stream_task = None

    async for raw in websocket:
        msg  = json.loads(raw)
        etype = msg.get("type")

        # ── RUN_TASK ──────────────────────────────────────────────────────── #
        if etype == "RUN_TASK":
            task = msg["task"]
            logger.info(f"[VM] Task: {task[:80]}...")
            _resume_event = asyncio.Event()

            llm = build_llm(API_KEY, MODEL, BASE_URL)

            async def notify_checkpoint():
                _streaming = False   # Pause stream during OTP
                await websocket.send(json.dumps({"event": "HUMAN_CHECKPOINT"}))
                logger.info("[VM] HUMAN_CHECKPOINT sent.")

            async def wait_for_resume():
                logger.info("[VM] Waiting for citizen OTP...")
                await _resume_event.wait()
                _resume_event.clear()
                _streaming = True   # Resume stream after OTP
                logger.info("[VM] Agent resumed.")

            def on_page_ready(page):
                """Callback from VDAKAgent when Playwright page is available."""
                global _active_page
                _active_page = page
                logger.info("[VM] Page reference acquired — streaming available.")

            agent = VDAKAgent(
                task=task,
                llm=llm,
                notify_checkpoint_cb=notify_checkpoint,
                wait_for_resume_cb=wait_for_resume,
                on_page_ready_cb=on_page_ready,
            )

            await websocket.send(json.dumps({"event": "AGENT_STARTED"}))

            # Start viewport streaming in background
            _streaming = True
            stream_task = asyncio.create_task(stream_viewport(websocket))

            try:
                history = await agent.run()
                result  = str(history.final_result()) if history else "Completed"
                await websocket.send(json.dumps({"event": "DONE", "result": result}))
                logger.info(f"[VM] Task done: {result}")
            except Exception as e:
                logger.error(f"[VM] Agent error: {e}")
                await websocket.send(json.dumps({"event": "ERROR", "detail": str(e)}))
            finally:
                _streaming = False
                if stream_task:
                    stream_task.cancel()
                _active_page = None

        # ── RESUME_OTP ────────────────────────────────────────────────────── #
        elif etype == "RESUME_OTP":
            logger.info("[VM] RESUME_OTP received.")
            _resume_event.set()

        else:
            logger.warning(f"[VM] Unknown message: {etype}")


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    logger.info(f"[VM] SEVA AI Browser Agent — WebSocket server on port {PORT}")
    async with websockets.serve(handle_connection, "0.0.0.0", PORT):
        logger.info(f"[VM] Listening on ws://0.0.0.0:{PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
