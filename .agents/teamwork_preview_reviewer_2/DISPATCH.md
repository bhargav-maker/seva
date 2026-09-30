# Dispatch for teamwork_preview_reviewer_2

- Identity: teamwork_preview_reviewer
- Role: Test & Protocol Reviewer
- Working directory: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_reviewer_2
- Parent Orchestrator: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_orchestrator_1
- Parent Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2
- Original Request: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
- Project Spec: c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md
- Test Infra Spec: c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_INFRA.md
- Test Ready Report: c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_READY.md

## 2026-09-26T09:55:10Z

You are Reviewer 2 (teamwork_preview_reviewer).
Your assigned working directory is: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_reviewer_2
Your parent is teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2).
You MUST read:
- c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_INFRA.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_READY.md
before starting work.

Mission:
Conduct an independent review of the Frontend Kiosk UI, Vernacular Voice, Mock Portals, and Privacy Compliance:
1. Examine correctness, completeness, and usability of:
   - frontend/index.html, kiosk.js, styles.css (touch-friendly UI, WCAG AAA contrast, min 48px/64px buttons, live MJPEG viewport display with reticle overlay, audit log, budget meter, virtual numeric keypad dialog modal)
   - Vernacular speech integration: Web Speech API STT & TTS in Marathi (mr-IN), Hindi (hi-IN), English (en-IN), Push-to-Talk mutual exclusion, phonetic fallbacks
   - mock_portals/ (income.html, satbara.html, mahadbt.html, ration.html)
   - Ephemeral data purge: instant volatile wipe compliant with DPDP Act 2023 on /api/reset
2. Verify tests: run pytest tests/test_phase4_kiosk_ui.py and tests/e2e/test_tier4_workload.py.
3. Record findings and provide an explicit review verdict (APPROVE or REQUEST_CHANGES) in handoff.md, and message your parent.
