"""
backend/config.py
Central Configuration Settings for SEVA AI Kiosk Platform.

Manages:
- Server settings (host, port, reload, debug)
- Session step budget (hard 8-step ceiling)
- ODAV engine parameters (DOM element ceilings, stall thresholds, state signature lengths)
- Browser sandbox & CDP screencast parameters (FPS, dimensions, quality, timeouts)
- LLM API gateway settings (Gemini, OpenRouter, fallback parameters)
- Multi-lingual localization settings (Marathi, Hindi, English)
- DPDP Act 2023 compliance settings (ephemeral data purge)
- Base directory paths & static mounts
"""

import os
from pathlib import Path
from typing import List, Dict

# Base Directory Resolution
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
MOCK_PORTALS_DIR = BASE_DIR / "mock_portals"

# Ensure runtime directories exist
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
MOCK_PORTALS_DIR.mkdir(parents=True, exist_ok=True)

# Server Configuration
HOST: str = os.getenv("SEVA_HOST", "0.0.0.0")
PORT: int = int(os.getenv("SEVA_PORT", "8000"))
DEBUG: bool = os.getenv("SEVA_DEBUG", "false").lower() in ("true", "1", "yes")

# Loop Guards & Step Budget (M3 Requirement)
MAX_STEPS: int = int(os.getenv("SEVA_MAX_STEPS", "8"))  # Hard 8-step budget guard
CONTEXT_HISTORY_LIMIT: int = 3  # Pruning: Retain last 3 step deltas in scratchpad
STALL_THRESHOLD: int = 2  # Detect stalls across 2 consecutive identical states
RECEIPT_PREFIX: str = "SEVA"

# ODAV Engine Parameters
DOM_EXTRACTION_LIMIT: int = 25  # Max interactive DOM elements extracted per page
STATE_SIGNATURE_LENGTH: int = 16  # SHA-256 hash slice length S(t) = SHA256(...)[:16]

# Browser Sandbox & CDP Screencast Configuration
HEADLESS: bool = os.getenv("SEVA_HEADLESS", "true").lower() in ("true", "1", "yes")
STREAM_FPS: int = int(os.getenv("SEVA_STREAM_FPS", "25"))  # Target >= 20 FPS
JPEG_QUALITY: int = int(os.getenv("SEVA_JPEG_QUALITY", "60"))
VIEWPORT_WIDTH: int = 1280
VIEWPORT_HEIGHT: int = 720
ACTION_TIMEOUT_MS: int = 6000
NAVIGATE_TIMEOUT_MS: int = 15000

# Cloud LLM Configuration
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_REST_BASE: str = os.getenv(
    "GEMINI_REST_BASE",
    "https://generativelanguage.googleapis.com/v1beta/models"
)

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct:free")
_raw_or_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_BASE_URL: str = (
    _raw_or_base if _raw_or_base.endswith("/chat/completions")
    else f"{_raw_or_base.rstrip('/')}/chat/completions"
)
LLM_TIMEOUT_SEC: float = 8.0  # 8-second timeout guard per R1

# Localization & Supported Languages
SUPPORTED_LANGUAGES: List[str] = ["mr-IN", "hi-IN", "en-IN", "mr", "hi", "en"]
DEFAULT_LANGUAGE: str = "mr-IN"

# Digital Personal Data Protection (DPDP) Act Compliance
EPHEMERAL_MODE: bool = True  # Zero disk persistence of citizen PII; purge on reset

# Citizen Public Service Portal Keyword Mappings
PORTAL_KEYWORD_MAP: Dict[str, str] = {
    "income": "income",
    "उत्पन्न": "income",
    "दाखला": "income",
    "satbara": "satbara",
    "सातबारा": "satbara",
    "७/१२": "satbara",
    "जमीन": "satbara",
    "pension": "pension",
    "पेन्शन": "pension",
    "निराधार": "pension",
    "ration": "ration",
    "रेशन": "ration",
    "धान्य": "ration",
    "mahadbt": "mahadbt",
    "शेतकरी": "mahadbt",
    "अनुदान": "mahadbt",
    "caste": "income",
    "जात": "income",
}
