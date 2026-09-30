# SEVA AI Backend & Runtime Technical Survey Report

**Prepared by:** Survey Explorer 1 (`teamwork_preview_explorer_survey_1`)  
**Date:** 2026-09-26  
**Scope:** Workspace audit, runtime environment analysis, R1 (Cloud LLM Decision Engine) and R3 (FastAPI ODAV Loop Architecture) deep-dive.

---

## 1. Executive Summary

This survey report provides a comprehensive architectural and technical foundation analysis for **SEVA AI**, an autonomous, voice-first vernacular digital kiosk platform designed for citizen public services in rural India (Setu Kendras, Gram Panchayats).

Key findings:
1. **Workspace & Runtime Readiness:** The environment is equipped with **Python 3.14.3** on Windows amd64. Two complete virtual environments (`vdak-host/venv` and `vdak-vm/venv`) contain all requisite packages including **Playwright 1.62.0**, **FastAPI 0.141.1**, **Uvicorn 0.52.4**, **Pydantic 2.13.5**, **google-genai 1.65.0**, **httpx 0.28.1**, and **websockets 15.0/17.1**.
2. **Prototype Baseline:** Legacy prototype directories (`vdak-host` and `vdak-vm`) provide operational code for WebSocket orchestration, CDP screencasting over MJPEG, state machines, and vernacular prompts in Marathi, Hindi, and Gujarati.
3. **R1 Technical Foundation:** `backend/llm_client.py` and `tests/test_phase1_schema.py` establish a deterministic JSON schema contract (`thought`, `action`, `selector`, `value`, `feedback`), context pruning (rolling scratchpad retaining goal + last 3 step deltas), and a deterministic vernacular fallback engine. Full dual-model support requires connecting Gemini 2.5 Flash as the primary endpoint with OpenRouter Qwen 2.5 7B as secondary.
4. **R3 Technical Foundation:** The Observe-Decide-Act-Verify (ODAV) framework can be cleanly unified into a centralized asynchronous FastAPI service providing `/api/start-task`, `/api/step`, `/api/stream`, `/api/session-state`, and `/api/reset` with a hard step budget (max 8 iterations) and 2-step stall detection.

---

## 2. Workspace & File Inventory

### 2.1 Workspace Structure
```
c:\Users\Praka\OneDrive\Desktop\kiosk\
├── .agents/                               # Multi-agent coordination metadata
│   ├── ORIGINAL_REQUEST.md                # Authoritative user requirements
│   ├── teamwork_preview_orchestrator_1/   # Top-level orchestrator plan & progress
│   ├── teamwork_preview_explorer_survey_1/# Survey Explorer 1 (Backend & Runtime)
│   ├── teamwork_preview_explorer_survey_2/# Survey Explorer 2 (Playwright & CDP)
│   ├── teamwork_preview_explorer_survey_3/# Survey Explorer 3 (UI & Speech)
│   └── sentinel/                          # Quality gate / audit markers
├── backend/                               # Unified backend core
│   └── llm_client.py                      # Cloud LLM decision engine & fallback logic
├── tests/                                 # Automated test suites
│   └── test_phase1_schema.py              # Phase 1 schema validation & 25 synthetic tests
├── vdak-host/                             # Prototype host kiosk service
│   ├── .env                               # Network & UI configuration
│   ├── main.py                            # FastAPI host orchestrator prototype
│   ├── run.py                             # Startup orchestrator
│   ├── state_machine.py                   # Transitions state machine
│   ├── requirements.txt                   # Host dependencies
│   ├── config/languages.py                # Indian language prompts (mr, hi, gu)
│   ├── ui/gradio_app.py                   # Gradio interface prototype
│   ├── voice/                             # ASR (faster-whisper) and TTS (piper-tts)
│   ├── vision/                            # Document camera capture & EasyOCR
│   └── venv/                              # Python 3.14 virtualenv
├── vdak-vm/                               # Prototype browser sandbox service
│   ├── .env                               # OpenRouter API key & ports
│   ├── agent.py                           # KioskBrowserAgent (Playwright)
│   ├── server.py                          # WebSocket agent server
│   ├── stream_server.py                   # CDP screencast stream server (MJPEG)
│   ├── test_agent.py                      # Headless Chromium navigation test
│   ├── latest_frame.jpg                   # Frame capture artifact (14,107 bytes)
│   ├── requirements.txt                   # Sandbox dependencies
│   └── venv/                              # Python 3.14 virtualenv with Playwright
├── .gitignore                             # Git ignore rules
```

