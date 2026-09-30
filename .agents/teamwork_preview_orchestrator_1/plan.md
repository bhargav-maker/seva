# SEVA AI Kiosk Project Execution Plan

## Objective
Design, build, verify, and deliver SEVA AI: a voice-first, vernacular digital kiosk platform for citizen public services in rural India (Setu Kendras, Gram Panchayats).

## Requirements Coverage
- **R1: Cloud LLM API Decision Engine & Schema Validator**
  - Gemini 2.5 Flash / OpenRouter Qwen 2.5 7B fallback
  - Deterministic JSON contract: `{"thought": str, "action": "navigate"|"click"|"fill"|"scroll"|"wait"|"finish", "selector": str, "value": str, "feedback": str}`
  - Context pruning: retain primary goal + last 3 step deltas (rolling scratchpad)
  - Safe fallback handling timeouts (>8s) and rate limits without daemon termination
- **R2: Playwright Browser Sandbox & CDP Screencast Stream**
  - Isolated headless Chromium sessions without physical desktop takeover
  - Interactive DOM selector extraction (up to 25 buttons, links, inputs, selects)
  - Native Chrome DevTools Protocol (CDP) screencasting over HTTP MJPEG at >= 20 FPS on `/api/stream`
  - Browser primitive actions execution: navigate, click, fill, scroll, wait, finish
- **R3: ODAV Agentic Loop Engine & Host REST API**
  - Asynchronous FastAPI backend exposing `/api/start-task`, `/api/step`, `/api/stream`, `/api/session-state`, `/api/reset`
  - Observe-Decide-Act-Verify (ODAV) loop cycle with state signature S(t) comparison
  - Stall detection across 2 consecutive identical states
  - Loop guards: hard step budget (max 8 iterations per session) and action="finish" gate
- **R4: Vernacular Kiosk UI & Web Speech Integration**
  - Touch-friendly HTML5 + Tailwind CSS kiosk UI
  - Multi-lingual Web Speech API STT and TTS in Marathi (mr-IN), Hindi (hi-IN), and English (en-IN)
  - Live viewport display rendering the 20+ FPS MJPEG stream
  - Real-time audit log, step budget indicator, human checkpoint modal (OTP/signature), and ephemeral data purge

## Methodology
- Top-Level Orchestrator uses the Project Pattern.
- Phase 0: Survey full scope with 3 parallel Explorers.
- Phase 1: Synthesize findings into `PROJECT.md` (Architecture, Feature Inventory, Milestones, Interface Contracts, Code Layout).
- Phase 2: Dual Track execution (Implementation Sub-orchestrators for milestones M1..Mn, and E2E Testing Track).
- Phase 3: Final milestone E2E test verification (Tiers 1-4).
- Phase 4: Tier 5 adversarial testing & hardening.
- Phase 5: Handoff and Sentinel completion report.
