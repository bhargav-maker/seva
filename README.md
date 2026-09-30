# SEVA AI (Vernacular Digital Assistance Kiosk)

[![Architecture: ODAV Loop](https://img.shields.io/badge/Architecture-ODAV%20Loop-amber.svg)](https://github.com/bhargav-maker/seva)
[![Engine: Playwright CDP](https://img.shields.io/badge/Engine-Playwright%20CDP-blue.svg)](https://github.com/bhargav-maker/seva)
[![Brain: Qwen 2.5 7B](https://img.shields.io/badge/Brain-Qwen%202.5%207B-purple.svg)](https://github.com/bhargav-maker/seva)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**SEVA AI** is an autonomous, voice-first, vernacular digital assistance kiosk platform engineered for rural Indian citizen public service centers (Gram Panchayats, Setu Kendras, CSCs).

A citizen speaks in conversational **Marathi (`mr-IN`)**, **Hindi (`hi-IN`)**, or **English (`en-IN`)**, and SEVA AI autonomously executes end-to-end web transactions on government public portals via sandboxed browser automation while streaming real-time visual verification (>=20 FPS MJPEG) and localized voice confirmations.

---

## 🏛️ System Architecture

SEVA AI rejects linear procedural scripts in favor of an **Observe–Decide–Act–Verify (ODAV)** closed-circuit state engine:

```
[ Citizen Voice / Goal ]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│  SEVA AI ODAV AGENT LOOP                               │
│                                                        │
│  1. OBSERVE : Filter top 25 interactive DOM nodes      │
│  2. DECIDE  : Brain (Qwen 2.5 7B) picks single action  │
│  3. ACT     : Playwright executes & streams CDP frames │
│  4. VERIFY  : Audit state signature S(t) & stalls      │
│               • Mutated & t < 8  ──► Proceed next step │
│               • Action == finish ──► Breakout & Exit   │
│               • Unchanged x 2    ──► Stall Recovery    │
└────────────────────────────────────────────────────────┘
```

---

## 🛡️ Invariant Loop Guardrails

1. **Step Budget Ceiling ($N = 8$):** Every session has a strict budget ceiling of 8 iterations to prevent infinite loops.
2. **Context Compaction ($k = 3$):** Never serializes full HTML trees. Rolling window carries only Original Goal + Last 3 Step Deltas + Top 25 Filtered DOM Nodes.
3. **Stall Recovery Gate:** Tracks state signature $S(t) = \text{SHA256}(\text{url} + \text{title} + \text{DOM})[:16]$. If $S(t) == S(t-1)$ across 2 consecutive steps, recovery scroll or clarification is triggered.
4. **Strict JSON Schema Contract:**
   ```json
   {
     "thought": "Technical deduction from observed DOM nodes",
     "intent": "search_service | fill_form | navigate_menu | click_action | finish",
     "action": "navigate | click | fill | scroll | wait | finish | fail",
     "selector": "CSS selector or element anchor",
     "value": "Input value or navigation URL",
     "feedback": "Localized conversational audio confirmation"
   }
   ```
5. **Ephemeral Privacy Purge:** All session memory and browser cookies are wiped upon session completion or reset (DPDP Act 2023 compliant).

---

## 📁 Repository Structure

```text
seva/
├── standalone_seva.py               # Complete single-file runnable kiosk platform
├── run_seva.py                      # Multi-process kiosk runner
├── vdak-host/                       # Edge Controller Runtime
│   ├── app.py                       # FastAPI entrypoint & REST routes
│   ├── config.py                    # Server, model, and timeout configuration
│   ├── bridge/
│   │   ├── vm_client.py             # OpenRouter Qwen 2.5 7B client & fallback engine
│   │   └── state_manager.py         # State signature, stall detector & k=3 compaction
│   ├── voice/
│   │   ├── asr.py                   # Faster-Whisper + Silero VAD (anti-hallucination)
│   │   └── tts.py                   # Offline/Native speech synthesizer
│   └── frontend/
│       ├── index.html               # Touch-friendly kiosk UI
│       ├── style.css                # Accessible high-contrast styling
│       └── app.js                   # Web Speech API & ODAV state polling
├── vdak-vm/                         # Sandboxed Browser Execution
│   ├── browser_controller.py        # Playwright Chromium sandbox & CDP screencaster
│   └── agent_loop.py                # Closed-circuit ODAV execution engine
├── mock_portals/                    # High-fidelity simulated Maharashtra portals
│   ├── income.html                  # Aaple Sarkar Income Certificate
│   ├── satbara.html                 # Mahabhulekh 7/12 Land Records
│   ├── mahadbt.html                 # Farmer Crop Subsidy
│   └── ration.html                  # AePDS Ration Services
├── tests/
│   └── test_prd_contracts.py        # Automated ODAV invariant validation tests
├── ALL_CODE.md                      # Consolidated master code documentation
├── GEMINI.md                        # Persistent Autonomous Loop Engine directives
└── AGENTS.md                        # System agent rules & contracts
```

---

## 🚀 Quick Start

### 1. Unified Standalone Launcher
Run the entire platform (FastAPI server, Playwright CDP stream, and Touch UI) in a single command:

```bash
# 1. Install dependencies
pip install fastapi uvicorn playwright httpx pydantic pydantic-settings

# 2. Install Playwright browser
playwright install chromium

# 3. (Optional) Set your OpenRouter API key for cloud LLM reasoning
export OPENROUTER_API_KEY="your_openrouter_api_key"

# 4. Start the Standalone Kiosk
python standalone_seva.py --port 8000
```
Open **`http://localhost:8000`** in your browser.

---

### 2. Run Deterministic Invariant Tests
Verify that all 6-key JSON schema constraints, $k=3$ compaction, 2-step stall detectors, and $N=8$ budget limits pass 100%:

```bash
python standalone_seva.py --test
```

Or using pytest:
```bash
python -m pytest tests/test_prd_contracts.py -v
```

---

## 📡 REST API Specification

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/start-task` | `POST` | Initializes citizen session with goal and vernacular language |
| `/api/step` | `POST` | Executes a single discrete ODAV state cycle |
| `/api/stream` | `GET` | Multipart HTTP MJPEG screencast stream at $\ge 20$ FPS |
| `/api/session-state`| `GET` | Queries active session status, step count, and budget |
| `/api/reset` | `POST` | Purges ephemeral session state and navigates to blank page |

---

## 📜 Supported Public Welfare Portals

* **Aaple Sarkar:** Income Certificate (*उत्पन्नाचा दाखला*), Domicile, Caste Certificate
* **Mahabhulekh:** 7/12 & 8A Land Records (*७/१२ उतारा*)
* **MahaDBT:** Farmer Agriculture Subsidies (*शेतकरी योजना*)
* **AePDS Maharashtra:** Ration Card Services (*रेशन कार्ड*)

---

## ⚖️ License
MIT License. Built for public digital empowerment.