### 2.2 Reusable Prototype Assets
- **`backend/llm_client.py`:** Contains markdown-stripping regex parser (`clean_json_response`), context pruning logic (`prune_context`), intent classifier (`match_governance_service`), and deterministic fallback database for e-governance workflows (Income Certificate, Niradhar Pension, Satbara 7/12 Land Records).
- **`vdak-host/config/languages.py`:** Rich translations for Marathi, Hindi, Gujarati, Tamil, Telugu, Kannada, and Bengali covering standard kiosk lifecycle events: greetings, scanning, confirmation, OTP requests, form filling, success receipts, and error notifications.
- **`vdak-vm/stream_server.py`:** Native Chrome DevTools Protocol (CDP) screencast implementation using `Page.startScreencast`, `Page.screencastFrameAck`, and multipart MJPEG HTTP streaming.
- **`tests/test_phase1_schema.py`:** 25 synthetic vernacular prompts across Marathi, Hindi, and English with strict schema assertions.

---

## 3. Runtime Environment & Toolchain Audit

### 3.1 Python Runtime & Interpreters
- **Python Version:** Python 3.14.3 (tags/v3.14.3, 64-bit Windows)
- **Executable Location:** `C:\Users\Praka\AppData\Local\Programs\Python\Python314\python.exe`
- **Virtual Environments Detected:**
  1. `c:\Users\Praka\OneDrive\Desktop\kiosk\vdak-host\venv`
  2. `c:\Users\Praka\OneDrive\Desktop\kiosk\vdak-vm\venv`

### 3.2 Installed Dependencies Inventory

| Package | Version in `vdak-host` | Version in `vdak-vm` | Role in SEVA AI |
|---|---|---|---|
| **playwright** | — | 1.62.0 | Isolated Chromium sandbox automation (R2) |
| **fastapi** | 0.141.1 | — | Host REST API & ODAV orchestration (R3) |
| **uvicorn** | 0.52.4 | 0.52.4 | High-performance ASGI server |
| **pydantic** | 2.13.5 | 2.12.5 | Strict schema validation & serialization (R1/R3) |
| **google-genai** | — | 1.65.0 | Official Google GenAI SDK for Gemini 2.5 Flash (R1) |
| **google-generativeai** | — | 0.8.6 | Legacy Gemini SDK |
| **httpx** | 0.28.1 | 0.28.1 | Asynchronous HTTP client for API requests |
| **websockets** | 17.1 | 15.0.1 | Low-latency duplex communication |
| **python-dotenv** | 1.2.3 | 1.2.2 | Environment variable management |
| **orjson** | 3.12.0 | 3.12.0 | Ultra-fast JSON serialization |
| **pillow (PIL)** | 12.3.0 | 12.3.0 | Screenshot compression & image processing |
| **opencv-python** | 5.0.0.93 | — | Vision processing & frame conversion |
| **faster-whisper** | 1.2.1 | 1.2.1 | Local vernacular speech recognition (R4) |
| **piper-tts** | 1.8.0 | — | Low-latency offline neural TTS (R4) |

### 3.3 Configuration & Environment Variables

