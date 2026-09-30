"""
backend/app.py
FastAPI Host Application for SEVA AI Autonomous Kiosk Platform.

Exposes REST APIs:
  - POST /api/start-task: Initialize citizen session, sandbox, and portal state.
  - POST /api/step: Coordinate single Observe-Decide-Act-Verify (ODAV) loop cycle.
  - GET  /api/stream: Continuous multipart/x-mixed-replace MJPEG screencast stream (>= 20 FPS).
  - GET  /api/session-state: Real-time query of active task, budget, history, and status.
  - POST /api/reset: Zero-data ephemeral memory purge (DPDP Act 2023 compliance) and sandbox teardown.
  - GET  /api/health: System health and diagnostic check.
  - Static Mounts: Mounts frontend assets and simulated Maharashtra e-governance portals.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

try:
    from backend.config import (
        FRONTEND_DIR,
        MOCK_PORTALS_DIR,
        MAX_STEPS,
        DEFAULT_LANGUAGE,
        PORTAL_KEYWORD_MAP,
        DEBUG
    )
    from backend.models import (
        StartTaskRequest,
        StartTaskResponse,
        StepRequest,
        StepResponse,
        SessionState,
        ResetResponse
    )
    from backend.browser_sandbox import BrowserSandbox
    from backend.state_manager import SessionStateManager, get_default_state_manager, reset_default_state_manager
    from backend.odav_engine import ODAVEngine
except ImportError:
    from config import (
        FRONTEND_DIR,
        MOCK_PORTALS_DIR,
        MAX_STEPS,
        DEFAULT_LANGUAGE,
        PORTAL_KEYWORD_MAP,
        DEBUG
    )
    from models import (
        StartTaskRequest,
        StartTaskResponse,
        StepRequest,
        StepResponse,
        SessionState,
        ResetResponse
    )
    from browser_sandbox import BrowserSandbox
    from state_manager import SessionStateManager, get_default_state_manager, reset_default_state_manager
    from odav_engine import ODAVEngine

logger = logging.getLogger("seva.app")
logging.basicConfig(level=logging.INFO if not DEBUG else logging.DEBUG)

# Runtime Singletons
_sandbox: Optional[BrowserSandbox] = None
_state_manager: Optional[SessionStateManager] = None
_odav_engine: Optional[ODAVEngine] = None


def get_sandbox() -> BrowserSandbox:
    """Returns singleton BrowserSandbox instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = BrowserSandbox()
    return _sandbox


def get_state_manager() -> SessionStateManager:
    """Returns singleton SessionStateManager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = get_default_state_manager()
    return _state_manager


def get_odav_engine() -> ODAVEngine:
    """Returns singleton ODAVEngine instance."""
    global _odav_engine
    if _odav_engine is None:
        _odav_engine = ODAVEngine(
            sandbox=get_sandbox(),
            state_manager=get_state_manager()
        )
    return _odav_engine


def set_custom_engine(engine: ODAVEngine) -> None:
    """Dependency injection helper for unit tests."""
    global _odav_engine, _sandbox, _state_manager
    _odav_engine = engine
    _sandbox = engine.sandbox
    _state_manager = engine.state_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: Initializes and cleanly closes browser resources."""
    logger.info("[APP] Starting SEVA AI Kiosk Platform daemon...")
    yield
    logger.info("[APP] Shutting down SEVA AI Kiosk Platform daemon...")
    global _sandbox
    if _sandbox is not None and _sandbox.is_running:
        try:
            await _sandbox.close()
        except Exception as e:
            logger.debug(f"[APP] Error closing sandbox during shutdown: {e}")


# Initialize FastAPI Application
app = FastAPI(
    title="SEVA AI Kiosk Platform",
    description="Autonomous vernacular digital kiosk for Indian citizen public services",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Kiosk UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _match_portal_for_task(task_text: str) -> str:
    """Determines simulated Maharashtra portal based on citizen intent."""
    lower = task_text.lower()
    for kw, portal in PORTAL_KEYWORD_MAP.items():
        if kw in lower:
            return portal
    return "income"  # default simulation portal


# --- REST API Endpoints ---

@app.post(
    "/api/start-task",
    response_model=StartTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize Citizen Session"
)
async def start_task(request: StartTaskRequest):
    """
    Initializes a new citizen session and starts the isolated browser sandbox.
    Loads matching simulated government portal based on citizen intent.
    """
    task_text = request.task.strip()
    if not task_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task description cannot be empty."
        )

    sandbox = get_sandbox()
    state_mgr = get_state_manager()
    engine = get_odav_engine()

    # Initialize headless browser sandbox session
    if not sandbox.is_running:
        await sandbox.initialize()

    # Determine and load appropriate portal simulation
    portal_name = _match_portal_for_task(task_text)
    await sandbox.load_portal_simulation(portal_name)

    # Initialize session state tracking
    session_data = state_mgr.start_session(
        task=task_text,
        language=request.language or DEFAULT_LANGUAGE
    )

    # Capture and record initial baseline state signature
    try:
        initial_sig = await sandbox.get_state_signature()
        state_mgr.current_signature = initial_sig
        state_mgr.current_url = sandbox.current_url
    except Exception as e:
        logger.warning(f"[APP] Could not fetch initial state signature: {e}")

    logger.info(
        f"[APP] Started task '{task_text[:40]}...' | Portal: {portal_name} | "
        f"Session: {state_mgr.session_id}"
    )

    return StartTaskResponse(
        status="started",
        session_id=state_mgr.session_id,
        step=state_mgr.step
    )


