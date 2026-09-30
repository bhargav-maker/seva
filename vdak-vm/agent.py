"""
vdak-vm/agent.py
Autonomous Browser Automation & Screen Streaming Agent for SEVA AI.
Controls headless/headful Chromium sessions and streams frames to the host kiosk.
"""

import asyncio
import base64
import io
import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

from PIL import Image
from playwright.async_api import async_playwright, Browser, Page, Playwright

logger = logging.getLogger("vdak.agent")
logging.basicConfig(level=logging.INFO)

SCREEN_FRAME_PATH = Path(__file__).parent / "latest_frame.jpg"

class KioskBrowserAgent:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._streaming = False
        self._stream_task: Optional[asyncio.Task] = None

    async def start(self) -> bool:
        """Launches Chromium with flags optimized for VM/sandboxed kiosk environments."""
        if self._browser is not None:
            return True
        try:
            logger.info("[AGENT] Launching Chromium browser...")
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--window-size=1280,720",
                ],
            )
            context = await self._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) SEVA-AI-Kiosk/1.0",
            )
            self._page = await context.new_page()
            logger.info("[AGENT] Browser launched successfully.")
            return True
        except Exception as e:
            logger.error(f"[AGENT] Failed to launch browser: {e}")
            return False

    async def stop(self):
        """Cleanly terminates the browser and background streaming."""
        self._streaming = False
        if self._stream_task:
            self._stream_task.cancel()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._browser = None
        self._page = None
        logger.info("[AGENT] Browser session closed.")

    async def capture_frame(self) -> Optional[bytes]:
        """Captures a screenshot of the current viewport and caches it as JPEG."""
        if not self._page:
            return None
        try:
            screenshot_bytes = await self._page.screenshot(type="jpeg", quality=65)
            # Write to disk for host polling if using file sharing
            with open(SCREEN_FRAME_PATH, "wb") as f:
                f.write(screenshot_bytes)
            return screenshot_bytes
        except Exception as e:
            logger.debug(f"[AGENT] Frame capture skipped: {e}")
            return None

    async def _stream_loop(self, fps: int = 5):
        """Continuous background capture loop for live screen-sharing."""
        interval = 1.0 / fps
        while self._streaming:
            await self.capture_frame()
            await asyncio.sleep(interval)

    def start_streaming(self, fps: int = 5):
        """Starts background frame capture loop."""
        if not self._streaming:
            self._streaming = True
            self._stream_task = asyncio.create_task(self._stream_loop(fps))

    async def navigate_to(self, url: str) -> bool:
        """Navigates to a portal URL with load state handling."""
        if not self._page:
            if not await self.start():
                return False
        try:
            logger.info(f"[AGENT] Navigating to: {url}")
            await self._page.goto(url, wait_until="networkidle", timeout=30000)
            await self.capture_frame()
            return True
        except Exception as e:
            logger.error(f"[AGENT] Navigation error to {url}: {e}")
            return False

    async def fill_field(self, selector: str, value: str) -> bool:
        """Fills a form field cleanly."""
        if not self._page:
            return False
        try:
            await self._page.wait_for_selector(selector, timeout=8000)
            await self._page.fill(selector, value)
            await self.capture_frame()
            return True
        except Exception as e:
            logger.warning(f"[AGENT] Failed to fill {selector}: {e}")
            return False

    async def click_element(self, selector: str) -> bool:
        """Clicks an interactable element on the portal."""
        if not self._page:
            return False
        try:
            await self._page.wait_for_selector(selector, timeout=8000)
            await self._page.click(selector)
            await asyncio.sleep(1.0)
            await self.capture_frame()
            return True
        except Exception as e:
            logger.warning(f"[AGENT] Failed to click {selector}: {e}")
            return False

    async def get_page_text(self) -> str:
        """Extracts visible text content from the current portal view."""
        if not self._page:
            return ""
        try:
            return await self._page.inner_text("body")
        except Exception as e:
            logger.error(f"[AGENT] Failed to read page text: {e}")
            return ""