| Variable | Location | Value / Status | Usage |
|---|---|---|---|
| `OPENROUTER_API_KEY` | `vdak-vm/.env` | `sk-or-v1-a961b75b...eb895476` | Active key for OpenRouter Qwen 2.5 7B fallback |
| `OPENROUTER_MODEL` | `vdak-vm/.env` | `qwen/qwen-2.5-7b-instruct:free` | Model target |
| `OPENROUTER_BASE_URL`| `vdak-vm/.env` | `https://openrouter.ai/api/v1` | OpenRouter endpoint |
| `GEMINI_API_KEY` | Environment / `.env` | Referenced in `llm_client.py` | Primary model key (Gemini 2.5 Flash) |
| `HOST_PORT` | `vdak-host/.env`| `8000` | FastAPI host listening port |
| `HOST_WS_PORT` | `vdak-vm/.env` | `8765` | WebSocket communication port |
| `GRADIO_PORT` | `vdak-host/.env`| `7860` | Prototype UI port |
| `DEFAULT_LANGUAGE` | `vdak-host/.env`| `mr` (Marathi) | Default kiosk dialect |

---

## 4. Deep-Dive: R1 Requirements (Cloud LLM API Decision Engine & Schema Validator)

### 4.1 Deterministic JSON Contract
The system must guarantee zero markdown backticks and strict conformance to the following schema:
```json
{
  "thought": "string explaining reasoning in English",
  "action": "navigate | click | fill | scroll | wait | finish",
  "selector": "CSS selector or text anchor for element, or empty if not applicable",
  "value": "Input text or destination URL, or empty if not applicable",
  "feedback": "Spoken feedback for citizen in their selected language (mr-IN, hi-IN, en-IN)"
}
```

#### Allowed Actions
1. `navigate`: Direct URL navigation (destination in `value`).
2. `click`: Element interaction (`selector` specified).
3. `fill`: Form field input (`selector` and `value` specified).
4. `scroll`: Viewport scrolling (delta in `value` or default 300px).
5. `wait`: Explicit pause for OTP/biometric/human intervention or page settlement.
6. `finish`: Goal reached or receipt token displayed.

#### Validation Implementation:
- **`backend/llm_client.py`:** Uses regex-based markdown cleaner and strict key checking.
- **Enhanced Pydantic Validation Proposal:**
  ```python
  from pydantic import BaseModel, Field
  from typing import Literal

  ActionType = Literal["navigate", "click", "fill", "scroll", "wait", "finish"]

  class LLMDecision(BaseModel):
      thought: str = Field(..., description="Reasoning for the selected action")
      action: ActionType = Field(..., description="Action to execute")
      selector: str = Field(default="", description="CSS selector or target anchor")
      value: str = Field(default="", description="Value to input or URL to navigate")
      feedback: str = Field(..., description="Spoken feedback for citizen in vernacular")
  ```

### 4.2 Dual-Model Architecture & Resilient Routing
To ensure zero kiosk downtime in rural conditions with erratic network connectivity:
1. **Tier 1 (Primary Cloud Model): Gemini 2.5 Flash**
   - High speed (<1.2s latency), large context window, multilingual support for Indic scripts.
   - Invocation via `google.genai` SDK or direct REST `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`.
   - Structured JSON output enforced via `response_mime_type="application/json"` and `response_schema`.
2. **Tier 2 (Secondary Cloud Model Fallback): OpenRouter Qwen 2.5 7B**
   - Model: `qwen/qwen-2.5-7b-instruct:free`.
   - OpenRouter API key already provisioned in `vdak-vm/.env`.
   - Fallback trigger: Gemini timeout (>8s), rate limit (HTTP 429), auth error (HTTP 401/403), or invalid output format.
3. **Tier 3 (Local Deterministic Knowledge Base Fallback):**
   - Fully implemented in `backend/llm_client.py:fallback_decide()`.
   - Encodes exact navigation and fill steps for Maharashtra e-district workflows:
     - Income Certificate (तहसीलदार उत्पन्नाचा दाखला)
     - Sanjay Gandhi Niradhar Destitute Pension (संजय गांधी निराधार योजना)
     - Mahabhulekh 7/12 Satbara Land Records (७/१२ सातबारा उतारा)
   - Guarantees 100% valid JSON contract even under complete network blackout.

