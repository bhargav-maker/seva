"""
vdak-host/app.py
FastAPI Host Application & REST API for SEVA AI Kiosk Platform.
Exposes the ODAV loop control endpoints and CDP screencast stream.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sys
from pathlib import Path

# Ensure paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from bridge.vm_client import VMClient
from bridge.state_manager import StateManager
from voice.tts import TTSEngine

try:
    from vdak_vm.browser_controller import BrowserController
    from vdak_vm.agent_loop import ODAVAgentLoop
except ImportError:
    import importlib.util
    # Dynamic import for hyphenated folder vdak-vm
    vm_dir = Path(__file__).parent.parent / "vdak-vm"
    bc_spec = importlib.util.spec_from_file_location("browser_controller", str(vm_dir / "browser_controller.py"))
    bc_mod = importlib.util.module_from_spec(bc_spec)
    bc_spec.loader.exec_module(bc_mod)
    BrowserController = bc_mod.BrowserController

    al_spec = importlib.util.spec_from_file_location("agent_loop", str(vm_dir / "agent_loop.py"))
    al_mod = importlib.util.module_from_spec(al_spec)
    al_spec.loader.exec_module(al_mod)
    ODAVAgentLoop = al_mod.ODAVAgentLoop

logger = logging.getLogger("vdak.host.app")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SEVA AI Kiosk Controller", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global runtime singletons
state_manager = StateManager(max_steps=settings.MAX_STEP_BUDGET, k_window=settings.CONTEXT_WINDOW_SIZE)
vm_client = VMClient(api_key=settings.OPENROUTER_API_KEY, model=settings.OPENROUTER_MODEL)
browser_controller = BrowserController(headless=True)
tts_engine = TTSEngine()
agent_loop = ODAVAgentLoop(
    browser_controller=browser_controller,
    vm_client=vm_client,
    state_manager=state_manager,
    tts_callback=lambda text, lang: tts_engine.speak(text, lang)
)

# Pydantic Schemas
class StartTaskRequest(BaseModel):
    task: str
    language: str = "mr"

class ActionDecision(BaseModel):
    thought: str
    intent: str
    action: str
    selector: str
    value: str
    feedback: str

@app.on_event("startup")
async def startup_event():
    logger.info("[App] Initializing SEVA AI runtime...")
    await browser_controller.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("[App] Shutting down SEVA AI runtime...")
    await browser_controller.close()

# ----------------- REST Endpoints -----------------

@app.post("/api/start-task")
async def start_task(req: StartTaskRequest):
    """Initializes a new citizen session and resets ODAV loop guards."""
    session_id = str(uuid.uuid4())[:8]
    state_manager.start_session(session_id=session_id, goal=req.task, language=req.language)

    # Initial spoken confirmation
    welcome_mr = "नमस्कार, आपला अर्ज सुरू करत आहे."
    welcome_hi = "नमस्ते, आपका आवेदन शुरू किया जा रहा है."
    tts_engine.speak(welcome_mr if req.language == "mr" else welcome_hi, req.language)

    return {
        "status": "started",
        "session_id": session_id,
        "step": 0,
        "max_steps": settings.MAX_STEP_BUDGET,
        "task": req.task,
        "language": req.language
    }

@app.post("/api/step")
async def execute_step():
    """Executes a single discrete ODAV iteration."""
    if not state_manager.active_session_id:
        raise HTTPException(status_code=400, detail="No active session. Call /api/start-task first.")

    if state_manager.is_finished:
        return {"status": "finished", "step": state_manager.current_step, "detail": "Task already completed"}

    if state_manager.is_budget_exhausted:
        return {"status": "budget_exhausted", "step": state_manager.current_step, "detail": "Step budget ceiling reached"}

    step_result = await agent_loop.run_single_step()
    return step_result

@app.get("/api/stream")
async def stream_mjpeg():
    """Streams live CDP screencast frames over multipart HTTP at ~25 FPS."""
    return StreamingResponse(
        browser_controller.mjpeg_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/session-state")
async def get_session_state():
    """Returns current ODAV session state, budget remaining, and stall status."""
    compact = state_manager.get_compacted_context()
    return {
        "active": state_manager.active_session_id is not None,
        "session_id": state_manager.active_session_id,
        "step": state_manager.current_step,
        "max_steps": state_manager.max_steps,
        "task": state_manager.citizen_goal,
        "language": state_manager.language,
        "recent_history": compact["recent_actions"],
        "last_signature": state_manager.last_signature,
        "stalled": state_manager.is_stalled,
        "finished": state_manager.is_finished,
        "budget_exhausted": state_manager.is_budget_exhausted
    }

@app.post("/api/reset")
async def reset_session():
    """Performs immediate ephemeral data purge complying with DPDP Act 2023."""
    state_manager.reset()
    # Navigate browser to blank page to purge cookies/DOM
    if browser_controller._page:
        try:
            await browser_controller._page.goto("about:blank")
        except Exception:
            pass
    return {"status": "reset", "purged": True}

# Static Mounts
frontend_dir = Path(__file__).parent / "frontend"
mock_portals_dir = Path(__file__).parent.parent / "mock_portals"

if mock_portals_dir.exists():
    app.mount("/mock_portals", StaticFiles(directory=str(mock_portals_dir)), name="mock_portals")

if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_index():
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>SEVA AI Kiosk Ready</h1>")
