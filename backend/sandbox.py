"""
backend/sandbox.py
Playwright Browser Sandbox & Native CDP Screencast Compositor for SEVA AI.
Re-exports BrowserSandbox and PlaywrightSandbox from backend.browser_sandbox.
"""

from backend.browser_sandbox import (
    BrowserSandbox,
    PlaywrightSandbox,
    PORTAL_TEMPLATES,
    VALID_JPEG_BYTES
)

__all__ = ["BrowserSandbox", "PlaywrightSandbox", "PORTAL_TEMPLATES", "VALID_JPEG_BYTES"]
