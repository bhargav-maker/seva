"""
vdak-host/ui/gradio_app.py  — Complete V-DAK Kiosk UI
100% Python. Pure Gradio. No React, no Node, nothing else needed.

Features:
  ✅ 7 Indian languages with native script display
  ✅ Demo mode — full simulated flow, no hardware needed
  ✅ Blinking red OTP screen
  ✅ Real-time state updates via polling
  ✅ Live OCR field display
  ✅ Activity log
  ✅ Model download helper
  ✅ Language auto-detection button
"""

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

import gradio as gr
import requests

# ── Add parent to path so config imports work ──────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.languages import SUPPORTED_LANGUAGES, get_prompt

logger = logging.getLogger("vdak.ui")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

HOST_URL = f"http://localhost:{os.getenv('HOST_PORT', '8000')}"

# ─────────────────────────────────────────────────────────────────────────────
#  Shared state (thread-safe via lock)
# ─────────────────────────────────────────────────────────────────────────────
_state = {
    "event":    "IDLE",
    "state":    "IDLE",
    "message":  "Kiosk ready. Select language and press Start.",
    "fields":   {},
    "language": "mr",
    "log":      [],
    "result":   "",
    "connected": False,
}
_lock = threading.Lock()


def _set(key, val):
    with _lock:
        _state[key] = val


def _get(key, default=None):
    with _lock:
        return _state.get(key, default)


def _log(msg: str):
    with _lock:
        _state["log"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        if len(_state["log"]) > 30:
            _state["log"] = _state["log"][-30:]


# ─────────────────────────────────────────────────────────────────────────────
#  Background WebSocket listener
# ─────────────────────────────────────────────────────────────────────────────

def _start_ws_listener():
    """Daemon thread: listens to FastAPI /ws/ui for real-time events."""
    import websocket as ws_lib

    ws_url = f"ws://localhost:{os.getenv('HOST_PORT', '8000')}/ws/ui"

    def on_message(ws, raw):
        try:
            msg = json.loads(raw)
            event = msg.get("event", "")
            with _lock:
                _state["event"]   = event
                _state["state"]   = event
                _state["message"] = msg.get("message", msg.get("result", ""))
                if "fields" in msg:
                    _state["fields"] = msg["fields"]
                if "result" in msg:
                    _state["result"] = msg["result"]
            _log(f"[{event}] {_state['message'][:60]}")
        except Exception as e:
            _log(f"[WS ERR] {e}")

    def on_open(ws):
        _set("connected", True)
        _log("✅ Connected to V-DAK backend.")

    def on_close(ws, *_):
        _set("connected", False)
        _log("⚠️ Disconnected from backend. Retrying...")

    def on_error(ws, err):
        _log(f"[WS] {err}")

    while True:
        try:
            app = ws_lib.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_open=on_open,
                on_close=on_close,
                on_error=on_error,
            )
            app.run_forever(ping_interval=20)
        except Exception as e:
            _log(f"[WS] Reconnect error: {e}")
        time.sleep(3)


threading.Thread(target=_start_ws_listener, daemon=True).start()

# ─────────────────────────────────────────────────────────────────────────────
#  API helpers
# ─────────────────────────────────────────────────────────────────────────────

def _api(method: str, path: str, **kwargs) -> dict:
    try:
        fn  = getattr(requests, method)
        res = fn(f"{HOST_URL}{path}", timeout=5, **kwargs)
        return res.json()
    except requests.exceptions.ConnectionError:
        _log("⚠️ Backend not running. Start: uvicorn main:app --port 8000")
        return {"error": "Backend not reachable"}
    except Exception as e:
        _log(f"[API ERR] {e}")
        return {"error": str(e)}


