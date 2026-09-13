"""
vdak-vm/server.py
WebSocket server on the VM side.
Receives tasks from the host orchestrator and runs the VDAKAgent.
Sends events back: READY | CHECKPOINT | STEP_UPDATE | DONE | ERROR
"""

import asyncio
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

# --------------------------------------------------------------------------- #
#  Config
# --------------------------------------------------------------------------- #
API_KEY   = os.getenv("OPENROUTER_API_KEY")
MODEL     = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct:free")
BASE_URL  = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
PORT      = int(os.getenv("HOST_WS_PORT", "8765"))

# --------------------------------------------------------------------------- #
#  Per-connection state
# --------------------------------------------------------------------------- #
_resume_event: asyncio.Event = asyncio.Event()


async def handle_connection(websocket):
    """Handle one host connection. Runs one browser session per RUN_TASK message."""
    global _resume_event

    logger.info(f"Host connected: {websocket.remote_address}")
    await websocket.send(json.dumps({"event": "READY"}))

    async for raw in websocket:
        message = json.loads(raw)
        event_type = message.get("type")

        # ------------------------------------------------------------------ #
        #  RUN_TASK — host sends extracted form data + target scheme
        # ------------------------------------------------------------------ #
        if event_type == "RUN_TASK":
            task_description = message["task"]
            logger.info(f"[VM] Task received: {task_description}")

            _resume_event = asyncio.Event()   # Fresh event for this session
            llm = build_llm(API_KEY, MODEL, BASE_URL)

            async def notify_checkpoint():
                """Tell host: agent is paused, citizen must type OTP."""
                await websocket.send(json.dumps({"event": "HUMAN_CHECKPOINT"}))
                logger.info("[VM] HUMAN_CHECKPOINT sent to host.")

            async def wait_for_resume():
                """Block agent until host sends RESUME_OTP."""
                logger.info("[VM] Waiting for citizen OTP...")
                await _resume_event.wait()
                _resume_event.clear()
                logger.info("[VM] Resumed.")

            agent = VDAKAgent(
                task=task_description,
                llm=llm,
                notify_checkpoint_cb=notify_checkpoint,
                wait_for_resume_cb=wait_for_resume,
            )

            try:
                await websocket.send(json.dumps({"event": "AGENT_STARTED"}))
                history = await agent.run()
                final_url = history.final_result() if history else "Unknown"
                await websocket.send(json.dumps({
                    "event": "DONE",
                    "result": str(final_url),
                }))
                logger.info("[VM] Task completed.")
            except Exception as e:
                logger.error(f"[VM] Agent error: {e}")
                await websocket.send(json.dumps({
                    "event": "ERROR",
                    "detail": str(e),
                }))

        # ------------------------------------------------------------------ #
        #  RESUME_OTP — citizen has typed their OTP, agent can continue
        # ------------------------------------------------------------------ #
        elif event_type == "RESUME_OTP":
            logger.info("[VM] RESUME_OTP received — unblocking agent.")
            _resume_event.set()

        else:
            logger.warning(f"[VM] Unknown message type: {event_type}")


# --------------------------------------------------------------------------- #
#  Entry Point
# --------------------------------------------------------------------------- #
async def main():
    logger.info(f"V-DAK VM WebSocket server starting on port {PORT}...")
    async with websockets.serve(handle_connection, "0.0.0.0", PORT):
        logger.info(f"[VM] Listening on ws://0.0.0.0:{PORT}")
        await asyncio.Future()   # Run forever


if __name__ == "__main__":
    asyncio.run(main())
