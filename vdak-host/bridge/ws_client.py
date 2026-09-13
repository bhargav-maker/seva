"""
vdak-host/bridge/ws_client.py
WebSocket client on the host side.
Sends tasks to the VM browser agent and handles events back.
"""

import asyncio
import json
import logging
from typing import Callable, Optional

import websockets

logger = logging.getLogger("vdak.bridge")


class VMBridge:
    """
    Persistent WebSocket connection to the VM browser agent.
    Handles: RUN_TASK → receives CHECKPOINT / DONE / ERROR events.
    """

    def __init__(self, vm_ws_url: str):
        self.vm_ws_url = vm_ws_url
        self._ws = None
        self._on_checkpoint: Optional[Callable] = None
        self._on_done: Optional[Callable]       = None
        self._on_error: Optional[Callable]      = None

    def set_handlers(
        self,
        on_checkpoint: Callable,
        on_done: Callable,
        on_error: Callable,
    ):
        self._on_checkpoint = on_checkpoint
        self._on_done       = on_done
        self._on_error      = on_error

    async def connect(self):
        """Connect to VM WebSocket server."""
        logger.info(f"[BRIDGE] Connecting to VM at {self.vm_ws_url}...")
        self._ws = await websockets.connect(self.vm_ws_url)
        logger.info("[BRIDGE] Connected to VM.")

    async def send_task(self, task_description: str):
        """Send a RUN_TASK command to the VM browser agent."""
        if not self._ws:
            raise RuntimeError("Not connected to VM. Call connect() first.")
        payload = json.dumps({"type": "RUN_TASK", "task": task_description})
        await self._ws.send(payload)
        logger.info(f"[BRIDGE] Task sent to VM: {task_description[:80]}...")

    async def send_resume(self):
        """Tell VM that citizen has submitted OTP — agent can continue."""
        if not self._ws:
            raise RuntimeError("Not connected to VM.")
        await self._ws.send(json.dumps({"type": "RESUME_OTP"}))
        logger.info("[BRIDGE] RESUME_OTP sent to VM.")

    async def listen(self):
        """
        Event loop — listens for VM events and dispatches to handlers.
        Runs until connection closes.
        """
        async for raw in self._ws:
            event = json.loads(raw)
            etype = event.get("event")
            logger.info(f"[BRIDGE] VM event: {etype}")

            if etype == "HUMAN_CHECKPOINT" and self._on_checkpoint:
                await self._on_checkpoint()

            elif etype == "DONE" and self._on_done:
                await self._on_done(event.get("result", ""))

            elif etype == "ERROR" and self._on_error:
                await self._on_error(event.get("detail", "Unknown error"))

    async def close(self):
        if self._ws:
            await self._ws.close()
            logger.info("[BRIDGE] VM connection closed.")
