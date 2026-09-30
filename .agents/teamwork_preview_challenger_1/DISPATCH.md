## 2026-09-26T09:55:11Z
You are Challenger 1 (teamwork_preview_challenger).
Your assigned working directory is: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_challenger_1
Your parent is teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2).
You MUST read:
- c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_INFRA.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_READY.md
before starting work.

Mission:
Adversarially challenge and stress-test the Backend & Sandbox components:
1. Empirically verify:
   - LLM schema validation under corrupt/adversarial JSON payloads, extra keys, missing keys, invalid actions.
   - Context pruning under extreme history lengths (0 steps, 1 step, 3 steps, 1,000 steps).
   - Timeout and rate-limit fallbacks: verify behavior when network times out or returns HTTP 429/500/503.
   - BrowserSandbox: rapid concurrent frame requests from mjpeg_frame_generator, invalid selectors, actions on non-existent elements, navigation to unreachable URLs.
2. Formulate adversarial test assertions.
3. Record results and empirical verdict (APPROVE or REQUEST_CHANGES) in handoff.md, and message your parent.
