"""
vdak-host/main.py  — Complete rewrite with multi-language support
V-DAK Host Orchestrator.
Gracefully handles missing VM (demo/offline mode).
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bridge.ws_client import VMBridge
from config.languages import get_prompt, get_language, DEFAULT_LANGUAGE
from state_machine import KioskStateMachine
from vision.camera import CameraCapture
from vision.ocr import OCREngine
from voice.asr import ASREngine
from voice.tts import TTSEngine

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vdak.host")

# ─────────────────────────────────────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────────────────────────────────────
VM_WS_URL    = os.getenv("VM_WS_URL", "ws://192.168.31.100:8765")
DEMO_MODE    = os.getenv("DEMO_MODE", "false").lower() == "true"

# ─────────────────────────────────────────────────────────────────────────────
#  Singletons
# ─────────────────────────────────────────────────────────────────────────────
asr        = ASREngine()
tts        = TTSEngine()
ocr        = OCREngine()
camera     = CameraCapture()
sm         = KioskStateMachine()
vm_bridge  = VMBridge(VM_WS_URL)

# Session state
_session: dict = {"language": DEFAULT_LANGUAGE, "fields": {}, "active": False}
ui_clients: list[WebSocket] = []

# ─────────────────────────────────────────────────────────────────────────────
#  UI Broadcasting
# ─────────────────────────────────────────────────────────────────────────────

async def push_ui(event: str, data: dict = {}):
    payload = json.dumps({"event": event, **data})
    dead = []
    for ws in ui_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for d in dead:
        ui_clients.remove(d)

# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def say(key: str):
    """Speak a prompt in the current session language."""
    lang = _session["language"]
    text = get_prompt(lang, key)
    tts.speak(text, lang)
    return text

async def say_push(key: str, event: str, extra: dict = {}):
    """Speak + push to UI simultaneously."""
    text = say(key)
    await push_ui(event, {"message": text, **extra})

# ─────────────────────────────────────────────────────────────────────────────
#  VM Event Handlers
# ─────────────────────────────────────────────────────────────────────────────

async def on_checkpoint():
    sm.checkpoint_hit()
    await say_push("otp_prompt", "HUMAN_CHECKPOINT")
    logger.info("[HOST] OTP checkpoint — citizen control.")

async def on_done(result: str):
    sm.submission_done()
    await say_push("done", "DONE", {"result": result})
    logger.info(f"[HOST] Done: {result}")
    await _purge()

async def on_error(detail: str):
    sm.error_occurred()
    await say_push("error", "ERROR", {"detail": detail})
    logger.error(f"[HOST] VM error: {detail}")

async def _purge():
    logger.info("[HOST] Purging session data.")
    _session["fields"] = {}
    _session["active"] = False
    sm.session_purged()
    await push_ui("IDLE", {"message": "Kiosk ready."})

# ─────────────────────────────────────────────────────────────────────────────
#  Demo Session (no hardware / no VM required)
# ─────────────────────────────────────────────────────────────────────────────

DEMO_FIELDS = {
    "name":         "Shantabai Patil",
    "dob":          "12/03/1968",
    "gender":       "Female",
    "aadhaar_last4": "7892",
}

async def run_demo_session():
    """Simulates the full kiosk flow with fake data. No hardware needed."""
    logger.info("[DEMO] Starting demo session.")
    lang = _session["language"]

    sm.citizen_detected()
    await say_push("greeting", "INTENT_DISCOVERY")
    await asyncio.sleep(2)

    await push_ui("INTENT_CAPTURED", {
        "text": get_prompt(lang, "scan_doc"),
        "message": "Citizen intent understood: Niradhar Pension Application",
    })
    await asyncio.sleep(1.5)

    sm.intent_confirmed()
    await say_push("scan_doc", "DOCUMENT_SCANNING")
    await asyncio.sleep(2.5)

    _session["fields"] = DEMO_FIELDS
    sm.docs_verified()
    await push_ui("OCR_DONE", {"fields": DEMO_FIELDS})
    await asyncio.sleep(1)

    await say_push("filling", "PORTAL_AUTOMATION", {"fields": DEMO_FIELDS})
    await asyncio.sleep(3)

    # Simulate OTP checkpoint
    sm.checkpoint_hit()
    await say_push("otp_prompt", "HUMAN_CHECKPOINT")
    logger.info("[DEMO] OTP checkpoint — waiting 8 seconds to simulate citizen.")
    await asyncio.sleep(8)

    # Auto-resume in demo
    if sm.is_waiting_for_otp():
        sm.otp_submitted()
    await push_ui("PORTAL_AUTOMATION", {"message": "OTP accepted. Submitting..."})
    await asyncio.sleep(2)

    sm.submission_done()
    await say_push("done", "DONE", {"result": "Application ID: MH2026-NGS-4872931"})
    await asyncio.sleep(2)
    await _purge()
    logger.info("[DEMO] Demo session complete.")

# ─────────────────────────────────────────────────────────────────────────────
#  Real Session (ASR + OCR + VM)
# ─────────────────────────────────────────────────────────────────────────────

async def run_real_session():
    lang = _session["language"]

    sm.citizen_detected()
    await say_push("greeting", "INTENT_DISCOVERY")

    # ASR — listen for citizen intent
    try:
        intent_text = await asyncio.to_thread(
            asr.listen_and_transcribe,
            lang_code=lang,
            duration=5.0,
        )
    except Exception as e:
        logger.error(f"[HOST] ASR failed: {e}")
        intent_text = "(voice input unavailable)"

    await push_ui("INTENT_CAPTURED", {"text": intent_text})

    # Document scan
    sm.intent_confirmed()
    await say_push("scan_doc", "DOCUMENT_SCANNING")

    try:
        frame = await asyncio.to_thread(_capture_document)
    except Exception as e:
        logger.error(f"[HOST] Camera failed: {e}")
        frame = None

    if frame is None:
        await say_push("error", "ERROR")
        sm.error_occurred()
        return

    # OCR
    try:
        extracted = await asyncio.to_thread(ocr.extract, frame, lang)
        await asyncio.to_thread(ocr.unload, lang)
    except Exception as e:
        logger.error(f"[HOST] OCR failed: {e}")
        extracted = {"fields": {}}

    fields = extracted["fields"]
    _session["fields"] = fields
    sm.docs_verified()
    await push_ui("OCR_DONE", {"fields": fields})
    await say_push("confirm", "PORTAL_AUTOMATION")

    # Build task for VM
    task = (
        f"Navigate to mahaonline.gov.in and apply for Sanjay Gandhi Niradhar "
        f"Anudan Yojana. Fill: Name={fields.get('name','')}, "
        f"DOB={fields.get('dob','')}, Gender={fields.get('gender','Female')}. "
        f"Stop and do NOT type anything into OTP, password, or PIN fields."
    )

    await say_push("filling", "PORTAL_AUTOMATION", {"task": task})
    vm_bridge.set_handlers(on_checkpoint, on_done, on_error)

    try:
        await vm_bridge.send_task(task)
        await vm_bridge.listen()
    except Exception as e:
        logger.error(f"[HOST] VM communication failed: {e}")
        await say_push("error", "ERROR", {"detail": str(e)})
        sm.error_occurred()

def _capture_document():
    with camera:
        return camera.capture_document()

# ─────────────────────────────────────────────────────────────────────────────
#  FastAPI App
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DEMO_MODE:
        try:
            await vm_bridge.connect()
            logger.info("[HOST] Connected to VM browser agent.")
        except Exception as e:
            logger.warning(f"[HOST] VM not reachable ({e}). Running in demo mode.")
    yield
    try:
        await vm_bridge.close()
    except Exception:
        pass

app = FastAPI(title="V-DAK Host Orchestrator", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SessionStartRequest(BaseModel):
    language: str = DEFAULT_LANGUAGE
    demo: bool = False


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "state":  sm.current,
        "demo_mode": DEMO_MODE,
        "supported_languages": list(get_language("mr").keys()),
    }


@app.get("/languages")
async def list_languages():
    from config.languages import SUPPORTED_LANGUAGES
    return {
        code: {"name": v["name"], "native_name": v["native_name"]}
        for code, v in SUPPORTED_LANGUAGES.items()
    }


@app.post("/session/start")
async def start_session(req: SessionStartRequest):
    if not sm.is_idle():
        return {"error": "Session already in progress", "state": sm.current}
    _session["language"] = req.language
    _session["active"]   = True
    use_demo = req.demo or DEMO_MODE
    logger.info(f"[HOST] Starting {'DEMO' if use_demo else 'REAL'} session | lang={req.language}")
    asyncio.create_task(run_demo_session() if use_demo else run_real_session())
    return {"status": "started", "language": req.language, "mode": "demo" if use_demo else "real"}


@app.post("/session/otp-submitted")
async def otp_submitted():
    if not sm.is_waiting_for_otp():
        return {"error": "Not in OTP checkpoint state", "state": sm.current}
    sm.otp_submitted()
    if not DEMO_MODE:
        await vm_bridge.send_resume()
    await push_ui("PORTAL_AUTOMATION", {"message": "OTP accepted — resuming..."})
    return {"status": "resumed"}


@app.post("/session/cancel")
async def cancel_session():
    sm.user_cancelled()
    await _purge()
    return {"status": "cancelled"}


@app.get("/session/state")
async def get_state():
    return {
        "state":    sm.current,
        "language": _session["language"],
        "fields":   _session["fields"],
        "active":   _session["active"],
    }


@app.websocket("/ws/ui")
async def ui_websocket(websocket: WebSocket):
    await websocket.accept()
    ui_clients.append(websocket)
    try:
        # Send current state immediately on connect
        await websocket.send_text(json.dumps({
            "event":    "CONNECTED",
            "state":    sm.current,
            "language": _session["language"],
            "fields":   _session["fields"],
        }))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in ui_clients:
            ui_clients.remove(websocket)
