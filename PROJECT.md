# Project: SEVA AI Kiosk Platform

## Architecture
SEVA AI is an autonomous, voice-first, vernacular digital kiosk platform for rural Indian citizen public services (Setu Kendras, Gram Panchayats). It implements an Observe-Decide-Act-Verify (ODAV) agentic framework orchestrating an isolated headless Chromium sandbox through Chrome DevTools Protocol (CDP) screencasting and a resilient Cloud LLM Decision Engine.

### Component Overview
1. **Cloud LLM Decision Engine (`backend/llm_client.py`):**
   - Dual-model routing: Gemini 2.5 Flash as primary; OpenRouter Qwen 2.5 7B as fallback.
   - Deterministic 5-key JSON schema: `{"thought": str, "action": str, "selector": str, "value": str, "feedback": str}`.
   - 3-step rolling scratchpad context pruning.
   - 8-second timeout guard and deterministic local knowledge base fallback.
2. **Playwright Browser Sandbox & CDP Screencast (`backend/browser_sandbox.py`):**
   - Isolated headless Chromium sessions (`--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`, 1280x720).
   - CDP `Page.startScreencast` capturing frames, continuous >=20 FPS MJPEG generator on `/api/stream`.
   - Extraction of up to 25 interactive DOM selectors (`<button>`, `<a>`, `<input>`, `<select>`, `<textarea>`).
   - Browser primitive action dispatcher (`navigate`, `click`, `fill`, `scroll`, `wait`, `finish`).
3. **ODAV Agentic Loop Engine & Host REST API (`backend/app.py`, `backend/odav_engine.py`, `backend/state_manager.py`):**
   - Asynchronous FastAPI server exposing `/api/start-task`, `/api/step`, `/api/stream`, `/api/session-state`, `/api/reset`.
   - ODAV cycle: Observe (extract DOM & URL, compute $S(t)$) -> Decide (LLM query) -> Act (execute action + stream) -> Verify (state mutation $S(t) \neq S(t-1)$ & 2-step stall detection).
   - Hard 8-step budget guard and finish termination gate.
4. **Vernacular Kiosk UI & Web Speech Integration (`frontend/` or `static/`):**
   - Touch-first HTML5 + Tailwind CSS SPA (WCAG AAA, >=48px/64px touch targets).
   - Web Speech API STT and TTS in Marathi (`mr-IN`), Hindi (`hi-IN`), and English (`en-IN`) with Push-to-Talk and phonetic fallbacks.
   - Real-time MJPEG stream display, ODAV audit log, step budget indicator, human checkpoint modal with virtual keypad, and ephemeral data purge.
   - High-fidelity mock Maharashtra citizen public service portals (`/portal/income`, `/portal/satbara`, `/portal/mahadbt`, `/portal/ration`).

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Dual-Model LLM Gateway | Gemini 2.5 Flash primary with OpenRouter Qwen 2.5 7B fallback | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Deterministic Schema Validator | Enforces 5-key JSON contract (`thought`, `action`, `selector`, `value`, `feedback`) | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Context Pruner (Rolling Scratchpad) | Retains goal + last 3 step deltas to maintain low latency & token budget | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Resilient Timeout & Network Fallback | 8-second timeout guard and local deterministic knowledge base | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Isolated Chromium Sandbox | Headless Chromium lifecycle with zero desktop takeover | M2 | ORIGINAL_REQUEST §R2 |
| 6 | Interactive DOM Extractor | Extracts up to 25 interactive elements (`button`, `a`, `input`, `select`, `textarea`) | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Native CDP Screencast Stream | `Page.startScreencast` delivering continuous >= 20 FPS MJPEG on `/api/stream` | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Primitive Action Executor | Dispatches `navigate`, `click`, `fill`, `scroll`, `wait`, `finish` with timeout guards | M2 | ORIGINAL_REQUEST §R2 |
| 9 | State Signature Calculator | Generates deterministic hash $S(t) = \text{SHA256}(\text{url} + \text{DOM})[:16]$ | M3 | ORIGINAL_REQUEST §R3 |
| 10 | State Mutation Auditor | Verifies $S(t) \neq S(t-1)$ to audit progress after action execution | M3 | ORIGINAL_REQUEST §R3 |
| 11 | Two-Step Stall Detector | Detects 2 consecutive identical states ($S(t) == S(t-1)$) to flag stalls | M3 | ORIGINAL_REQUEST §R3 |
| 12 | FastAPI Host REST Endpoints | Implements `/api/start-task`, `/api/step`, `/api/stream`, `/api/session-state`, `/api/reset` | M3 | ORIGINAL_REQUEST §R3 |
| 13 | Hard Step Budget Guard | Maximum 8 iterations per session ceiling | M3 | ORIGINAL_REQUEST §R3 |
| 14 | Finish Termination Gate | Generates application tracking receipt and marks task completed | M3 | ORIGINAL_REQUEST §R3 |
| 15 | Touch-Friendly Rural Kiosk UI | HTML5 + Tailwind CSS SPA, high contrast, large touch targets | M4 | ORIGINAL_REQUEST §R4 |
| 16 | Multi-Lingual Web Speech STT/TTS | Marathi (`mr-IN`), Hindi (`hi-IN`), English (`en-IN`) with Push-to-Talk | M4 | ORIGINAL_REQUEST §R4 |
| 17 | Live MJPEG Viewport Display | Renders `/api/stream` with automatic reconnect and canvas reticle overlay | M4 | ORIGINAL_REQUEST §R4 |
| 18 | Real-Time ODAV Audit Log | Visualizes ODAV phases, current action, thoughts, and state hashes | M4 | ORIGINAL_REQUEST §R4 |
| 19 | Human Checkpoint Modal | Modal for OTP/signature entry with touch virtual numeric keypad | M4 | ORIGINAL_REQUEST §R4 |
| 20 | Ephemeral Data Purge | Immediate memory and session state wipe compliant with DPDP Act 2023 | M4 | ORIGINAL_REQUEST §R4 |
| 21 | High-Fidelity Mock Portals | Maharashtra service portals (`/portal/income`, `/portal/satbara`, `/portal/mahadbt`, `/portal/ration`) | M4 | ORIGINAL_REQUEST §R4 |
| 22 | Comprehensive E2E Verification | Tiers 1-4 automated test suite validating complete citizen workflows | M5 | ORIGINAL_REQUEST §R1-R4 |
| 23 | Adversarial Coverage Hardening | Tier 5 adversarial testing covering edge cases, corrupt inputs, and network failures | M5 | ORIGINAL_REQUEST §R1-R4 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | LLM Decision Engine & Schema Validator | Dual-model gateway (Gemini + Qwen), schema validator, 3-step pruning, fallback engine | none | DONE |
| M2 | Playwright Sandbox & CDP Screencast | Headless Chromium, CDP screencast >=20 FPS, DOM extractor (25 items), action dispatcher | none | DONE |
| M3 | ODAV Loop Engine & FastAPI Backend | Full ODAV cycle, state signature $S(t)$, stall detector, budget guard, `/api/*` endpoints | M1, M2 | DONE |
| M4 | Vernacular Kiosk UI & Web Speech | Touch SPA, Web Speech (mr/hi/en), live stream viewer, audit log, OTP modal, mock portals | M3 | DONE |
| M5 | Final Milestone: E2E Test Pass & Hardening | Pass 100% of E2E tests (Tiers 1-4) and execute Tier 5 adversarial hardening | M1, M2, M3, M4 | DONE |