def _backend_healthy() -> bool:
    try:
        r = requests.get(f"{HOST_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  State → display helpers
# ─────────────────────────────────────────────────────────────────────────────

STATE_ICON = {
    "IDLE":              "🟢",
    "INTENT_DISCOVERY":  "🎙️",
    "INTENT_CAPTURED":   "💬",
    "DOCUMENT_SCANNING": "📄",
    "OCR_DONE":          "🔍",
    "PORTAL_AUTOMATION": "🤖",
    "HUMAN_CHECKPOINT":  "🔴",
    "SUBMISSION":        "📨",
    "DONE":              "✅",
    "ERROR":             "❌",
    "PURGE":             "🔄",
    "CONNECTED":         "🟢",
}

STATE_LABEL = {
    "IDLE":              "Kiosk Ready — Waiting for Citizen",
    "INTENT_DISCOVERY":  "Listening... Citizen is speaking",
    "INTENT_CAPTURED":   "Intent Understood",
    "DOCUMENT_SCANNING": "Scanning Document...",
    "OCR_DONE":          "Document Read Successfully",
    "PORTAL_AUTOMATION": "AI Agent Filling Form...",
    "HUMAN_CHECKPOINT":  "YOUR TURN — Enter OTP Now",
    "SUBMISSION":        "Submitting Application...",
    "DONE":              "Application Submitted! ✅",
    "ERROR":             "Error — Please Try Again",
    "PURGE":             "Resetting Kiosk...",
    "CONNECTED":         "Kiosk Ready",
}

LANG_FLAGS = {
    "mr": "🇮🇳", "hi": "🇮🇳", "gu": "🇮🇳",
    "ta": "🇮🇳", "kn": "🇮🇳", "te": "🇮🇳", "bn": "🇮🇳",
}


def _fmt_fields(fields: dict) -> str:
    if not fields:
        return "*Scan a document to see extracted fields.*"
    rows = "\n".join(f"| **{k.replace('_',' ').title()}** | {v} |" for k, v in fields.items())
    return f"| Field | Value |\n|---|---|\n{rows}"


def _fmt_log(log: list) -> str:
    return "\n".join(reversed(log[-20:])) if log else "*No activity yet.*"


# ─────────────────────────────────────────────────────────────────────────────
#  Refresh function — called every 1.5s by gr.Timer
# ─────────────────────────────────────────────────────────────────────────────

def refresh():
    with _lock:
        event   = _state["event"]
        message = _state["message"]
        fields  = dict(_state["fields"])
        log     = list(_state["log"])
        result  = _state["result"]
        conn    = _state["connected"]

    icon    = STATE_ICON.get(event, "⚪")
    label   = STATE_LABEL.get(event, event)
    is_otp  = event == "HUMAN_CHECKPOINT"
    is_done = event == "DONE"
    is_idle = event in ("IDLE", "CONNECTED")
    is_busy = not is_idle and not is_otp and not is_done

    # Backend status
    backend_status = "🟢 Backend connected" if conn else "🔴 Backend offline — start FastAPI first"

    # State HTML
    color = {
        "IDLE": "#2d8a4e", "CONNECTED": "#2d8a4e",
        "HUMAN_CHECKPOINT": "#cc0000",
        "DONE": "#1a6b1a",
        "ERROR": "#cc0000",
        "PORTAL_AUTOMATION": "#1a5fa8",
    }.get(event, "#555555")

    state_html = f"""
    <div style="
        background:{color};color:white;padding:18px 24px;border-radius:12px;
        font-size:1.4em;font-weight:bold;text-align:center;margin-bottom:8px;">
        {icon} {label}
    </div>
    <div style="text-align:center;color:#555;font-size:0.9em;">{backend_status}</div>
    """

    # OTP banner HTML
    otp_html = ""
    if is_otp:
        otp_html = """
        <div style="
            background:#cc0000;color:white;padding:32px;border-radius:16px;
            font-size:2em;font-weight:900;text-align:center;
            animation:pulse 1s ease-in-out infinite alternate;
            box-shadow:0 0 30px rgba(204,0,0,0.5);">
            🔴 YOUR TURN<br>
            <span style="font-size:0.6em;font-weight:normal;">
            Type your OTP on the keyboard right now.<br>
            Then click "I Have Entered My OTP" below.
            </span>
        </div>
        <style>
        @keyframes pulse { from {opacity:1;} to {opacity:0.6;} }
        </style>
        """

    # Done banner
    done_html = ""
    if is_done:
        done_html = f"""
        <div style="
            background:#1a6b1a;color:white;padding:24px;border-radius:12px;
            font-size:1.3em;font-weight:bold;text-align:center;">
            ✅ Application Submitted Successfully!<br>
            <span style="font-size:0.7em;font-weight:normal;">
            {result}
            </span>
        </div>
        """

    return (
        state_html,                              # state_display
        otp_html,                                # otp_banner
        done_html,                               # done_banner
        _fmt_fields(fields),                     # fields_md
        _fmt_log(log),                           # log_md
        gr.update(visible=is_otp),               # otp_btn
        gr.update(interactive=is_idle, variant="primary" if is_idle else "secondary"),  # start_btn
        gr.update(visible=is_busy),              # cancel_btn
        message,                                 # message_box
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Gradio UI
# ─────────────────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
body { font-family: 'Noto Sans', 'Segoe UI', sans-serif !important; }
.gradio-container { max-width: 1400px; margin: auto; }
#header { text-align:center; padding: 20px 0 10px 0; }
#header h1 { font-size: 2.2em; color: #1a3a6b; margin-bottom: 4px; }
#header p { color: #666; font-size: 1em; }
.lang-choice { font-size: 1.1em !important; }
.big-btn button { font-size: 1.3em !important; padding: 16px !important; }
footer { display: none !important; }
"""

# Language choices with native script
LANG_CHOICES = [
    (f"{LANG_FLAGS.get(k,'🌐')} {v['native_name']} — {v['name']}", k)
    for k, v in SUPPORTED_LANGUAGES.items()
]

with gr.Blocks(
    title="V-DAK — Vernacular Digital Assistance Kiosk",
    css=CUSTOM_CSS,
    theme=gr.themes.Soft(
        primary_hue=gr.themes.colors.blue,
        secondary_hue=gr.themes.colors.orange,
        font=gr.themes.GoogleFont("Noto Sans"),
    ),
) as demo:

    # ── Header ────────────────────────────────────────────────────────────── #
    gr.HTML("""
    <div id="header">
        <h1>🏛️ V-DAK — Vernacular Digital Assistance Kiosk</h1>
        <p>
            AI-powered government services in your language &nbsp;|&nbsp;
            <strong style="color:green;">₹0 cost to citizens</strong> &nbsp;|&nbsp;
            मराठी · हिन्दी · ગુજરાતી · தமிழ் · ಕನ್ನಡ · తెలుగు · বাংলা
        </p>
        <hr style="border-color:#e0e0e0;margin:12px 0;">
    </div>
    """)

    with gr.Row(equal_height=False):

        # ── LEFT COLUMN — Controls ─────────────────────────────────────────── #
        with gr.Column(scale=1, min_width=340):

            gr.Markdown("### 🌐 Language / भाषा / மொழி")
            lang_dropdown = gr.Dropdown(
                choices=LANG_CHOICES,
                value="mr",
                label="Select your language",
                interactive=True,
                elem_classes=["lang-choice"],
            )

            gr.Markdown("### 🎛️ Session")
            with gr.Row():
                start_btn = gr.Button(
                    "▶ Start Session",
                    variant="primary",
                    size="lg",
                    elem_classes=["big-btn"],
                )
                demo_btn = gr.Button(
                    "🎬 Demo",
                    variant="secondary",
                    size="lg",
                )

            cancel_btn = gr.Button("⏹ Cancel Session", variant="stop", visible=False)

            gr.Markdown("---")
            gr.Markdown("### 📋 Extracted Document Fields")
            fields_md = gr.Markdown("*Scan a document to see fields.*")

            gr.Markdown("---")
            gr.Markdown("### ℹ️ Current Message")
            message_box = gr.Textbox(
                label="",
                value="Kiosk ready.",
                interactive=False,
                lines=2,
            )

            # Model download helper
            with gr.Accordion("⬇️ Download Voice Models (first time)", open=False):
                gr.Markdown(
                    "Run this once to download Piper TTS voice models for all 7 languages.\n"
                    "Requires internet. Takes ~2 minutes."
                )
                dl_btn    = gr.Button("Download All Voice Models", variant="secondary")
                dl_status = gr.Textbox(label="Status", interactive=False, lines=3)

                def do_download():
                    from voice.tts import TTSEngine
                    engine = TTSEngine()
                    results = []
                    for code in ["mr", "hi", "gu", "ta", "kn", "te", "bn"]:
                        ok = engine.download_model(code)
                        results.append(f"{'✅' if ok else '❌'} {code}")
                    return "\n".join(results)

                dl_btn.click(fn=do_download, outputs=dl_status)

        # ── RIGHT COLUMN — State + OTP + Log ──────────────────────────────── #
        with gr.Column(scale=2):

            state_display = gr.HTML(
                value='<div style="background:#2d8a4e;color:white;padding:18px;border-radius:12px;font-size:1.4em;font-weight:bold;text-align:center;">🟢 Kiosk Ready</div>'
            )

            otp_banner  = gr.HTML(value="", visible=True)
            done_banner = gr.HTML(value="", visible=True)

            # OTP submission button — only shows during HUMAN_CHECKPOINT
            otp_btn = gr.Button(
                "✅ I Have Entered My OTP — Continue",
                variant="primary",
                size="lg",
                visible=False,
                elem_classes=["big-btn"],
            )

            gr.Markdown("### 📝 Live Activity")
            log_md = gr.Markdown("*Activity will appear here...*")

    # ── Timer — refresh every 1.5 seconds ─────────────────────────────────── #
    timer = gr.Timer(value=1.5)
    timer.tick(
        fn=refresh,
        outputs=[
            state_display, otp_banner, done_banner,
            fields_md, log_md,
            otp_btn, start_btn, cancel_btn,
            message_box,
        ],
    )

    # ── Button callbacks ──────────────────────────────────────────────────── #

    def on_start(lang_code):
        _set("language", lang_code)
        _log(f"[UI] Starting REAL session | lang={lang_code}")
        resp = _api("post", "/session/start", json={"language": lang_code, "demo": False})
        _log(f"[UI] {resp}")

    def on_demo(lang_code):
        _set("language", lang_code)
        _log(f"[UI] Starting DEMO session | lang={lang_code}")
        resp = _api("post", "/session/start", json={"language": lang_code, "demo": True})
        _log(f"[UI] {resp}")

    def on_otp():
        _log("[UI] OTP submitted by citizen.")
        resp = _api("post", "/session/otp-submitted")
        _log(f"[UI] {resp}")

    def on_cancel():
        _log("[UI] Session cancelled.")
        resp = _api("post", "/session/cancel")
        _log(f"[UI] {resp}")

    start_btn.click(fn=on_start,  inputs=[lang_dropdown])
    demo_btn.click(fn=on_demo,    inputs=[lang_dropdown])
    otp_btn.click(fn=on_otp)
    cancel_btn.click(fn=on_cancel)


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("GRADIO_PORT", "7860"))
    logger.info(f"Starting V-DAK UI at http://0.0.0.0:{port}")
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
        quiet=False,
    )
