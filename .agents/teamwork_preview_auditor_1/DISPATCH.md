# Dispatch for teamwork_preview_auditor_1

- Identity: teamwork_preview_auditor
- Role: Forensic Integrity Auditor
- Working directory: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_auditor_1
- Parent Orchestrator: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_orchestrator_1
- Parent Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2
- Original Request: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
- Project Spec: c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md
- Test Infra Spec: c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_INFRA.md
- Test Ready Report: c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_READY.md

## 2026-09-26T09:55:23Z
You are Forensic Auditor 1 (teamwork_preview_auditor).
Your assigned working directory is: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_auditor_1
Your parent is teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2).
You MUST read:
- c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_INFRA.md
- c:\Users\Praka\OneDrive\Desktop\kiosk\TEST_READY.md
before starting work.

Mission:
Perform a strict, independent Forensic Integrity Audit across the entire SEVA AI codebase and test suite:
1. Check for Cheating / Facades / Dummy Implementations:
   - Verify whether source code in backend/ contains hardcoded test answers, mock passes, or fake logic designed to fool tests.
   - Verify whether tests in tests/ (both unit and e2e/) contain fake assertions like `assert True`, bypassed checks, or suppressed failures.
   - Verify that Playwright BrowserSandbox, CDP screencasting, ODAV engine, and LLM gateway are authentic and fully operational.
2. Verify Privacy & Compliance:
   - Verify DPDP Act 2023 compliance: confirm that reset purges all volatile citizen data, history, and browser sessions.
3. Render an authoritative binary verdict:
   - Output either **CLEAN** or **INTEGRITY VIOLATION** with detailed supporting evidence.
4. Record your full audit findings in handoff.md, and message your parent immediately with your verdict.

