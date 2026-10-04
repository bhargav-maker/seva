#!/usr/bin/env python3
"""
SEVA AI Kiosk - Main Entry Point
Voice-First Autonomous Gram Panchayat Kiosk Engine
Built on Sagar Tamang's F.R.I.D.A.Y. (FastMCP + LiveKit)
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from friday_core.server import app
from friday_core.voice_agent import VoiceAgent, VoiceConfig
from vision.presence_detector import PresenceDetector, PresenceConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SevaKiosk:
    """Main SEVA AI Kiosk orchestrator."""

    def __init__(self):
        self.voice_agent: VoiceAgent = None
        self.presence_detector: PresenceDetector = None
        self.running = False

    async def start(self):
        logger.info("=" * 60)
        logger.info("SEVA AI KIOSK STARTING")
        logger.info("Voice-First Autonomous Gram Panchayat Assistant")
        logger.info("Built on Sagar Tamang's F.R.I.D.A.Y. Engine")
        logger.info("=" * 60)

        # Configuration
        voice_config = VoiceConfig(
            language=os.getenv("SEVA_LANGUAGE", "mr-IN"),
            presence_dwell_seconds=1.0,
            walk_away_seconds=15.0
        )

        # Initialize Voice Agent (LiveKit + Gemini)
        self.voice_agent = VoiceAgent(voice_config)
        await self.voice_agent.start()

        # Initialize Presence Detector (Webcam)
        self.presence_detector = PresenceDetector(
            config=PresenceConfig(
                dwell_seconds=1.0,
                walk_away_seconds=15.0
            ),
            on_dwell=self._on_dwell_triggered,
            on_walk_away=self._on_walk_away
        )
        self.presence_detector.start()

        self.running = True
        logger.info("SEVA AI Kiosk fully operational")

        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await self.stop()

    async def stop(self):
        logger.info("Shutting down SEVA AI Kiosk...")
        self.running = False

        if self.voice_agent:
            await self.voice_agent.stop()
        if self.presence_detector:
            self.presence_detector.stop()

        logger.info("SEVA AI Kiosk stopped")

    async def _on_dwell_triggered(self):
        logger.info("DWELL TRIGGER: Citizen detected - Proactive greeting initiated")
        if self.voice_agent:
            await self.voice_agent._proactive_greeting()

    async def _on_walk_away(self):
        logger.warning("WALK AWAY: Citizen left - Privacy purge initiated")
        if self.voice_agent:
            await self.voice_agent._privacy_purge()


async def main():
    kiosk = SevaKiosk()

    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(kiosk.stop()))

    await kiosk.start()


if __name__ == "__main__":
    # Windows-specific event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())