---

## Interface Contracts

### 1. `backend/llm_client.py` ↔ `backend/odav_engine.py`
```python
def decide_action(
    goal: str,
    history: List[Dict[str, Any]],
    url: str,
    dom_elements: List[Dict[str, Any]],
    language: str = "mr"
) -> Dict[str, str]:
    """
    Returns deterministic dictionary:
    {
        "thought": str,
        "action": "navigate" | "click" | "fill" | "scroll" | "wait" | "finish",
        "selector": str,
        "value": str,
        "feedback": str
    }
    """
```

### 2. `backend/browser_sandbox.py` ↔ `backend/odav_engine.py`
```python
class BrowserSandbox:
    async def initialize(self) -> None: ...
    async def extract_interactive_elements(self) -> Tuple[str, List[Dict[str, Any]]]: ...
    async def execute_action(self, action: str, selector: str, value: str) -> Tuple[bool, str]: ...
    async def get_frame(self) -> bytes: ...
    async def mjpeg_frame_generator(self): ...  # yields bytes
    async def close(self) -> None: ...
```

### 3. `backend/app.py` ↔ Frontend Kiosk Client
- `POST /api/start-task`: `{"task": str, "language": str}` -> `{"status": "started", "session_id": str, "step": 0}`
- `POST /api/step`: `{}` -> `{"step": int, "state_signature": str, "action": dict, "stalled": bool, "status": str}`
- `GET /api/stream`: HTTP 200 `multipart/x-mixed-replace; boundary=frame`
- `GET /api/session-state`: `{"active": bool, "step": int, "max_steps": 8, "task": str, "language": str, "history": list, "last_action": dict, "url": str, "stalled": bool, "finished": bool}`
- `POST /api/reset`: `{"status": "reset", "purged": true}`

---

## Code Layout
```
c:\Users\Praka\OneDrive\Desktop\kiosk\
├── backend/
│   ├── __init__.py
│   ├── app.py                     # FastAPI application & REST routes
│   ├── config.py                  # App configuration & env vars
│   ├── llm_client.py              # Cloud LLM gateway, schema validation & fallbacks
│   ├── browser_sandbox.py         # Playwright Chromium manager & CDP screencaster
│   ├── odav_engine.py             # ODAV cycle coordinator
│   ├── state_manager.py           # Session state store, budget guards, stall detector
│   └── models.py                  # Pydantic models & schemas
├── frontend/                      # Static kiosk application assets
│   ├── index.html                 # Touch-first kiosk UI
│   ├── kiosk.js                   # Web Speech API, stream viewer, state sync
│   └── styles.css                 # Custom high-contrast styles & animations
├── mock_portals/                  # Simulated Maharashtra e-governance portals
│   ├── income.html                # Aaple Sarkar Income Certificate portal
│   ├── satbara.html               # Mahabhulekh 7/12 Land Records portal
│   ├── mahadbt.html               # Farmer Agriculture Subsidy portal
│   └── ration.html                # AePDS Ration Card Services portal
├── tests/
│   ├── test_phase1_schema.py      # M1 unit & schema validation tests
│   ├── test_phase2_sandbox.py     # M2 Playwright & CDP tests
│   ├── test_phase3_odav.py        # M3 ODAV engine & FastAPI endpoints tests
│   ├── test_phase4_kiosk_ui.py    # M4 UI & static portal routes tests
│   └── e2e/                       # E2E Testing Track test suites (Tiers 1-5)
│       ├── test_tier1_feature.py
│       ├── test_tier2_boundary.py
│       ├── test_tier3_pairwise.py
│       ├── test_tier4_workload.py
│       └── test_tier5_adversarial.py
├── PROJECT.md                     # Project master architecture & milestone index
└── TEST_INFRA.md                  # E2E Test infrastructure specification
```
