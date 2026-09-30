## 2026-09-26T08:30:53Z
You are Worker M3 (teamwork_preview_worker).
Your assigned working directory is: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_worker_m3
Your parent is teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2).
You MUST read the authoritative user request at: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md and the project specification at: c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusively Owned Files:
- c:\Users\Praka\OneDrive\Desktop\kiosk\backend\app.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\backend\odav_engine.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\backend\state_manager.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\backend\config.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\tests\test_phase3_odav.py

Scope & Requirements:
1. Implement backend/state_manager.py:
   - SessionStateManager managing active task, language, step count (up to 8), history, state signature history, stall detector, and ephemeral data purge.
   - Hard step budget guard: maximum 8 iterations per session.
2. Implement backend/odav_engine.py:
   - Coordinate the Observe-Decide-Act-Verify (ODAV) loop cycle:
     * Observe: inspect browser state via browser_sandbox, capture URL and up to 25 interactive DOM elements, compute state signature S(t) = SHA256(url + DOM)[:16].
     * Decide: query llm_client.decide_action(...) with pruned context (last 3 step deltas) and language.
     * Act: dispatch action via browser_sandbox.execute_action(action, selector, value).
     * Verify: audit state mutation S(t) != S(t-1); detect stalls across 2 consecutive identical states, set stalled=True.
     * Handle termination gates: action="finish" (mark completed, generate receipt SEVA-YYYYMMDD-XXXXX) or step >= 8 (mark budget_exceeded).
3. Implement backend/app.py (FastAPI):
   - Endpoints:
     * POST /api/start-task: JSON {"task": str, "language": str} -> initialize session & sandbox, return session metadata.
     * POST /api/step: execute single ODAV cycle -> return step, state_signature, action, stalled, status.
     * GET /api/stream: return StreamingResponse with multipart/x-mixed-replace MJPEG stream from browser_sandbox.mjpeg_frame_generator() at >= 20 FPS.
     * GET /api/session-state: return current session state, step budget, history, and status.
     * POST /api/reset: terminate browser, purge all session data (DPDP Act compliance), return reset confirmation.
     * Static mounts for frontend and mock portals.
4. Implement and run tests/test_phase3_odav.py:
   - Test all endpoints, ODAV step cycle, stall detection, budget guard, and reset purge.
   - Run tests using Python and ensure 100% pass.
5. Record progress in progress.md, create handoff.md, and message your parent with verified test results.
