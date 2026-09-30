"""
vdak-host/config.py
System-wide configuration for SEVA AI Host Controller.
Governs networking, OpenRouter inference, ODAV guardrails, and timeouts.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Host Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Inference Brain (OpenRouter)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "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")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    INFERENCE_TIMEOUT_SEC: float = 8.0

    # ODAV Invariants & Guardrails
    MAX_STEP_BUDGET: int = 8
    CONTEXT_WINDOW_SIZE: int = 3
    STALL_THRESHOLD: int = 2
    ACTION_TIMEOUT_MS: int = 5000

    # CDP Screencast & Stream
    STREAM_FPS: int = 25
    VIEWPORT_WIDTH: int = 1280
    VIEWPORT_HEIGHT: int = 720

    # Paths
    BASE_DIR: Path = Path(__file__).parent
    FRONTEND_DIR: Path = BASE_DIR / "frontend"
    MOCK_PORTALS_DIR: Path = BASE_DIR.parent / "mock_portals"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
