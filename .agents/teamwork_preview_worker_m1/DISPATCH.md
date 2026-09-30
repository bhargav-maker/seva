## 2026-09-26T08:22:01Z
You are Worker M1 (teamwork_preview_worker).
Your assigned working directory is: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_worker_m1
Your parent is teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2).
You MUST read the authoritative user request at: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md and the project specification at: c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusively Owned Files:
- c:\Users\Praka\OneDrive\Desktop\kiosk\backend\models.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\backend\llm_client.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\tests\test_phase1_schema.py

Scope & Requirements:
1. Implement Pydantic models in backend/models.py:
   - LLMDecision model strictly enforcing deterministic JSON schema: {"thought": str, "action": "navigate"|"click"|"fill"|"scroll"|"wait"|"finish", "selector": str, "value": str, "feedback": str}.
   - Context pruning data structures and session state models.
2. Refactor/complete backend/llm_client.py:
   - Dual-model cloud routing:
     * Primary: Gemini 2.5 Flash via google-genai or direct HTTPS REST endpoint.
     * Secondary fallback: OpenRouter Qwen 2.5 7B (qwen/qwen-2.5-7b-instruct:free) using credentials in vdak-vm/.env.
   - Safe fallback engine: 8-second timeout guard, rate-limit (429) & network error handling without crashing daemon.
   - Deterministic local e-governance fallback database for Maharashtra citizen workflows (Income Certificate, Niradhar Pension, 7/12 Satbara, Ration card) in Marathi (mr), Hindi (hi), and English (en).
   - Context pruning: rolling scratchpad retaining citizen goal and the last 3 step deltas.
3. Verify implementation by running the test suite:
   - Run tests/test_phase1_schema.py using Python (e.g., vdak-vm\venv\Scripts\python.exe tests/test_phase1_schema.py or python tests/test_phase1_schema.py).
   - Ensure all 25 synthetic vernacular prompts pass 100% with zero validation errors.
4. Record your progress in progress.md, produce handoff.md, and message your parent with verified test results.
