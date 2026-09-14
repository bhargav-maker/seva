"""
vdak-vm/agent.py — Updated with page-ready callback for live streaming
"""

import asyncio
import logging
from typing import Callable, Optional

from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI

logger = logging.getLogger("vdak.agent")

OTP_SELECTORS = [
    'input[type="password"]',
    'input[autocomplete="one-time-code"]',
    'input[autocomplete="current-password"]',
    'input[name*="otp" i]',
    'input[name*="pin" i]',
    'input[placeholder*="otp" i]',
    'input[placeholder*="password" i]',
    'input[id*="otp" i]',
]


async def detect_sensitive_field(page) -> bool:
    for sel in OTP_SELECTORS:
        try:
            elements = await page.query_selector_all(sel)
            for el in elements:
                if await el.is_visible():
                    logger.warning(f"[AGENT] Sensitive field: {sel}")
                    return True
        except Exception:
            continue
    return False


class VDAKAgent:
    """
    browser-use Agent extended with:
    - OTP/sensitive field auto-detection and pause
    - Page-ready callback for live viewport streaming
    """

    def __init__(
        self,
        task: str,
        llm: ChatOpenAI,
        notify_checkpoint_cb: Callable,
        wait_for_resume_cb:   Callable,
        on_page_ready_cb:     Optional[Callable] = None,
    ):
        self.task                 = task
        self.llm                  = llm
        self.notify_checkpoint_cb = notify_checkpoint_cb
        self.wait_for_resume_cb   = wait_for_resume_cb
        self.on_page_ready_cb     = on_page_ready_cb

    async def run(self):
        browser = Browser(
            config=BrowserConfig(
                headless=False,
                disable_security=False,
            )
        )

        agent = Agent(
            task=self.task,
            llm=self.llm,
            browser=browser,
        )

        # Expose Playwright page for live streaming
        try:
            page = await browser.get_current_page()
            if self.on_page_ready_cb:
                self.on_page_ready_cb(page)
        except Exception as e:
            logger.warning(f"[AGENT] Could not get page ref: {e}")

        original_step = agent.step

        async def step_with_checkpoint(*args, **kwargs):
            result = await original_step(*args, **kwargs)
            try:
                page = await browser.get_current_page()
                # Update streaming reference
                if self.on_page_ready_cb:
                    self.on_page_ready_cb(page)
                if await detect_sensitive_field(page):
                    logger.warning("[AGENT] OTP field — pausing.")
                    await self.notify_checkpoint_cb()
                    await self.wait_for_resume_cb()
            except Exception as e:
                logger.debug(f"[AGENT] Step check error: {e}")
            return result

        agent.step = step_with_checkpoint

        try:
            return await agent.run()
        finally:
            await browser.close()


def build_llm(api_key: str, model: str, base_url: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.0,
        default_headers={
            "HTTP-Referer": "https://seva-ai.local",
            "X-Title":      "SEVA AI Kiosk",
        },
    )