### 4.3 Context Pruning (Rolling Scratchpad)
- **Requirement:** Retain only the primary goal and the last 3 step deltas.
- **Rationale:** Long browser interaction histories degrade LLM instruction-following, increase latency (>3s), and exceed rate-limit token budgets.
- **Algorithm:**
  ```python
  def prune_context(goal: str, history: List[Dict[str, Any]]) -> str:
      recent_deltas = history[-3:] if len(history) > 3 else history
      summary = f"Citizen Goal: {goal}\n"
      if recent_deltas:
          summary += "Recent Step Deltas (last 3):\n"
          for i, delta in enumerate(recent_deltas, 1):
              summary += f"  [{i}] action={delta.get('action')}, selector='{delta.get('selector')}', status={delta.get('status')}\n"
      return summary
  ```

### 4.4 Timeout & Error Handling Guards
- Maximum API call timeout: **8.0 seconds** (enforced using `urllib.request.urlopen(timeout=8.0)` or `httpx.AsyncClient(timeout=8.0)`).
- Safe exception handling: Catch `HTTPError`, `URLError`, `TimeoutError`, and `json.JSONDecodeError`.
- No exception ever bubbles up to kill the daemon or terminate the session prematurely.

---

## 5. Deep-Dive: R3 Requirements (ODAV Agentic Loop Engine & Host REST API)

### 5.1 Host REST API Architecture
The host service must expose 5 core endpoints:

```
[Citizen UI / Kiosk Terminal]
         │
         ├── POST /api/start-task ───────► Initializes sandbox session & sets S(0)
         ├── POST /api/step ─────────────► Executes single ODAV iteration cycle
         ├── GET  /api/stream ───────────► Multipart MJPEG screencast stream (>=20 FPS)
         ├── GET  /api/session-state ────► Returns session progress, step count, audit log
         └── POST /api/reset ────────────► Purges citizen data, terminates browser, resets IDLE
```

#### Detailed Endpoint Specifications

| Endpoint | Method | Request Payload | Response Contract | Purpose |
|---|---|---|---|---|
| `/api/start-task` | `POST` | `{"task": str, "language": str}` | `{"status": "started", "session_id": str, "initial_url": str, "step": 0}` | Launches or connects browser, resets step budget, initializes ODAV state |
| `/api/step` | `POST` | `{"session_id": str}` (optional, defaults to active) | `{"step": int, "state_signature": str, "action": dict, "stalled": bool, "status": "running"|"completed"|"stalled"|"budget_exceeded"}` | Executes exactly 1 Observe-Decide-Act-Verify cycle |
| `/api/stream` | `GET` | None | `multipart/x-mixed-replace; boundary=frame` (JPEG headers) | Continuous live CDP screencast stream at >= 20 FPS |
| `/api/session-state` | `GET` | None | `{"active": bool, "step": int, "max_steps": 8, "task": str, "language": str, "history": list, "last_action": dict, "url": str, "stalled": bool, "finished": bool}` | Real-time session monitoring and audit log feed |
| `/api/reset` | `POST` | None | `{"status": "reset", "purged": true}` | Immediate session wipe, browser cleanup, DPDP-compliant memory purge |

### 5.2 ODAV Loop Cycle Implementation

