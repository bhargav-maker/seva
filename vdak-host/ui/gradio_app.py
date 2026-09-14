"""
vdak-host/ui/gradio_app.py — SEVA AI Kiosk UI (Production)
Complete overhaul:
  ✅ SEVA AI branding
  ✅ Solar / battery status badge
  ✅ Live browser viewport stream (Base64 JPEG → gr.Image)
  ✅ OTP blinking banner
  ✅ Official receipt display
  ✅ NO_PROXY env fix
  ✅ All 7 languages with native script
"""

import base64
import io
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

import gradio as gr
import requests
from PIL import Image

# ── Fix: loopback proxy bypass ────────────────────────────────────────────────
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.languages import SUPPORTED_LANGUAGES, get_prompt

logger = logging.getLogger("vdak.ui")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

HOST_URL = f"http://127.0.0.1:{os.getenv('HOST_PORT', '8000')}"
WS_URL   = f"ws://127.0.0.1:{os.getenv('HOST_PORT', '8000')}/ws/ui"

# ─────────────────────────────────────────────────────────────────────────────
#  Shared State
# ─────────────────────────────────────────────────────────────────────────────
_state = {
    "event":          "IDLE",
    "message":        "SEVA AI ready. Select language and start.",
    "fields":         {},
    "receipt":        None,
    "browser_frame":  None,   # PIL Image or None
    "log":            [],
    "language":       "mr",
    "connected":      False,
}
_lock = threading.Lock()


def _set(k, v):
    with _lock:
        _state[k] = v

def _get(k, d=None):
    with _lock:
        return _state.get(k, d)

def _log(msg):
    ts = time.strftime("%H:%M:%S")
    with _lock:
        _state["log"].append(f"[{ts}] {msg}")
        if len(_state["log"]) > 40:
            _state["log"] = _state["log"][-40:]


# ─────────────────────────────────────────────────────────────────────────────
#  WebSocket Listener (background daemon thread)
# ─────────────────────────────────────────────────────────────────────────────

def _ws_listener():
    import websocket as wsl

    def on_message(ws, raw):
        try:
            msg   = json.loads(raw)
            event = msg.get("event", "")
            with _lock:
                _state["event"]   = event
                _state["message"] = msg.get("message", msg.get("result", _state["message"]))
                if "fields" in msg and msg["fields"]:
                    _state["fields"] = msg["fields"]
                if "receipt" in msg and msg["receipt"]:
                    _state["receipt"] = msg["receipt"]

                # Decode live browser frame
                if event == "BROWSER_FRAME" and "data" in msg:
                    try:
                        img_bytes = base64.b64decode(msg["data"])
                        _state["browser_frame"] = Image.open(io.BytesIO(img_bytes))
                    except Exception:
                        pass
                elif event in ("IDLE", "PURGE"):
                    _state["browser_frame"] = None
                    _state["fields"]        = {}
                    _state["receipt"]       = None

            if event != "BROWSER_FRAME":
                _log(f"[{event}] {_state['message'][:60]}")
        except Exception as e:
            _log(f"[WS ERR] {e}")

    def on_open(ws):
        _set("connected", True)
        _log("✅ Connected to SEVA AI backend.")

    def on_close(ws, *_):
        _set("connected", False)
        _log("⚠️  Backend offline. Start FastAPI then refresh.")

    def on_error(ws, e):
        _log(f"[WS] {e}")

    while True:
        try:
            app = wsl.WebSocketApp(
                WS_URL,
                on_message=on_message, on_open=on_open,
                on_close=on_close,     on_error=on_error,
            )
            app.run_forever(ping_interval=20)
        except Exception as e:
            _log(f"[WS] Reconnect: {e}")
        time.sleep(3)

threading.Thread(target=_ws_listener, daemon=True).start()

