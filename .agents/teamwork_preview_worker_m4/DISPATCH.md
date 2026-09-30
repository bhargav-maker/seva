# Dispatch for teamwork_preview_worker_m4

- Identity: teamwork_preview_worker
- Role: M4 Worker (Vernacular Kiosk UI & Web Speech)
- Working directory: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_worker_m4
- Parent Orchestrator: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_orchestrator_1
- Parent Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2
- Original Request: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
- Project Spec: c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md
- Test Infra Spec: c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_INFRA.md

## 2026-09-26T08:30:54Z
You are Worker M4 (teamwork_preview_worker).
Your assigned working directory is: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_worker_m4
Your parent is teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2).
You MUST read the authoritative user request at: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md and the project specification at: c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusively Owned Files:
- c:\Users\Praka\OneDrive\Desktop\kiosk\frontend\index.html
- c:\Users\Praka\OneDrive\Desktop\kiosk\frontend\kiosk.js
- c:\Users\Praka\OneDrive\Desktop\kiosk\frontend\styles.css
- c:\Users\Praka\OneDrive\Desktop\kiosk\mock_portals\income.html
- c:\Users\Praka\OneDrive\Desktop\kiosk\mock_portals\satbara.html
- c:\Users\Praka\OneDrive\Desktop\kiosk\mock_portals\mahadbt.html
- c:\Users\Praka\OneDrive\Desktop\kiosk\mock_portals\ration.html
- c:\Users\Praka\OneDrive\Desktop\kiosk\tests\test_phase4_kiosk_ui.py

Scope & Requirements:
1. Implement touch-friendly rural kiosk UI in frontend/:
   - Touch-first HTML5 + Tailwind CSS SPA optimized for rural kiosk terminals (Gram Panchayat / Setu Kendra) with WCAG AAA high contrast and large touch targets (min 48px, primary 64px-80px).
   - Viewport display rendering /api/stream with auto-reconnection and canvas reticle overlay.
   - Native Web Speech API integration: SpeechRecognition (STT) and SpeechSynthesis (TTS) in Marathi (mr-IN), Hindi (hi-IN), and English (en-IN). Push-to-Talk with mutual exclusion, phonetic fallbacks, and quick touch-chip prompts.
   - Real-time ODAV audit feed displaying OBSERVE, DECIDE, ACT, and VERIFY phases, thought, action, and state signature hashes.
   - Step budget visual indicator (1/8 steps meter).
   - Human Checkpoint dialog modal with on-screen virtual numeric keypad (0-9) for keyboardless OTP / biometric / signature entry.
   - Ephemeral data purge button triggering immediate session wipe and /api/reset call.
2. Implement 4 high-fidelity mock Maharashtra citizen public service portals in mock_portals/:
   - income.html (Aaple Sarkar: Tahsildar Income Certificate)
   - satbara.html (Mahabhulekh: 7/12 Satbara Land Records)
   - mahadbt.html (MahaDBT: Farmer Agriculture Subsidy)
   - ration.html (AePDS: Food & Civil Supplies Ration Card Services)
3. Implement and execute tests/test_phase4_kiosk_ui.py:
   - Validate HTML structure, touch target sizing, multi-lingual prompt matrices, mock portal routes, and UI synchronization.
   - Run tests using Python and ensure 100% pass.
4. Record progress in progress.md, create handoff.md, and message your parent with verified test results.
