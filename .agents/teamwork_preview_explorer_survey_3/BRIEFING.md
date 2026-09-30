# BRIEFING — 2026-09-26T08:26:00Z

## Mission
Map the technical foundations for R4: Vernacular Kiosk UI, Web Speech Integration (mr-IN, hi-IN, en-IN), real-time MJPEG screencast viewport, ODAV audit feed, human checkpoint modals, and realistic mock citizen portals.

## 🔒 My Identity
- Archetype: teamwork_preview_explorer
- Roles: Vernacular Kiosk UI & Web Speech Integration Explorer (R4)
- Working directory: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_explorer_survey_3
- Original parent: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2
- Milestone: Survey Phase Complete

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production code
- Write only to .agents/teamwork_preview_explorer_survey_3/
- Adhere to touch-friendly public terminal ergonomics (Setu Kendra / Gram Panchayat, >= 48px/64px touch targets)
- Native Web Speech API STT/TTS with Marathi (mr-IN), Hindi (hi-IN), English (en-IN) and offline/permission fallbacks
- Low-latency MJPEG streaming display (>= 20 FPS) and real-time ODAV cycle audit visualization
- Ephemeral data purge & privacy guarantees for public shared terminals

## Current Parent
- Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2
- Updated: 2026-09-26T08:26:00Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md` (authoritative project requirements)
  - `backend/llm_client.py` (JSON contracts, GOVERNANCE_SERVICES, vernacular prompts)
  - `backend/sandbox.py` (Playwright sandbox, CDP screencast, PORTAL_TEMPLATES)
  - `tests/test_phase1_schema.py` (25 synthetic citizen prompts in mr-IN, hi-IN, en-IN)
  - `tests/test_phase2_sandbox.py` (CDP screencast FPS and DOM selector assertions)
  - `vdak-host/` and `vdak-vm/` (legacy Gradio and WebSocket screenshot architectures)
- **Key findings**:
  - HTML5 + Tailwind CSS SPA served via FastAPI `StaticFiles` eliminates Gradio latency and provides high accessibility and touch ergonomics.
  - Native `<img>` tag with `src="/api/stream"` natively plays the 20+ FPS MJPEG screencast.
  - Web Speech API provides client-side zero-latency STT and TTS across mr-IN, hi-IN, en-IN with Hindi phonetic fallback for Marathi when needed.
  - Push-to-Talk with mutual exclusion prevents acoustic feedback loops on kiosk hardware.
  - Native `<dialog id="checkpoint-modal">` with on-screen virtual numeric keypad enables keyboardless OTP authentication.
  - Ephemeral data purge on reset or 60s idle adheres to India's DPDP Act 2023.
  - Four realistic mock portals (Income Certificate, 7/12 Land Records, MahaDBT Farmer Subsidy, Ration Card Services) provide complete, deterministic test coverage.
- **Unexplored areas**: None for survey scope. Implementation plan is fully specified.

## Key Decisions Made
- Selected HTML5 + Tailwind CSS SPA layout with master-detail split (62% live viewport, 38% ODAV control/audit).
- Designed touch-friendly on-screen numeric keypad for OTP entry inside the human checkpoint modal.
- Formulated acoustic feedback suppression state machine for Web Speech API.
- Specified 4 realistic Maharashtra governance mock portals.

## Artifact Index
- `c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_explorer_survey_3\progress.md` — Progress tracker and liveness heartbeat
- `c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_explorer_survey_3\survey_report.md` — Comprehensive R4 survey report
- `c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_explorer_survey_3\handoff.md` — 5-component handoff report
