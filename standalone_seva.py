"""
standalone_seva.py - Single-File Complete Implementation of SEVA AI Kiosk Platform
===================================================================================
Architecture: Autonomous Observe-Decide-Act-Verify (ODAV) Browser Engine
Components Included:
  1. System Configuration & Loop Invariants (N=8 budget ceiling, k=3 context compaction)
  2. Strict 6-Key JSON Schema Validator (thought, intent, action, selector, value, feedback)
  3. Cloud LLM Bridge (OpenRouter Qwen 2.5 7B) + Heuristic Fallback Engine
  4. ODAV State Manager (S(t) SHA256 Signature, 2-Step Stall Detector, Ephemeral Purge)
  5. Playwright Chromium Sandbox & Native CDP Screencaster (>=20 FPS MJPEG Stream)
  6. Closed-Circuit ODAV Agent Loop Orchestrator
  7. FastAPI REST Server & Endpoints (/api/start-task, /api/step, /api/stream, /api/reset)
  8. Embedded HTML5 + Tailwind Touch Kiosk UI with Web Speech API (mr-IN, hi-IN, en-IN)
  9. Built-in Deterministic Contract Test Suite (run via: python standalone_seva.py --test)
===================================================================================
"""

import argparse
import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import sys
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

# -----------------------------------------------------------------------------
# 1. LOGGING & CONSTANTS
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("seva.standalone")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct")

MAX_STEP_BUDGET = 8
CONTEXT_WINDOW_SIZE = 3
STALL_THRESHOLD = 2
ACTION_TIMEOUT_MS = 5000
INFERENCE_TIMEOUT_SEC = 8.0
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 720

REQUIRED_SCHEMA_KEYS = ["thought", "intent", "action", "selector", "value", "feedback"]
VALID_ACTIONS = ["navigate", "click", "fill", "scroll", "wait", "finish", "fail"]

