# Dispatch for teamwork_preview_test_writer_e2e

- Identity: teamwork_preview_test_writer
- Role: E2E Test Suite Writer
- Working directory: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_test_writer_e2e
- Parent Orchestrator: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_orchestrator_1
- Parent Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2
- Original Request: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
- Project Spec: c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md
- Test Infra Spec: c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_INFRA.md

## 2026-09-26T08:22:04Z
You are the E2E Test Writer (teamwork_preview_test_writer).
Your assigned working directory is: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_test_writer_e2e
Your parent is teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2).
You MUST read:
- c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_INFRA.md
before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All test cases and assertions must be genuine and opaque-box. DO NOT hardcode artificial passes or mock out core functionality so that invalid implementations would falsely pass. A teamwork_preview_auditor will independently verify test suite integrity.

Exclusively Owned Files:
- c:\Users\Praka\OneDrive\Desktop\kiosk\tests\e2e\__init__.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\tests\e2e\test_tier1_feature.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\tests\e2e\test_tier2_boundary.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\tests\e2e\test_tier3_pairwise.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\tests\e2e\test_tier4_workload.py
- c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_READY.md

Scope & Requirements:
1. Develop the comprehensive E2E test suite according to TEST_INFRA.md:
   - Tier 1: Feature Coverage (>=5 test cases per feature for R1 through R4).
   - Tier 2: Boundary & Corner Cases (>=5 test cases per feature: limits, empty strings, null values, timeouts, network disconnects, step budget ceilings).
   - Tier 3: Cross-Feature Combinations (pairwise interaction testing: LLM pruning + CDP streaming, stall detection + human OTP modal, language switching + STT/TTS).
   - Tier 4: Real-World Application Scenarios (end-to-end citizen workflows: Income certificate application, 7/12 Land record query, Farmer subsidy application, Ration card lookup, Mid-session citizen cancellation with ephemeral data purge).
2. Author TEST_READY.md upon completing the test suites:
   - Include test runner command, expected exit codes, and coverage matrix across Tiers 1-4.
3. Record progress in progress.md, write handoff.md, and message your parent when TEST_READY.md is published.
