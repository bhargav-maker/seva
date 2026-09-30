# Original User Request

## 2026-09-26T08:08:41Z

Build "SEVA AI", a voice-first, vernacular digital kiosk platform bridging the digital divide for citizen public services in rural India (Setu Kendras, Gram Panchayats). The system implements an API-driven browser orchestration architecture running an Agentic Loop Engine strictly adhering to the Observe-Decide-Act-Verify (ODAV) framework.

Working directory: c:\Users\Praka\OneDrive\Desktop\kiosk
Integrity mode: development

## Requirements

### R1. Cloud LLM API Decision Engine & Schema Validator
- Route citizen requests and extracted browser DOM state to LLM API (Gemini 2.5 Flash / OpenRouter Qwen 2.5 7B) with deterministic JSON contract: {"thought": str, "action": "navigate"|"click"|"fill"|"scroll"|"wait"|"finish", "selector": str, "value": str, "feedback": str}.
- Context pruning: retain only the primary goal and the last 3 step deltas (rolling scratchpad).
- Safe fallback engine handling timeouts (>8s) or rate limits without terminating the kiosk daemon.

### R2. Playwright Browser Sandbox & CDP Screencast Stream
- Run isolated, headless Chromium sessions without physical desktop takeover.
- Extract up to 25 interactive DOM selectors (<button>, <a>, <input>, <select>).
- Implement native Chrome DevTools Protocol (CDP) screencasting over an HTTP MJPEG stream at >= 20 FPS on /api/stream.
- Execute primitive browser actions: navigate, click, fill, scroll, wait, finish.

### R3. ODAV Agentic Loop Engine & Host REST API
- Fast, asynchronous FastAPI backend exposing /api/start-task, /api/step, /api/stream, /api/session-state, and /api/reset.
- Implement ODAV loop cycle:
  - Observe: Capture active URL and interactive DOM elements, compute state signature S(t).
  - Decide: Query LLM with pruned context for single next action.
  - Act: Dispatch action to Playwright and stream frame.
  - Verify: Audit state mutation S(t) != S(t-1); detect stalls across 2 consecutive identical states.
- Loop Guards: Hard step budget (maximum 8 iterations per session) and termination gate on action="finish".

### R4. Vernacular Kiosk UI & Web Speech Integration
- Touch-friendly HTML5 + Tailwind CSS kiosk interface designed for physical public terminals.
- Native multi-lingual Web Speech API voice input (STT) and conversational audio feedback (TTS) in Marathi (mr-IN), Hindi (hi-IN), and English (en-IN).
- Live viewport display rendering the 20+ FPS MJPEG stream.
- Real-time audit log, step budget indicator, human checkpoint modal (OTP/signature), and ephemeral data purge.
