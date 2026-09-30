# Dispatch for teamwork_preview_worker_m2

- Identity: teamwork_preview_worker
- Role: M2 Worker (Playwright Sandbox & CDP Screencast)
- Working directory: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_worker_m2
- Parent Orchestrator: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_orchestrator_1
- Parent Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2
- Original Request: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
- Project Spec: c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md

## 2026-09-26T08:22:03Z
Assigned working directory: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_worker_m2
Parent: teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2)
Authoritative user request: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
Project specification: c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md

Exclusively Owned Files:
- c:\Users\Praka\OneDrive\Desktop\kiosk\backend\browser_sandbox.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\tests\test_phase2_sandbox.py

Scope & Requirements:
1. Implement backend/browser_sandbox.py providing BrowserSandbox:
   - Isolated headless Chromium sessions without physical desktop takeover (--no-sandbox, --disable-dev-shm-usage, --disable-gpu, --window-size=1280,720).
   - Native CDP screencasting session via page.context().new_cdp_session(page), starting screencast with Page.startScreencast (JPEG quality 60, 1280x720), low-latency frame handling, and immediate Page.screencastFrameAck flow control.
   - Asynchronous MJPEG stream generator (mjpeg_frame_generator) yielding multipart/x-mixed-replace JPEG frames at >= 20 FPS for the /api/stream endpoint.
   - Interactive DOM selector extractor locating and indexing up to 25 interactive elements (<button>, <a>, <input>, <select>, <textarea>) with robust selector hierarchy (#id, [name], text=, tag).
   - State signature computation: deterministic 16-character SHA-256 hash S(t) = SHA256(url + DOM)[:16].
   - Primitive browser actions dispatcher: navigate, click, fill, scroll, wait, finish with safe timeout guards (e.g. 6s selector timeout, 15s navigation) returning Tuple[bool, str].
2. Build and run tests/test_phase2_sandbox.py:
   - Test headless startup, CDP screencast frame emission, >= 20 FPS throughput capability, 25 DOM elements extraction, S(t) signature stability, and all primitive actions.
   - Run tests using Python (vdak-vm\venv\Scripts\python.exe or python).
3. Record progress in progress.md, produce handoff.md, and message your parent with verified test results.