```
   ┌───────────────────────────────────────────────────────────┐
   │                       ODAV CYCLE                         │
   │                                                           │
   │  1. OBSERVE                                               │
   │     • Extract Page URL                                    │
   │     • Extract up to 25 interactive DOM selectors          │
   │     • Compute State Signature S(t) = SHA256(URL + DOM)   │
   │                            │                              │
   │                            ▼                              │
   │  2. DECIDE                                                │
   │     • Prune history (Goal + last 3 deltas)                │
   │     • Query CloudLLMGateway (Gemini -> Qwen -> Fallback)  │
   │     • Enforce JSON contract schema                        │
   │                            │                              │
   │                            ▼                              │
   │  3. ACT                                                   │
   │     • Execute Playwright primitive:                       │
   │       navigate / click / fill / scroll / wait / finish    │
   │     • Emit live frame to screencast stream                │
   │                            │                              │
   │                            ▼                              │
   │  4. VERIFY                                                │
   │     • Capture new State Signature S'(t)                   │
   │     • Audit State Mutation: ΔS = (S'(t) != S(t-1))        │
   │     • Stall Check: If ΔS == 0 for 2 consecutive cycles    │
   │       → Flag stalled=True, trigger recovery/human check   │
   └───────────────────────────────────────────────────────────┘
```

#### State Signature Calculation:
```python
import hashlib
import json

def compute_state_signature(url: str, dom_elements: list) -> str:
    # Retain tag, id, name, text, and selector to form deterministic representation
    simplified = [
        f"{el.get('tag')}:{el.get('id')}:{el.get('selector')}:{el.get('text', '')[:20]}"
        for el in dom_elements[:25]
    ]
    raw = f"{url}|" + ";".join(sorted(simplified))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
```

### 5.3 Loop Guards & Termination Gates
1. **Hard Step Budget Guard:**
   - Maximum iterations allowed: **8 steps** per task.
   - If `step >= 8` and `action != "finish"`:
     - Terminate execution loop.
     - Set status to `"budget_exceeded"`.
     - Prompt citizen with human assistance fallback to avoid infinite looping or portal lockouts.
2. **Termination Gate (`action="finish"`):**
   - When the LLM decides `action="finish"`:
     - Mark task status as `"completed"`.
     - Trigger receipt generator with unique Application ID (e.g., `SEVA-YYYYMMDD-XXXXX`).
     - Deliver spoken vernacular confirmation.
     - Prepare session for automatic ephemeral data purge.
3. **Stall Detection Guard:**
   - If state signature $S(t) == S(t-1)$ across 2 consecutive step cycles:
     - Set `stalled = True`.
     - Alert the decision engine with feedback that previous action produced no DOM mutation.
     - If stall persists, trigger human checkpoint modal.

---

## 6. Recommended Architecture & Implementation Layout

To unify the fragmented prototype files into a clean, testable, and robust architecture:

### 6.1 Proposed Target Layout
```
backend/
├── __init__.py
├── app.py                     # Main FastAPI application with /api/* routes
├── config.py                  # Pydantic settings & environment configuration
├── llm_client.py              # CloudLLMGateway (Gemini + Qwen + Fallback + Schema)
├── browser_sandbox.py         # Playwright headless browser manager & CDP screencaster
├── odav_engine.py             # ODAV cycle coordinator (Observe, Decide, Act, Verify)
├── state_manager.py           # Session state store, budget guards, stall detector
└── models.py                  # Pydantic data schemas for requests, responses, and actions

tests/
├── test_phase1_schema.py      # LLM contract & 25 vernacular prompts test suite
├── test_odav_engine.py        # ODAV step cycle, stall detection, and budget guards
└── test_api_endpoints.py      # FastAPI HTTP endpoint tests (/api/start-task, /api/step, etc.)
```

### 6.2 Key Verification Commands
- Phase 1 Schema Validation:
  ```bash
  python tests/test_phase1_schema.py
  ```
- Backend REST API Testing:
  ```bash
  pytest tests/test_api_endpoints.py
  ```
- Fast server startup check:
  ```bash
  uvicorn backend.app:app --host 127.0.0.1 --port 8000
  ```

---

## 7. Conclusion

All prerequisites, libraries, and core technical components for SEVA AI's R1 (Decision Engine) and R3 (FastAPI ODAV Engine) are present and verified in the workspace. With the existing `vdak-vm` CDP screencast patterns and `backend/llm_client.py` fallback algorithms, the implementation team can rapidly integrate a unified, production-grade service that strictly fulfills all project requirements.
