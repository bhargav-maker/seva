"""
vdak-vm/browser_controller.py
Isolated Playwright Chromium Sandbox & CDP Screencast Controller for SEVA AI.
Enforces:
1. Native Chrome DevTools Protocol (CDP) screencasting at >= 20 FPS
2. Extraction of top 25 interactive DOM elements (button, a, input, select)
3. Zero physical host OS cursor hijacking
4. 5000ms timeout guards on all discrete browser actions
"""

import asyncio
import base64
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

logger = logging.getLogger("vdak.vm.browser_controller")

DEFAULT_TIMEOUT_MS = 5000
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 720

class BrowserController:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._cdp_session = None
        self._latest_frame_bytes: bytes = b""
        self._frame_lock = asyncio.Lock()
        self._is_screencasting = False

    async def initialize(self) -> bool:
        """Launches isolated headless Chromium without OS desktop takeover."""
        if self._browser is not None:
            return True
        try:
            logger.info("[BrowserController] Launching Chromium sandbox...")
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    f"--window-size={VIEWPORT_WIDTH},{VIEWPORT_HEIGHT}",
                ],
            )
            self._context = await self._browser.new_context(
                viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) SEVA-AI-Kiosk/2.0",
                device_scale_factor=1.0,
            )
            self._page = await self._context.new_page()
            self._page.set_default_timeout(DEFAULT_TIMEOUT_MS)

            await self._start_cdp_screencast()
            logger.info("[BrowserController] Sandbox initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"[BrowserController] Launch failed: {e}")
            return False

    async def _start_cdp_screencast(self) -> None:
        """Starts native Chrome DevTools Protocol screencast for 20-25 FPS streaming."""
        if not self._page or self._is_screencasting:
            return
        try:
            self._cdp_session = await self._context.new_cdp_session(self._page)
            
            async def on_screencast_frame(event):
                try:
                    data = event.get("data")
                    session_id = event.get("sessionId")
                    if data:
                        raw_bytes = base64.b64decode(data)
                        async with self._frame_lock:
                            self._latest_frame_bytes = raw_bytes
                    if self._cdp_session and session_id:
                        await self._cdp_session.send("Page.screencastFrameAck", {"sessionId": session_id})
                except Exception:
                    pass

            self._cdp_session.on("Page.screencastFrame", on_screencast_frame)
            await self._cdp_session.send("Page.startScreencast", {
                "format": "jpeg",
                "quality": 80,
                "maxWidth": VIEWPORT_WIDTH,
                "maxHeight": VIEWPORT_HEIGHT,
                "everyNthFrame": 1
            })
            self._is_screencasting = True
            logger.info("[BrowserController] CDP Screencast stream engaged.")
        except Exception as e:
            logger.warning(f"[BrowserController] CDP screencast setup fallback: {e}")

    async def get_latest_frame(self) -> bytes:
        """Returns the most recent raw JPEG frame bytes."""
        async with self._frame_lock:
            if self._latest_frame_bytes:
                return self._latest_frame_bytes
        # Fallback to screenshot if CDP frame is not yet populated
        if self._page:
            try:
                return await self._page.screenshot(type="jpeg", quality=75)
            except Exception:
                pass
        return b""

    async def mjpeg_frame_generator(self):
        """Yields continuous multipart JPEG frame stream at ~25 FPS."""
        frame_interval = 1.0 / 25.0
        while True:
            t0 = time.time()
            frame = await self.get_latest_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
                    + frame + b"\r\n"
                )
            elapsed = time.time() - t0
            sleep_time = max(0.005, frame_interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def extract_interactive_elements(self) -> Tuple[str, str, List[Dict[str, Any]]]:
        """
        Extracts active page URL, document title, and top 25 interactive DOM elements:
        <button>, <a>, <input>, <select>, <textarea>.
        """
        if not self._page:
            return "about:blank", "Empty", []

        url = self._page.url
        title = await self._page.title()

        extractor_script = """
        () => {
            const elements = [];
            const interactiveSelectors = 'button, a[href], input:not([type="hidden"]), select, textarea, [role="button"]';
            const nodes = Array.from(document.querySelectorAll(interactiveSelectors));

            for (const el of nodes) {
                if (elements.length >= 25) break;

                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || rect.width <= 0 || rect.height <= 0) {
                    continue;
                }

                let text = (el.innerText || el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim();
                text = text.replace(/\\s+/g, ' ').substring(0, 60);

                let selector = '';
                if (el.id) {
                    selector = `#${el.id}`;
                } else if (el.name) {
                    selector = `[name="${el.name}"]`;
                } else if (el.className && typeof el.className === 'string') {
                    const firstClass = el.className.split(' ').filter(c => c && !c.includes(':'))[0];
                    if (firstClass) selector = `${el.tagName.toLowerCase()}.${firstClass}`;
                }
                if (!selector) {
                    selector = el.tagName.toLowerCase();
                }

                elements.push({
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    id: el.id || '',
                    name: el.name || '',
                    text: text,
                    selector: selector,
                    placeholder: el.placeholder || '',
                    disabled: el.disabled || false
                });
            }
            return elements;
        }
        """
        try:
            elements = await self._page.evaluate(extractor_script)
            return url, title, elements[:25]
        except Exception as e:
            logger.error(f"[BrowserController] DOM extraction error: {e}")
            return url, title, []

    async def execute_action(self, action: str, selector: str, value: str) -> Tuple[bool, str]:
        """
        Executes discrete browser action with a strict 5000ms timeout guard.
        """
        if not self._page:
            return False, "Browser not initialized"

        action = action.lower()
        try:
            if action == "navigate":
                target_url = value or selector
                if not target_url.startswith("http://") and not target_url.startswith("https://") and not target_url.startswith("file://"):
                    target_url = f"http://{target_url}"
                await self._page.goto(target_url, wait_until="commit", timeout=DEFAULT_TIMEOUT_MS)
                return True, f"Navigated to {target_url}"

            elif action == "click":
                if not selector:
                    return False, "Missing selector for click action"
                await self._page.click(selector, timeout=DEFAULT_TIMEOUT_MS)
                return True, f"Clicked element: {selector}"

            elif action == "fill":
                if not selector:
                    return False, "Missing selector for fill action"
                await self._page.fill(selector, value, timeout=DEFAULT_TIMEOUT_MS)
                return True, f"Filled '{value}' into {selector}"

            elif action == "scroll":
                delta_y = 400
                if value and value.isdigit():
                    delta_y = int(value)
                await self._page.evaluate(f"window.scrollBy(0, {delta_y})")
                return True, f"Scrolled {delta_y}px vertically"

            elif action == "wait":
                wait_ms = 1000
                if value and value.isdigit():
                    wait_ms = min(5000, int(value))
                await asyncio.sleep(wait_ms / 1000.0)
                return True, f"Waited {wait_ms}ms"

            elif action == "finish":
                return True, "Task completed successfully"

            elif action == "fail":
                return False, f"Action flagged as failed: {value}"

            else:
                return False, f"Unknown action: {action}"

        except Exception as e:
            logger.warning(f"[BrowserController] Execution failed on action '{action}' ({selector}): {e}")
            return False, str(e)

    async def close(self) -> None:
        """Terminates Chromium and releases all resources."""
        self._is_screencasting = False
        try:
            if self._cdp_session:
                await self._cdp_session.detach()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass
        self._browser = None
        self._page = None
        logger.info("[BrowserController] Closed sandbox.")