# ─────────────────────────────────────────────────────────────────────────────
#  API Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _api(method, path, **kwargs):
    try:
        r = getattr(requests, method)(f"{HOST_URL}{path}", timeout=5, **kwargs)
        return r.json()
    except requests.exceptions.ConnectionError:
        _log("⚠️  Backend not running. Run: python run.py --demo")
        return {"error": "Backend offline"}
    except Exception as e:
        _log(f"[API] {e}")
        return {"error": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
#  Refresh (called every 1.5s by gr.Timer)
# ─────────────────────────────────────────────────────────────────────────────

STATE_COLORS = {
    "IDLE":              ("#2d8a4e", "🟢 Ready — Waiting for Citizen"),
    "CONNECTED":         ("#2d8a4e", "🟢 SEVA AI Ready"),
    "INTENT_DISCOVERY":  ("#1a5fa8", "🎙️ Listening — Citizen Speaking..."),
    "INTENT_CAPTURED":   ("#1a5fa8", "💬 Intent Understood"),
    "DOCUMENT_SCANNING": ("#7a5c00", "📄 Scanning Document..."),
    "OCR_DONE":          ("#7a5c00", "🔍 Document Read"),
    "PORTAL_AUTOMATION": ("#1a3a8f", "🤖 AI Filling Form..."),
    "HUMAN_CHECKPOINT":  ("#cc0000", "🔴 YOUR TURN — Enter OTP"),
    "SUBMISSION":        ("#1a6b1a", "📨 Submitting..."),
    "DONE":              ("#1a6b1a", "✅ Application Submitted!"),
    "ERROR":             ("#cc0000", "❌ Error — Try Again"),
    "PURGE":             ("#555",    "🔄 Resetting Kiosk..."),
}

BLANK_FRAME = Image.new("RGB", (960, 540), color=(20, 20, 30))

def _receipt_md(receipt: dict) -> str:
    if not receipt:
        return ""
    rows = "\n".join(f"| **{k.replace('_',' ').title()}** | {v} |" for k, v in receipt.items())
    return f"""
---
## 🏛️ SEVA AI — Official Application Receipt

| Field | Details |
|---|---|
{rows}

*This receipt confirms your application has been submitted. Please keep the Application ID safe.*
"""

def _fields_md(fields: dict) -> str:
    if not fields:
        return "*No document scanned yet.*"
    rows = "\n".join(f"| **{k.replace('_',' ').title()}** | {v} |" for k, v in fields.items())
    return f"| Field | Value |\n|---|---|\n{rows}"

def refresh():
    with _lock:
        event   = _state["event"]
        message = _state["message"]
        fields  = dict(_state["fields"])
        receipt = dict(_state["receipt"]) if _state["receipt"] else None
        frame   = _state["browser_frame"]
        log     = list(_state["log"])
        conn    = _state["connected"]

    color, label = STATE_COLORS.get(event, ("#555", f"⚪ {event}"))
    is_otp   = event == "HUMAN_CHECKPOINT"
    is_done  = event == "DONE"
    is_idle  = event in ("IDLE", "CONNECTED", "PURGE")
    is_busy  = not is_idle and not is_otp and not is_done

    backend_dot = "🟢" if conn else "🔴"
    backend_txt = "Backend connected" if conn else "Backend offline — run: python run.py --demo"
    solar_html  = """
    <div style="display:flex;gap:12px;align-items:center;font-size:0.85em;color:#444;">
        <span>⚡ Solar Array: Active</span>
        <span style="background:#e8f5e9;color:#2d8a4e;padding:2px 8px;border-radius:8px;">Battery 96%</span>
        <span>🌐 Edge ASR/TTS: Local</span>
    </div>
    """

    state_html = f"""
    <div style="background:{color};color:white;padding:16px 24px;border-radius:12px;
                font-size:1.35em;font-weight:bold;text-align:center;margin-bottom:6px;">
        {label}
    </div>
    <div style="display:flex;justify-content:space-between;font-size:0.82em;color:#555;margin-bottom:4px;">
        <span>{backend_dot} {backend_txt}</span>
        <span>🏷️ {event}</span>
    </div>
    """

    otp_html = ""
    if is_otp:
        otp_html = """
        <style>@keyframes pulse{0%{opacity:1}50%{opacity:0.45}100%{opacity:1}}</style>
        <div style="background:#cc0000;color:white;padding:28px 20px;border-radius:16px;
                    font-size:1.8em;font-weight:900;text-align:center;
                    animation:pulse 1.2s ease-in-out infinite;
                    box-shadow:0 4px 24px rgba(204,0,0,0.45);margin:8px 0;">
            🔴 YOUR TURN<br>
            <div style="font-size:0.55em;font-weight:400;margin-top:8px;line-height:1.5;">
                Type your OTP in the browser window below.<br>
                तुमचा OTP टाइप करा · अपना OTP टाइप करें<br>
                Then click <b>I Have Entered My OTP</b>
            </div>
        </div>
        """

    done_html = _receipt_md(receipt) if (is_done and receipt) else ""

    display_frame = frame if frame is not None else BLANK_FRAME
    log_txt       = "\n".join(reversed(log[-25:])) if log else "*No activity yet.*"

    return (
        state_html,
        solar_html,
        otp_html,
        done_html,
        _fields_md(fields),
        display_frame,
        log_txt,
        message,
        gr.update(visible=is_otp),
        gr.update(interactive=is_idle, variant="primary" if is_idle else "secondary"),
        gr.update(visible=is_busy),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Gradio Layout — SEVA AI Kiosk
# ─────────────────────────────────────────────────────────────────────────────

LANG_CHOICES = [
    (f"🇮🇳 {v['native_name']} — {v['name']}", k)
    for k, v in SUPPORTED_LANGUAGES.items()
]

CSS = """
body { font-family: 'Noto Sans', 'Segoe UI', sans-serif !important; }
.gradio-container { max-width:1500px; margin:auto; }
#seva-header { text-align:center; padding:20px 0 6px; }
#seva-header h1 { font-size:2.4em; color:#1a3a6b; margin:0; }
#seva-header .tagline { color:#555; font-size:1em; margin-top:4px; }
footer { display:none !important; }
.big-btn button { font-size:1.2em !important; padding:14px !important; font-weight:600 !important; }
"""

with gr.Blocks(
    title="SEVA AI — Rural Digital Assistance Kiosk",
    css=CSS,
    theme=gr.themes.Soft(
        primary_hue=gr.themes.colors.blue,
        font=gr.themes.GoogleFont("Noto Sans"),
    ),
) as demo:

    # ── Header ────────────────────────────────────────────────────────────── #
    gr.HTML("""
    <div id="seva-header">
        <h1>🏛️ SEVA AI</h1>
        <div class="tagline">
            <strong>Solar-Powered Offline AI Form Assistant</strong> &nbsp;·&nbsp;
            Empowering rural citizens through voice-guided, typing-free public services
        </div>
        <div style="margin-top:8px;font-size:0.9em;color:#888;">
            मराठी &nbsp;·&nbsp; हिन्दी &nbsp;·&nbsp; ગુજરાતી &nbsp;·&nbsp;
            தமிழ் &nbsp;·&nbsp; ಕನ್ನಡ &nbsp;·&nbsp; తెలుగు &nbsp;·&nbsp; বাংলা
        </div>
        <hr style="border-color:#e0e0e0;margin:12px 0 4px;">
    </div>
    """)

    solar_html  = gr.HTML()
    state_html  = gr.HTML(
        value='<div style="background:#2d8a4e;color:white;padding:16px;border-radius:12px;'
              'font-size:1.35em;font-weight:bold;text-align:center;">🟢 SEVA AI Ready</div>'
    )

    with gr.Row(equal_height=False):

        # ── LEFT — Controls + Fields ──────────────────────────────────────── #
        with gr.Column(scale=1, min_width=320):

            gr.Markdown("### 🌐 Language / भाषा")
            lang_dd = gr.Dropdown(
                choices=LANG_CHOICES, value="mr",
                label="Select your language", interactive=True,
            )

            gr.Markdown("### 🎛️ Session Control")
            with gr.Row():
                start_btn = gr.Button("▶ Start", variant="primary", size="lg", elem_classes=["big-btn"])
                demo_btn  = gr.Button("🎬 Demo", variant="secondary", size="lg")
            cancel_btn = gr.Button("⏹ Cancel", variant="stop", visible=False)

            gr.Markdown("---")
            gr.Markdown("### 📋 Extracted Fields")
            fields_md = gr.Markdown("*Scan a document to see fields.*")

            gr.Markdown("---")
            gr.Markdown("### 📢 Current Prompt")
            message_box = gr.Textbox(
                label="", value="SEVA AI ready.", interactive=False, lines=2
            )

            with gr.Accordion("⬇️ Download Voice Models", open=False):
                gr.Markdown("Downloads Piper TTS for all 7 languages. ~60MB each.")
                dl_lang = gr.Dropdown(
                    choices=[(f"{v['name']} ({k})", k) for k, v in SUPPORTED_LANGUAGES.items()],
                    value="mr", label="Language to download"
                )
                dl_btn    = gr.Button("Download", variant="secondary")
                dl_status = gr.Textbox(label="Status", interactive=False, lines=2)

                def do_download(lang):
                    from voice.tts import TTSEngine
                    ok = TTSEngine().download_model(lang)
                    return f"{'✅ Downloaded' if ok else '❌ Failed (check URL or network)'} — {lang}"
                dl_btn.click(fn=do_download, inputs=[dl_lang], outputs=[dl_status])

        # ── RIGHT — Live Feed + OTP + Log ─────────────────────────────────── #
        with gr.Column(scale=2):

            gr.Markdown("### 🖥️ Live Browser Automation Feed")
            browser_img = gr.Image(
                value=BLANK_FRAME,
                label="Browser viewport — updates during automation",
                interactive=False,
                height=400,
                type="pil",
            )

            otp_banner = gr.HTML(value="")
            otp_btn    = gr.Button(
                "✅ I Have Entered My OTP — Continue",
                variant="primary", size="lg", visible=False,
                elem_classes=["big-btn"],
            )

            done_md = gr.Markdown(value="")

            gr.Markdown("### 📝 Live Activity Log")
            log_md = gr.Markdown("*Activity will appear here...*")

    # ── Timer ─────────────────────────────────────────────────────────────── #
    timer = gr.Timer(value=1.5)
    timer.tick(
        fn=refresh,
        outputs=[
            state_html, solar_html, otp_banner, done_md,
            fields_md, browser_img, log_md, message_box,
            otp_btn, start_btn, cancel_btn,
        ],
    )

    # ── Callbacks ──────────────────────────────────────────────────────────── #
    def on_start(lang):
        _set("language", lang)
        _log(f"[UI] Starting REAL session | lang={lang}")
        _api("post", "/session/start", json={"language": lang, "demo": False})

    def on_demo(lang):
        _set("language", lang)
        _log(f"[UI] Starting DEMO session | lang={lang}")
        _api("post", "/session/start", json={"language": lang, "demo": True})

    def on_otp():
        _log("[UI] OTP submitted by citizen.")
        _api("post", "/session/otp-submitted")

    def on_cancel():
        _log("[UI] Session cancelled.")
        _api("post", "/session/cancel")

    start_btn.click(fn=on_start,  inputs=[lang_dd])
    demo_btn.click(fn=on_demo,    inputs=[lang_dd])
    otp_btn.click(fn=on_otp)
    cancel_btn.click(fn=on_cancel)


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("GRADIO_PORT", "7860"))
    logger.info(f"SEVA AI UI → http://0.0.0.0:{port}")
    demo.launch(server_name="0.0.0.0", server_port=port, share=False, show_error=True)
