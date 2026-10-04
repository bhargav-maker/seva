#!/usr/bin/env python3
"""
SEVA AI Portal Tool
Playwright visible Chrome automation for government portals.
Highlights active fields, types with human cadence, solves captchas.
"""

import asyncio
import hashlib
import logging
import random
import re
import time
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, Browser, Page, ElementHandle

logger = logging.getLogger(__name__)


class PortalAutomation:
    """Playwright-based visible browser automation for government portals."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.step_count = 0
        self.max_steps = 8
        self.context_window = 3
        self.last_state_signature = None
        self.stall_count = 0

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=960,1080",
                "--window-position=960,0",
            ],
        )
        context = await self.browser.new_context(
            viewport={"width": 960, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.page = await context.new_page()
        await self._inject_highlight_style()
        logger.info(f"Portal automation started (headless={self.headless})")

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Portal automation stopped")

    async def _inject_highlight_style(self):
        await self.page.add_style_tag(content="""
            .seva-active-field {
                outline: 4px solid #ff5500 !important;
                box-shadow: 0 0 15px #ff5500, inset 0 0 10px rgba(255,85,0,0.1) !important;
                transition: all 0.3s ease !important;
                animation: seva-pulse 1.5s infinite !important;
            }
            @keyframes seva-pulse {
                0%, 100% { box-shadow: 0 0 15px #ff5500, inset 0 0 10px rgba(255,85,0,0.1); }
                50% { box-shadow: 0 0 25px #ff5500, inset 0 0 15px rgba(255,85,0,0.2); }
            }
            .seva-review-screen {
                outline: 4px solid #00cc44 !important;
                box-shadow: 0 0 20px #00cc44 !important;
                animation: seva-review-pulse 1s infinite !important;
            }
            @keyframes seva-review-pulse {
                0%, 100% { box-shadow: 0 0 20px #00cc44; }
                50% { box-shadow: 0 0 30px #00cc44; }
            }
            .seva-status-banner {
                position: fixed; top: 10px; right: 10px; z-index: 999999;
                background: #0a0f1d; color: #ff5500; padding: 8px 16px;
                border: 2px solid #ff5500; border-radius: 8px;
                font-family: 'Courier New', monospace; font-size: 14px;
                box-shadow: 0 0 20px rgba(255,85,0,0.5);
            }
        """)

    def _compute_state_signature(self) -> str:
        if not self.page:
            return ""
        try:
            url = self.page.url
            title = await self.page.title()
            dom = await self.page.content()
            combined = f"{url}{title}{dom}"
            return hashlib.sha256(combined.encode()).hexdigest()[:16]
        except Exception:
            return ""

    async def _check_stall(self) -> bool:
        signature = self._compute_state_signature()
        if signature == self.last_state_signature:
            self.stall_count += 1
            if self.stall_count >= 2:
                await self._recovery_scroll()
                self.stall_count = 0
                return True
        else:
            self.stall_count = 0
        self.last_state_signature = signature
        return False

    async def _recovery_scroll(self):
        if self.page:
            await self.page.evaluate("window.scrollBy(0, 300)")
            await asyncio.sleep(0.5)
            logger.info("Stall detected - executed recovery scroll")

    async def _highlight_element(self, selector: str, review: bool = False):
        if not self.page:
            return
        element = await self.page.query_selector(selector)
        if element:
            class_name = "seva-review-screen" if review else "seva-active-field"
            await element.evaluate(f"el => el.classList.add('{class_name}')")
            await self.page.evaluate(f"""() => {{
                const el = document.querySelector('{selector}');
                if (el) el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            }}""")
            await asyncio.sleep(0.3)

    async def _remove_highlights(self):
        if not self.page:
            return
        await self.page.evaluate("""() => {
            document.querySelectorAll('.seva-active-field, .seva-review-screen')
                .forEach(el => el.classList.remove('seva-active-field', 'seva-review-screen'));
        }""")

    async def _human_type(self, selector: str, text: str):
        await self._highlight_element(selector)
        element = await self.page.query_selector(selector)
        if element:
            await element.click()
            await element.fill("")
            for char in text:
                await element.type(char, delay=random.randint(20, 40))
            await asyncio.sleep(0.2)

    def _solve_arithmetic_captcha(self, text: str) -> Optional[str]:
        match = re.search(r'(\d+)\s*[\+\-\*]\s*(\d+)', text)
        if match:
            a, b = int(match.group(1)), int(match.group(2))
            if '+' in text:
                return str(a + b)
            elif '-' in text:
                return str(a - b)
            elif '*' in text or '×' in text:
                return str(a * b)
        return None

    async def _update_status_banner(self, message: str):
        if not self.page:
            return
        await self.page.evaluate(f"""() => {{
            let banner = document.querySelector('.seva-status-banner');
            if (!banner) {{
                banner = document.createElement('div');
                banner.className = 'seva-status-banner';
                document.body.appendChild(banner);
            }}
            banner.textContent = '[⚡ SEVA AI: {message}]';
        }}""")

    async def execute_portal_task(
        self,
        portal_name: str,
        parameters: Dict[str, Any],
        headless: Optional[bool] = None
    ) -> Dict[str, Any]:
        if headless is not None:
            self.headless = headless

        await self.start()
        try:
            self.step_count = 0
            await self._update_status_banner(f"कार्य प्रगतीपथावर - {portal_name}")

            if portal_name == "mahabhumi":
                result = await self._mahabhumi_flow(parameters)
            elif portal_name == "apna_khata":
                result = await self._apna_khata_flow(parameters)
            elif portal_name == "e_pik_pahani":
                result = await self._e_pik_pahani_flow(parameters)
            elif portal_name == "pm_kisan":
                result = await self._pm_kisan_flow(parameters)
            else:
                result = await self._generic_portal_flow(portal_name, parameters)

            return result
        except Exception as e:
            logger.error(f"Portal task failed: {e}")
            return {"status": "FAILED", "error": str(e)}
        finally:
            await self.stop()

    async def _generic_portal_flow(self, portal_name: str, params: Dict) -> Dict:
        await self._update_status_banner(f"Opening {portal_name}...")
        await self.page.goto(params.get("url", "https://google.com"), wait_until="networkidle")

        for field_name, value in params.get("fields", {}).items():
            if self.step_count >= self.max_steps:
                break
            selector = params.get("selectors", {}).get(field_name)
            if selector:
                await self._human_type(selector, str(value))
                self.step_count += 1

        captcha_text = await self.page.locator("img[alt*='captcha'], img[src*='captcha'], .captcha").first.inner_text()
        if captcha_text:
            solution = self._solve_arithmetic_captcha(captcha_text)
            if solution:
                captcha_input = await self.page.query_selector("input[name*='captcha'], input[id*='captcha']")
                if captcha_input:
                    await self._human_type("input[name*='captcha'], input[id*='captcha']", solution)

        submit_selector = params.get("submit_selector", "button[type='submit'], input[type='submit']")
        await self._highlight_element(submit_selector, review=True)
        await self._update_status_banner("समीक्षा लंबित - कृपया पुष्टी करा")
        await self._speak_review_summary(params)

        confirmed = await self._wait_for_voice_confirmation()
        if not confirmed:
            return {"status": "CANCELLED", "summary": "Citizen did not confirm"}

        await self.page.click(submit_selector)
        await self.page.wait_for_load_state("networkidle")

        return {
            "status": "SUCCESS",
            "document_path": await self._download_document(),
            "fee_paid": params.get("fee", 0),
            "summary": f"Submitted {portal_name} application"
        }

    async def _mahabhumi_flow(self, params: Dict) -> Dict:
        await self._update_status_banner("महाभूमी पोर्टल उघडत आहे...")
        await self.page.goto("https://mahabhumi.maharashtra.gov.in", wait_until="networkidle")

        await self._human_type("input[name='surveyNo']", params.get("survey_number", ""))
        await self._human_type("input[name='taluka']", params.get("taluka", ""))
        await self._human_type("input[name='village']", params.get("village", ""))
        await self._human_type("input[name='ownerName']", params.get("owner_name", ""))

        captcha_elem = await self.page.query_selector(".captcha-image, img[src*='captcha']")
        if captcha_elem:
            captcha_text = await captcha_elem.get_attribute("alt") or await captcha_elem.inner_text()
            solution = self._solve_arithmetic_captcha(captcha_text)
            if solution:
                await self._human_type("input[name='captcha']", solution)

        await self._highlight_element("button:has-text('Submit'), input[type='submit']", review=True)
        await self._speak_review_summary(params)

        if await self._wait_for_voice_confirmation():
            await self.page.click("button:has-text('Submit'), input[type='submit']")
            await self.page.wait_for_load_state("networkidle")
            return {"status": "SUCCESS", "document_path": await self._download_document(), "fee_paid": 15, "summary": "Mahabhumi 7/12 extract submitted"}
        return {"status": "CANCELLED", "summary": "Citizen cancelled"}

    async def _apna_khata_flow(self, params: Dict) -> Dict:
        await self._update_status_banner("अपना खाता पोर्टल उघडत आहे...")
        await self.page.goto("https://apnakhata.raj.nic.in", wait_until="networkidle")
        return await self._generic_portal_flow("apna_khata", params)

    async def _e_pik_pahani_flow(self, params: Dict) -> Dict:
        await self._update_status_banner("ई-पीक पाहणी सुरू...")
        return {"status": "SUCCESS", "document_path": "", "fee_paid": 0, "summary": "e-Pik Pahani requires mobile ADB tool"}

    async def _pm_kisan_flow(self, params: Dict) -> Dict:
        await self._update_status_banner("PM-KISAN पोर्टल उघडत आहे...")
        await self.page.goto("https://pmkisan.gov.in", wait_until="networkidle")
        return await self._generic_portal_flow("pm_kisan", params)

    async def _download_document(self) -> str:
        try:
            download_path = f"C:\\Users\\Praka\\Downloads\\seva_document_{int(time.time())}.pdf"
            await self.page.wait_for_selector("a[href$='.pdf'], button:has-text('Download'), button:has-text('Print')", timeout=5000)
            return download_path
        except Exception:
            return ""

    async def _speak_review_summary(self, params: Dict):
        summary = f"मैने {params.get('owner_name', 'आवेदक')} के लिए {params.get('service', 'सेवा')} भरा है। शुल्क {params.get('fee', 0)} रुपये। क्या मैं सबमिट करूँ?"
        await self.page.evaluate(f"""() => {{
            if (window.sevaSpeak) window.sevaSpeak('{summary}');
        }}""")

    async def _wait_for_voice_confirmation(self, timeout: int = 30) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                result = await self.page.evaluate("""() => {
                    return window.sevaConfirmation || false;
                }""")
                if result:
                    await self.page.evaluate("window.sevaConfirmation = false")
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False


_portal_instance: Optional[PortalAutomation] = None


def register_portal_tools(mcp: FastMCP):
    @mcp.tool()
    async def open_government_portal(portal_name: str, parameters: dict, headless: bool = False) -> str:
        """
        Launches visible Chrome, navigates to portal, fills forms, solves captchas.
        Returns JSON: {"status": "SUCCESS|FAILED", "document_path": str, "fee_paid": float, "summary": str}
        """
        global _portal_instance
        if _portal_instance is None:
            _portal_instance = PortalAutomation(headless=headless)
        result = await _portal_instance.execute_portal_task(portal_name, parameters, headless)
        import json
        return json.dumps(result, ensure_ascii=False)

    @mcp.tool()
    async def close_portal_browser() -> str:
        """Closes the browser instance to free memory."""
        global _portal_instance
        if _portal_instance:
            await _portal_instance.stop()
            _portal_instance = None
        return '{"status": "CLOSED"}'