# -----------------------------------------------------------------------------
# 2. SCHEMA SANITIZATION & DETERMINISTIC CONTRACT VALIDATOR
# -----------------------------------------------------------------------------
def sanitize_json_markdown(raw_text: str) -> str:
    """Strips Markdown code fences and leading/trailing whitespace."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def validate_action_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    """Validates adherence to the PRD Section 5.1 JSON action contract."""
    for key in REQUIRED_SCHEMA_KEYS:
        if key not in payload:
            raise ValueError(f"Schema violation: missing required key '{key}'")
        if not isinstance(payload[key], str):
            payload[key] = str(payload[key])

    action = payload["action"].lower()
    if action not in VALID_ACTIONS:
        raise ValueError(f"Schema violation: invalid action '{action}'. Must be one of {VALID_ACTIONS}")
    payload["action"] = action
    return {k: payload[k] for k in REQUIRED_SCHEMA_KEYS}

# -----------------------------------------------------------------------------
# 3. ODAV STATE MANAGER & CONTEXT COMPACTOR (k=3, N=8)
# -----------------------------------------------------------------------------
class StateManager:
    """
    Manages session lifecycle, computes S(t) signatures, detects stalls,
    enforces context compaction (k=3), and audits step budget ceiling (N=8).
    """
    def __init__(self, max_steps: int = MAX_STEP_BUDGET, k_window: int = CONTEXT_WINDOW_SIZE):
        self.max_steps = max_steps
        self.k_window = k_window
        self.reset()

    def reset(self) -> None:
        """Purges in-memory state and citizen PII (DPDP Act 2023 compliance)."""
        self.active_session_id: Optional[str] = None
        self.citizen_goal: str = ""
        self.language: str = "mr"
        self.current_step: int = 0
        self.history: List[Dict[str, Any]] = []
        self.last_signature: Optional[str] = None
        self.stall_count: int = 0
        self.is_finished: bool = False
        self.is_stalled: bool = False
        self.is_budget_exhausted: bool = False

    def start_session(self, session_id: str, goal: str, language: str = "mr") -> None:
        self.reset()
        self.active_session_id = session_id
        self.citizen_goal = goal
        self.language = language
        logger.info(f"[StateManager] Session {session_id} initialized for goal: '{goal}' ({language})")

    def compute_signature(self, url: str, title: str, dom_elements: List[Dict[str, Any]]) -> str:
        """Computes deterministic 16-hex state signature S(t) = SHA256(URL + Title + DOM)[:16]."""
        dom_repr = json.dumps(dom_elements[:25], sort_keys=True)
        raw = f"{url}|{title}|{dom_repr}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def get_compacted_context(self) -> Dict[str, Any]:
        """Context Compaction (k=3): carries only original goal + last 3 step deltas."""
        recent = self.history[-self.k_window:] if len(self.history) > self.k_window else list(self.history)
        return {
            "goal": self.citizen_goal,
            "language": self.language,
            "step_count": self.current_step,
            "recent_actions": recent,
            "budget_remaining": max(0, self.max_steps - self.current_step)
        }

    def record_step(
        self,
        signature: str,
        action_dict: Dict[str, str],
        url: str,
        execution_success: bool = True
    ) -> Dict[str, Any]:
        self.current_step += 1

        # Check 2-step stall condition
        if self.last_signature is not None and signature == self.last_signature:
            self.stall_count += 1
        else:
            self.stall_count = 0
        self.last_signature = signature

        record = {
            "step": self.current_step,
            "signature": signature,
            "url": url,
            "action": action_dict,
            "success": execution_success,
            "stall_count": self.stall_count
        }
        self.history.append(record)

        if action_dict.get("action") == "finish":
            self.is_finished = True
        elif self.stall_count >= STALL_THRESHOLD:
            self.is_stalled = True
        elif self.current_step >= self.max_steps:
            self.is_budget_exhausted = True

        status = "finished" if self.is_finished else (
            "stalled" if self.is_stalled else (
                "budget_exhausted" if self.is_budget_exhausted else "active"
            )
        )

        return {
            "status": status,
            "step": self.current_step,
            "budget_remaining": max(0, self.max_steps - self.current_step),
            "state_signature": signature,
            "stalled": self.is_stalled,
            "finished": self.is_finished
        }

# -----------------------------------------------------------------------------
# 4. INFERENCE BRAIN & DETERMINISTIC FALLBACK ENGINE
# -----------------------------------------------------------------------------
class VMClient:
    """Communicates with OpenRouter Qwen 2.5 7B with resilient local heuristic fallback."""
    def __init__(self, api_key: str = OPENROUTER_API_KEY, model: str = OPENROUTER_MODEL):
        self.api_key = api_key
        self.model = model
        self.timeout = INFERENCE_TIMEOUT_SEC

    async def decide_next_action(
        self,
        goal: str,
        recent_history: List[Dict[str, Any]],
        url: str,
        dom_elements: List[Dict[str, Any]],
        language: str = "mr"
    ) -> Dict[str, str]:
        user_prompt = {
            "citizen_goal": goal,
            "language": language,
            "current_url": url,
            "recent_actions": recent_history,
            "top_dom_nodes": dom_elements[:25]
        }

        if not self.api_key:
            return self._local_heuristic_fallback(goal, url, dom_elements, language)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://seva-ai.kiosk.internal",
            "X-Title": "SEVA AI Kiosk Platform"
        }

        system_prompt = (
            "You are SEVA AI, an autonomous browser engine executing citizen public services on Indian portals.\n"
            "Return ONLY raw JSON with 6 keys: thought, intent, action, selector, value, feedback.\n"
            "Valid actions: navigate, click, fill, scroll, wait, finish, fail."
        )

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)}
            ],
            "temperature": 0.1,
            "max_tokens": 300
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"]
                cleaned = sanitize_json_markdown(raw_text)
                parsed = json.loads(cleaned)
                return validate_action_payload(parsed)
        except Exception as e:
            logger.warning(f"[VMClient] Remote inference fallback triggered ({e})")
            return self._local_heuristic_fallback(goal, url, dom_elements, language)

    def _local_heuristic_fallback(
        self,
        goal: str,
        url: str,
        dom_elements: List[Dict[str, Any]],
        language: str
    ) -> Dict[str, str]:
        lower_goal = goal.lower()
        if not url or url == "about:blank":
            if "income" in lower_goal or "उत्पन्न" in goal:
                return {
                    "thought": "Navigating to Aaple Sarkar Income Certificate portal.",
                    "intent": "navigate_menu",
                    "action": "navigate",
                    "selector": "",
                    "value": "http://localhost:8000/mock_portals/income.html",
                    "feedback": "उत्पन्नाचा दाखला पोर्टल उघडत आहे." if language == "mr" else "आय प्रमाण पत्र पोर्टल खोला जा रहा है."
                }
            elif "7/12" in lower_goal or "सातबारा" in goal or "land" in lower_goal:
                return {
                    "thought": "Navigating to Mahabhulekh 7/12 Land Records portal.",
                    "intent": "navigate_menu",
                    "action": "navigate",
                    "selector": "",
                    "value": "http://localhost:8000/mock_portals/satbara.html",
                    "feedback": "७/१२ उतारा पोर्टल उघडत आहे." if language == "mr" else "७/१२ भूलेख पोर्टल खोला जा रहा है."
                }

        for elem in dom_elements:
            text = elem.get("text", "").lower()
            sel = elem.get("selector", "")
            if "submit" in text or "अर्ज करा" in text:
                return {
                    "thought": f"Submitting form via {sel}.",
                    "intent": "click_action",
                    "action": "click",
                    "selector": sel,
                    "value": "",
                    "feedback": "अर्ज सादर करत आहे." if language == "mr" else "आवेदन जमा किया जा रहा है."
                }
            if "download" in text or "पावती" in text:
                return {
                    "thought": "Transaction complete. Emitting finish action.",
                    "intent": "finish",
                    "action": "finish",
                    "selector": sel,
                    "value": "",
                    "feedback": "आपला अर्ज पूर्ण झाला आहे." if language == "mr" else "आपका आवेदन पूर्ण हो गया है."
                }

        return {
            "thought": "Awaiting portal readiness.",
            "intent": "verify_output",
            "action": "wait",
            "selector": "",
            "value": "1000",
            "feedback": "सरकारी पोर्टल तपासत आहे." if language == "mr" else "सरकारी पोर्टल की जांच की जा रही है."
        }

# -----------------------------------------------------------------------------
# 5. PLAYWRIGHT CHROMIUM SANDBOX & CDP SCREENCASTER
# -----------------------------------------------------------------------------
class BrowserController:
    """Isolated Chromium instance with Chrome DevTools Protocol (CDP) screencasting."""
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._cdp_session = None
        self._latest_frame_bytes: bytes = b""
        self._frame_lock = asyncio.Lock()
        self._is_screencasting = False

    async def initialize(self) -> bool:
        try:
            from playwright.async_api import async_playwright
            logger.info("[BrowserController] Launching Chromium sandbox...")
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    f"--window-size={VIEWPORT_WIDTH},{VIEWPORT_HEIGHT}",
                ],
            )
            self._context = await self._browser.new_context(
                viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) SEVA-AI-Kiosk/2.0",
            )
            self._page = await self._context.new_page()
            self._page.set_default_timeout(ACTION_TIMEOUT_MS)

            await self._start_cdp_screencast()
            return True
        except Exception as e:
            logger.error(f"[BrowserController] Launch error: {e}")
            return False

    async def _start_cdp_screencast(self) -> None:
        if not self._page or self._is_screencasting:
            return
        try:
            self._cdp_session = await self._context.new_cdp_session(self._page)
            async def on_frame(event):
                try:
                    data = event.get("data")
                    sid = event.get("sessionId")
                    if data:
                        raw = base64.b64decode(data)
                        async with self._frame_lock:
                            self._latest_frame_bytes = raw
                    if self._cdp_session and sid:
                        await self._cdp_session.send("Page.screencastFrameAck", {"sessionId": sid})
                except Exception:
                    pass

            self._cdp_session.on("Page.screencastFrame", on_frame)
            await self._cdp_session.send("Page.startScreencast", {
                "format": "jpeg",
                "quality": 80,
                "maxWidth": VIEWPORT_WIDTH,
                "maxHeight": VIEWPORT_HEIGHT,
                "everyNthFrame": 1
            })
            self._is_screencasting = True
            logger.info("[BrowserController] CDP Screencast stream engaged.")
        except Exception as e:
            logger.warning(f"[BrowserController] CDP screencast fallback: {e}")

    async def get_latest_frame(self) -> bytes:
        async with self._frame_lock:
            if self._latest_frame_bytes:
                return self._latest_frame_bytes
        if self._page:
            try:
                return await self._page.screenshot(type="jpeg", quality=75)
            except Exception:
                pass
        return b""

    async def mjpeg_frame_generator(self):
        """Yields continuous multipart JPEG frame stream at ~25 FPS."""
        frame_interval = 1.0 / 25.0
        while True:
            t0 = time.time()
            frame = await self.get_latest_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
                    + frame + b"\r\n"
                )
            elapsed = time.time() - t0
            sleep_time = max(0.005, frame_interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def extract_interactive_elements(self) -> Tuple[str, str, List[Dict[str, Any]]]:
        """Extracts URL, Title, and top 25 interactive DOM nodes."""
        if not self._page:
            return "about:blank", "Empty", []
        url = self._page.url
        title = await self._page.title()

        script = """
        () => {
            const elements = [];
            const interactiveSelectors = 'button, a[href], input:not([type="hidden"]), select, textarea, [role="button"]';
            const nodes = Array.from(document.querySelectorAll(interactiveSelectors));
            for (const el of nodes) {
                if (elements.length >= 25) break;
                const rect = el.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) continue;
                let text = (el.innerText || el.value || el.placeholder || '').trim().substring(0, 60);
                let selector = el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : el.tagName.toLowerCase());
                elements.push({
                    tag: el.tagName.toLowerCase(),
                    text: text,
                    selector: selector,
                    placeholder: el.placeholder || ''
                });
            }
            return elements;
        }
        """
        try:
            elements = await self._page.evaluate(script)
            return url, title, elements[:25]
        except Exception:
            return url, title, []

    async def execute_action(self, action: str, selector: str, value: str) -> Tuple[bool, str]:
        if not self._page:
            return False, "Browser offline"
        action = action.lower()
        try:
            if action == "navigate":
                target = value or selector
                if not (target.startswith("http://") or target.startswith("https://")):
                    target = f"http://{target}"
                await self._page.goto(target, wait_until="commit", timeout=ACTION_TIMEOUT_MS)
                return True, f"Navigated to {target}"
            elif action == "click":
                await self._page.click(selector, timeout=ACTION_TIMEOUT_MS)
                return True, f"Clicked {selector}"
            elif action == "fill":
                await self._page.fill(selector, value, timeout=ACTION_TIMEOUT_MS)
                return True, f"Filled '{value}' into {selector}"
            elif action == "scroll":
                delta = int(value) if (value and value.isdigit()) else 400
                await self._page.evaluate(f"window.scrollBy(0, {delta})")
                return True, f"Scrolled {delta}px"
            elif action == "wait":
                wait_time = min(5000, int(value)) if (value and value.isdigit()) else 1000
                await asyncio.sleep(wait_time / 1000.0)
                return True, f"Waited {wait_time}ms"
            elif action == "finish":
                return True, "Task completed successfully"
            elif action == "fail":
                return False, f"Action flagged as failed: {value}"
            return False, f"Unknown action: {action}"
        except Exception as e:
            return False, str(e)

    async def close(self) -> None:
        self._is_screencasting = False
        try:
            if self._cdp_session:
                await self._cdp_session.detach()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass

# -----------------------------------------------------------------------------
# 6. ODAV AGENT LOOP ORCHESTRATOR
# -----------------------------------------------------------------------------
class ODAVAgentLoop:
    def __init__(self, browser: BrowserController, brain: VMClient, state_mgr: StateManager, tts_cb=None):
        self.browser = browser
        self.brain = brain
        self.state_mgr = state_mgr
        self.tts_cb = tts_cb

    async def run_single_step(self) -> Dict[str, Any]:
        # 1. OBSERVE
        url, title, dom = await self.browser.extract_interactive_elements()
        sig_before = self.state_mgr.compute_signature(url, title, dom)

        # 2. DECIDE
        ctx = self.state_mgr.get_compacted_context()
        decision = await self.brain.decide_next_action(
            goal=ctx["goal"],
            recent_history=ctx["recent_actions"],
            url=url,
            dom_elements=dom,
            language=ctx["language"]
        )

        if decision.get("feedback") and self.tts_cb:
            self.tts_cb(decision["feedback"], ctx["language"])

        # 3. ACT
        success, exec_msg = await self.browser.execute_action(
            decision.get("action", "wait"),
            decision.get("selector", ""),
            decision.get("value", "")
        )
        await asyncio.sleep(0.5)

        # 4. VERIFY
        new_url, new_title, new_dom = await self.browser.extract_interactive_elements()
        sig_after = self.state_mgr.compute_signature(new_url, new_title, new_dom)

        step_res = self.state_mgr.record_step(
            signature=sig_after,
            action_dict=decision,
            url=new_url,
            execution_success=success
        )

        if step_res.get("stalled"):
            logger.warning("[AgentLoop] 2-Step stall detected. Executing recovery scroll.")
            await self.browser.execute_action("scroll", "", "300")

        return {
            "step": step_res["step"],
            "status": step_res["status"],
            "decision": decision,
            "signature_before": sig_before,
            "signature_after": sig_after,
            "mutated": sig_before != sig_after,
            "execution_msg": exec_msg,
            "stalled": step_res.get("stalled", False),
            "finished": step_res.get("finished", False)
        }

# -----------------------------------------------------------------------------
# 7. EMBEDDED KIOSK HTML5 DASHBOARD
# -----------------------------------------------------------------------------
INDEX_HTML = """<!DOCTYPE html>
<html lang="mr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SEVA AI — Digital Assistance Kiosk</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white font-sans select-none overflow-hidden">
  <header class="h-20 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-8">
    <div class="flex items-center space-x-4">
      <div class="w-12 h-12 bg-amber-500 rounded-full flex items-center justify-center font-bold text-2xl text-slate-900">स</div>
      <div>
        <h1 class="text-2xl font-bold text-amber-400">SEVA AI</h1>
        <p class="text-xs text-slate-400">ग्रामपंचायत व सेतू केंद्र डिजिटल सहाय्यक (ODAV Loop)</p>
      </div>
    </div>
    <div class="flex items-center space-x-3 bg-slate-950 px-4 py-2 rounded-xl border border-slate-700">
      <span class="text-xs font-semibold text-slate-400 uppercase">Step Budget:</span>
      <span id="budget" class="text-xl font-mono font-bold text-emerald-400">8 / 8</span>
    </div>
  </header>

  <main class="grid grid-cols-12 gap-6 p-6 h-[calc(100vh-5rem)]">
    <!-- Viewport -->
    <section class="col-span-8 bg-slate-950 rounded-2xl border border-slate-800 flex flex-col overflow-hidden relative shadow-2xl">
      <div class="bg-slate-800/80 px-4 py-2 flex items-center justify-between border-b border-slate-700">
        <span class="text-sm font-semibold text-slate-300">Live CDP Viewport (>=20 FPS)</span>
        <span id="active-url" class="text-xs font-mono text-slate-400 truncate max-w-md">about:blank</span>
      </div>
      <div class="flex-1 flex items-center justify-center bg-black relative">
        <img id="stream" src="/api/stream" class="w-full h-full object-contain">
      </div>
    </section>

    <!-- Controls & Logs -->
    <section class="col-span-4 flex flex-col space-y-4">
      <div class="bg-slate-800 rounded-2xl p-6 border border-slate-700 flex flex-col items-center text-center shadow-lg">
        <p class="text-base font-medium text-slate-200 mb-3">खालील बटण दाबून बोला किंवा सेवा निवडा</p>
        <button id="mic" class="w-24 h-24 rounded-full bg-amber-500 hover:bg-amber-400 transition flex items-center justify-center shadow-xl shadow-amber-500/20 text-3xl">🎙️</button>
        <p id="speech-text" class="text-xs font-mono text-amber-300 mt-3 italic min-h-[1.5rem]">"माझा उत्पन्नाचा दाखला काढायचा आहे..."</p>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <button onclick="startService('उत्पन्नाचा दाखला काढा')" class="bg-slate-800 hover:bg-slate-700 p-3 rounded-xl border border-slate-700 text-left">
          <div class="font-bold text-sm">📜 उत्पन्न दाखला</div>
          <div class="text-xs text-slate-400">Income Certificate</div>
        </button>
        <button onclick="startService('७/१२ उतारा काढा')" class="bg-slate-800 hover:bg-slate-700 p-3 rounded-xl border border-slate-700 text-left">
          <div class="font-bold text-sm">🌾 ७/१२ उतारा</div>
          <div class="text-xs text-slate-400">Land Records</div>
        </button>
      </div>

      <div class="flex-1 bg-slate-950 rounded-2xl p-4 border border-slate-800 flex flex-col overflow-hidden">
        <div class="flex justify-between pb-2 border-b border-slate-800 mb-2">
          <span class="text-xs font-bold text-slate-400 uppercase">ODAV Audit Log</span>
          <button onclick="resetSession()" class="text-xs font-bold text-rose-400 hover:text-rose-300">Purge</button>
        </div>
        <div id="logs" class="flex-1 overflow-y-auto space-y-2 text-xs font-mono pr-1 text-slate-400">
          <div>Loop ready. Awaiting citizen voice input.</div>
        </div>
      </div>
    </section>
  </main>

  <script>
    let rec = null;
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      rec = new SpeechRec();
      rec.lang = 'mr-IN';
      rec.onresult = (e) => {
        const text = e.results[0][0].transcript;
        document.getElementById('speech-text').innerText = `"${text}"`;
        startService(text);
      };
    }

    document.getElementById('mic').onclick = () => {
      if (rec) {
        try { rec.start(); } catch(e) { rec.stop(); }
      }
    };

    async function startService(task) {
      log('CITIZEN', `Goal: "${task}"`);
      const res = await fetch('/api/start-task', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task: task, language: 'mr'})
      });
      const data = await res.json();
      log('ODAV:START', `Session ${data.session_id} active. Initiating loop...`);
      stepLoop();
    }

    async function stepLoop() {
      try {
        const res = await fetch('/api/step', {method: 'POST'});
        const data = await res.json();
        if (data.detail) { log('INFO', data.detail); return; }
        const d = data.decision || {};
        log('DECIDE', `[${d.action}] ${d.selector || ''} -> ${d.thought}`);
        log('VERIFY', `Mutated: ${data.mutated} | Status: ${data.status}`);
        document.getElementById('budget').innerText = `${8 - data.step} / 8`;
        if (!data.finished && data.status !== 'budget_exhausted') {
          setTimeout(stepLoop, 1200);
        } else {
          log('FINISH', `Session finished: ${data.status}`);
        }
      } catch(e) { log('ERROR', e.message); }
    }

    async function resetSession() {
      await fetch('/api/reset', {method: 'POST'});
      log('PURGE', 'Session state wiped. Ephemeral data purged.');
      document.getElementById('budget').innerText = '8 / 8';
    }

    function log(phase, msg) {
      const l = document.getElementById('logs');
      const div = document.createElement('div');
      div.innerHTML = `<span class="text-amber-400 font-bold">[${phase}]</span> ${msg}`;
      l.appendChild(div);
      l.scrollTop = l.scrollHeight;
    }
  </script>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# 8. FASTAPI REST SERVER SETUP
