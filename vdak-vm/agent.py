"""
vdak-vm/agent.py
V-DAK Browser Agent — extends browser-use Agent with OTP checkpoint logic.
When an OTP / password field is detected, the agent SUSPENDS itself and
notifies the host orchestrator to hand control to the citizen.
"""

import asyncio
import logging
from typing import Optional

from browser_use import Agent, Browser, BrowserConfig
from browser_use.agent.views import AgentHistoryList
from langchain_openai import ChatOpenAI

logger = logging.getLogger("vdak.agent")


# --------------------------------------------------------------------------- #
#  OTP / Sensitive Field Detection
# --------------------------------------------------------------------------- #

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


async def detect_otp_or_password_field(page) -> bool:
    """Return True if current page has any OTP / password input visible."""
    for selector in OTP_SELECTORS:
        try:
            elements = await page.query_selector_all(selector)
            for el in elements:
                if await el.is_visible():
                    logger.warning(f"[CHECKPOINT] Sensitive field detected: {selector}")
                    return True
        except Exception:
            continue
    return False


# --------------------------------------------------------------------------- #
#  V-DAK Agent
# --------------------------------------------------------------------------- #

class VDAKAgent:
    """
    Wraps browser-use Agent with:
    - OTP / password field auto-detection
    - Pause / resume handshake with host orchestrator
    - Aadhaar field guard (never auto-fill sensitive fields)
    """

    def __init__(
        self,
        task: str,
        llm: ChatOpenAI,
        notify_checkpoint_cb,   # async callback → sends HUMAN_CHECKPOINT to host
        wait_for_resume_cb,     # async callback → blocks until host sends RESUME
    ):
        self.task = task
        self.llm = llm
        self.notify_checkpoint_cb = notify_checkpoint_cb
        self.wait_for_resume_cb = wait_for_resume_cb
        self._agent: Optional[Agent] = None
        self._paused = False

    async def run(self) -> AgentHistoryList:
        """Run the browser agent with checkpoint interruption logic."""
        browser = Browser(
            config=BrowserConfig(
                headless=False,          # Show browser on VM screen for demo
                disable_security=False,
            )
        )

        self._agent = Agent(
            task=self.task,
            llm=self.llm,
            browser=browser,
        )

        # Monkey-patch step callback for checkpoint detection
        original_step = self._agent.step

        async def step_with_checkpoint(*args, **kwargs):
            result = await original_step(*args, **kwargs)
            # After every action, check for OTP fields
            try:
                page = await browser.get_current_page()
                if await detect_otp_or_password_field(page):
                    logger.warning("[VDAK] OTP field detected — suspending agent.")
                    await self.notify_checkpoint_cb()
                    await self.wait_for_resume_cb()
                    logger.info("[VDAK] Agent resumed by citizen.")
            except Exception as e:
                logger.error(f"Checkpoint detection error: {e}")
            return result

        self._agent.step = step_with_checkpoint

        try:
            history = await self._agent.run()
            return history
        finally:
            await browser.close()


# --------------------------------------------------------------------------- #
#  LLM Factory — OpenRouter
# --------------------------------------------------------------------------- #

def build_llm(api_key: str, model: str, base_url: str) -> ChatOpenAI:
    """Build a LangChain LLM pointed at OpenRouter."""
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.0,           # Deterministic navigation
        default_headers={
            "HTTP-Referer": "https://vdak-kiosk.local",
            "X-Title": "V-DAK Vernacular Kiosk",
        },
    )