@app.post(
    "/api/step",
    response_model=StepResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Single ODAV Cycle"
)
async def execute_step(request: Optional[StepRequest] = None):
    """
    Executes a single Observe-Decide-Act-Verify (ODAV) loop cycle.
    Enforces the hard 8-step budget ceiling, state mutation audits,
    and completion gates.
    """
    state_mgr = get_state_manager()
    engine = get_odav_engine()

    # Validate active session
    if not state_mgr.active and not state_mgr.finished and not state_mgr.is_budget_exceeded():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active citizen session. Please call /api/start-task first."
        )

    force_action = request.force_action if request else None

    try:
        result = await engine.step(force_action=force_action)
        return StepResponse(
            step=result["step"],
            state_signature=result["state_signature"],
            action=result["action"],
            stalled=result.get("stalled", False),
            status=result.get("status", "progressing"),
            feedback=result.get("feedback", "")
        )
    except Exception as e:
        logger.error(f"[APP] Step execution exception: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ODAV step execution failed: {str(e)}"
        )


@app.get(
    "/api/stream",
    summary="Native CDP Screencast MJPEG Video Stream"
)
async def stream_screencast():
    """
    Returns continuous multipart/x-mixed-replace MJPEG stream
    from native CDP screencast frames at >= 20 FPS.
    """
    sandbox = get_sandbox()
    if not sandbox.is_running:
        # Auto-initialize sandbox if not yet running
        await sandbox.initialize()

    return StreamingResponse(
        sandbox.mjpeg_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive"
        }
    )


@app.get(
    "/api/session-state",
    response_model=SessionState,
    summary="Retrieve Active Session State"
)
async def get_session_state_endpoint():
    """
    Returns complete session state snapshot, step budget utilization,
    audit history, and completion status.
    """
    state_mgr = get_state_manager()
    state_dict = state_mgr.get_session_state()

    return SessionState(
        session_id=state_dict.get("session_id", ""),
        active=state_dict.get("active", False),
        step=state_dict.get("step", 0),
        max_steps=state_dict.get("max_steps", MAX_STEPS),
        task=state_dict.get("task", ""),
        language=state_dict.get("language", DEFAULT_LANGUAGE),
        history=state_dict.get("history", []),
        last_action=state_dict.get("last_action"),
        url=state_dict.get("url", ""),
        stalled=state_dict.get("stalled", False),
        finished=state_dict.get("finished", False),
        state_signature=state_dict.get("state_signature", "")
    )


@app.post(
    "/api/reset",
    response_model=ResetResponse,
    summary="Reset Session & Ephemeral Data Purge"
)
async def reset_session():
    """
    Terminates browser sandbox session and purges all ephemeral memory
    and citizen interaction history in compliance with the DPDP Act 2023.
    """
    global _sandbox, _odav_engine
    sandbox = get_sandbox()
    state_mgr = get_state_manager()

    # 1. Close browser sandbox cleanly
    try:
        if sandbox.is_running:
            await sandbox.close()
    except Exception as e:
        logger.warning(f"[APP] Error closing sandbox on reset: {e}")

    # Nullify singletons to guarantee fresh session
    _sandbox = None
    _odav_engine = None

    # 2. Ephemeral data purge (DPDP Act compliance)
    state_mgr.purge_ephemeral_data()

    logger.info("[APP] System reset complete. Ephemeral memory wiped.")

    return ResetResponse(
        status="reset",
        purged=True
    )


@app.get("/api/health", summary="Health Check")
async def health_check():
    """Returns application health and subsystem statuses."""
    sandbox = get_sandbox()
    state_mgr = get_state_manager()
    return {
        "status": "healthy",
        "service": "SEVA AI Kiosk Platform",
        "version": "1.0.0",
        "sandbox_running": sandbox.is_running,
        "session_active": state_mgr.active,
        "current_step": state_mgr.step,
        "max_steps": state_mgr.max_steps
    }


# --- Static Mounts for Frontend & Mock Portals ---

# Mount Mock Portals Directory if present
if MOCK_PORTALS_DIR.exists():
    app.mount("/portal", StaticFiles(directory=str(MOCK_PORTALS_DIR), html=True), name="portals")
    app.mount("/mock_portals", StaticFiles(directory=str(MOCK_PORTALS_DIR), html=True), name="mock_portals")

# Mount Frontend Assets Directory if present
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    # If frontend/index.html exists, serve as root
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        @app.get("/", response_class=HTMLResponse)
        async def serve_index():
            return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    else:
        @app.get("/", response_class=HTMLResponse)
        async def serve_fallback_root():
            return HTMLResponse(
                content="""<!DOCTYPE html>
<html>
<head><title>SEVA AI Kiosk</title></head>
<body style="font-family:sans-serif;padding:40px;background:#0f172a;color:#fff;">
  <h1>🏛️ SEVA AI Kiosk Platform</h1>
  <p>Status: Backend Online | API Ready</p>
  <p>Access REST API at <a href="/docs" style="color:#38bdf8;">/docs</a></p>
</body>
</html>"""
            )
else:
    @app.get("/", response_class=HTMLResponse)
    async def serve_fallback_root():
        return HTMLResponse(
            content="""<!DOCTYPE html>
<html>
<head><title>SEVA AI Kiosk</title></head>
<body style="font-family:sans-serif;padding:40px;background:#0f172a;color:#fff;">
  <h1>🏛️ SEVA AI Kiosk Platform</h1>
  <p>Status: Backend Online | API Ready</p>
  <p>Access REST API at <a href="/docs" style="color:#38bdf8;">/docs</a></p>
</body>
</html>"""
        )