# -----------------------------------------------------------------------------
app = FastAPI(title="SEVA AI Standalone Kiosk Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state_mgr = StateManager()
vm_client = VMClient()
browser = BrowserController(headless=True)
agent_loop = ODAVAgentLoop(browser, vm_client, state_mgr)

class StartTaskRequest(BaseModel):
    task: str
    language: str = "mr"

@app.on_event("startup")
async def on_startup():
    await browser.initialize()

@app.on_event("shutdown")
async def on_shutdown():
    await browser.close()

@app.get("/", response_class=HTMLResponse)
async def get_kiosk_ui():
    return HTMLResponse(content=INDEX_HTML)

@app.post("/api/start-task")
async def api_start_task(req: StartTaskRequest):
    sid = str(uuid.uuid4())[:8]
    state_mgr.start_session(session_id=sid, goal=req.task, language=req.language)
    return {"status": "started", "session_id": sid, "step": 0, "max_steps": MAX_STEP_BUDGET}

@app.post("/api/step")
async def api_step():
    if not state_mgr.active_session_id:
        raise HTTPException(status_code=400, detail="No active session. Call /api/start-task first.")
    if state_mgr.is_finished:
        return {"status": "finished", "step": state_mgr.current_step, "detail": "Task already completed"}
    if state_mgr.is_budget_exhausted:
        return {"status": "budget_exhausted", "step": state_mgr.current_step, "detail": "Budget ceiling reached"}
    return await agent_loop.run_single_step()

@app.get("/api/stream")
async def api_stream():
    return StreamingResponse(
        browser.mjpeg_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/session-state")
async def api_session_state():
    ctx = state_mgr.get_compacted_context()
    return {
        "active": state_mgr.active_session_id is not None,
        "session_id": state_mgr.active_session_id,
        "step": state_mgr.current_step,
        "max_steps": state_mgr.max_steps,
        "goal": state_mgr.citizen_goal,
        "recent_history": ctx["recent_actions"],
        "stalled": state_mgr.is_stalled,
        "finished": state_mgr.is_finished
    }

@app.post("/api/reset")
async def api_reset():
    state_mgr.reset()
    if browser._page:
        try:
            await browser._page.goto("about:blank")
        except Exception:
            pass
    return {"status": "reset", "purged": True}

# -----------------------------------------------------------------------------
# 9. SELF-TEST RUNNER (python standalone_seva.py --test)
# -----------------------------------------------------------------------------
def run_deterministic_tests():
    print("=" * 60)
    print("RUNNING DETERMINISTIC ODAV INVARIANT TESTS")
    print("=" * 60)

    # Test 1: Strict JSON Schema Validator
    valid_payload = {
        "thought": "Find button",
        "intent": "click_action",
        "action": "click",
        "selector": "#btn",
        "value": "",
        "feedback": "क्लिक करत आहे"
    }
    res = validate_action_payload(valid_payload)
    assert res == valid_payload, "Schema validation failure"
    print("[PASS] Test 1: Strict 6-Key Schema Contract")

    # Test 2: Markdown Stripping
    wrapped = "```json\n" + json.dumps(valid_payload) + "\n```"
    unwrapped = sanitize_json_markdown(wrapped)
    assert json.loads(unwrapped) == valid_payload
    print("[PASS] Test 2: Markdown Code-Fence Stripper")

    # Test 3: Context Compactor (k=3)
    sm = StateManager()
    sm.start_session("test_01", "Get Land Records")
    for i in range(10):
        sm.record_step(f"sig_{i}", {"action": "wait", "step": str(i)}, f"http://test/{i}")
    compact = sm.get_compacted_context()
    assert len(compact["recent_actions"]) == 3
    assert compact["recent_actions"][-1]["step"] == 10
    print("[PASS] Test 3: Rolling Context Compactor (k=3)")

    # Test 4: Budget Ceiling (N=8)
    sm2 = StateManager(max_steps=8)
    sm2.start_session("test_02", "Income Cert")
    for i in range(7):
        sm2.record_step(f"sig_{i}", {"action": "click"}, f"http://test/{i}")
        assert not sm2.is_budget_exhausted
    res_final = sm2.record_step("sig_7", {"action": "click"}, "http://test/7")
    assert res_final["status"] == "budget_exhausted"
    assert sm2.is_budget_exhausted
    print("[PASS] Test 4: Hard 8-Step Budget Ceiling")

    # Test 5: Two-Step Stall Detector
    sm3 = StateManager()
    sm3.start_session("test_03", "Stall Test")
    sm3.record_step("sig_SAME", {"action": "click"}, "http://test")
    assert sm3.stall_count == 0
    sm3.record_step("sig_SAME", {"action": "click"}, "http://test")
    assert sm3.stall_count == 1
    res_stall = sm3.record_step("sig_SAME", {"action": "click"}, "http://test")
    assert res_stall["status"] == "stalled"
    assert sm3.is_stalled
    print("[PASS] Test 5: Two-Step Stall Recovery Detector")

    print("=" * 60)
    print("ALL TESTS PASSED (100% SUCCESS)")
    print("=" * 60)

# -----------------------------------------------------------------------------
# 10. CLI LAUNCHER
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SEVA AI Kiosk Platform")
    parser.add_argument("--test", action="store_true", help="Run deterministic invariant tests")
    parser.add_argument("--port", type=int, default=PORT, help="Port to bind server")
    args = parser.parse_args()

    if args.test:
        run_deterministic_tests()
        sys.exit(0)

    print("=" * 65)
    print("🏛️  SEVA AI - Vernacular Digital Assistance Kiosk Platform")
    print(f"[*] Starting Standalone Kiosk Server on http://{HOST}:{args.port}")
    print(f"[*] View Kiosk Touch UI:     http://localhost:{args.port}/")
    print(f"[*] CDP Video Stream:        http://localhost:{args.port}/api/stream")
    print("=" * 65)
    uvicorn.run(app, host=HOST, port=args.port, log_level="info")
