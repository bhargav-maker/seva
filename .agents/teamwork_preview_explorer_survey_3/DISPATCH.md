# Dispatch for teamwork_preview_explorer_survey_3

- Identity: teamwork_preview_explorer
- Role: Vernacular Kiosk UI & Audio Explorer
- Working directory: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_explorer_survey_3
- Parent Orchestrator: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_orchestrator_1
- Parent Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2
- Original Request: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md

## 2026-09-26T08:12:34Z
You are a Survey Explorer (teamwork_preview_explorer).
Your assigned working directory is: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_explorer_survey_3
Your parent is teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2).
You MUST read the authoritative user request at: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\ORIGINAL_REQUEST.md before starting work.

Mission:
Map the technical foundations for R4: Vernacular Kiosk UI & Web Speech Integration.
1. Investigate the Frontend Kiosk UI architecture:
   - Touch-friendly HTML5 + Tailwind CSS interface designed for physical public terminals in rural India (Setu Kendra / Gram Panchayat).
   - High accessibility, high contrast, large touch targets (min 48px/64px), intuitive visual hierarchy.
   - Live viewport component for rendering the >= 20 FPS MJPEG stream from `/api/stream`.
   - Real-time audit log displaying current step, thought, action, and ODAV status.
   - Step budget indicator (e.g. 1/8, visual progress meter).
   - Human checkpoint modal (for sensitive steps like OTP entry, biometric, signature).
   - Ephemeral data purge (session reset button, automatic cleanup on completion/reset).
2. Investigate Vernacular Voice & Audio:
   - Web Speech API SpeechRecognition (STT) and SpeechSynthesis (TTS).
   - Support for Marathi (mr-IN), Hindi (hi-IN), and English (en-IN).
   - Audio feedback prompts, fallback handling when Web Speech is unavailable or permissions are denied.
3. Investigate Demo / Mock Citizen Portals:
   - Design realistic rural citizen public service mock portals (e.g. Mahadbt / Ration Card Services / 7/12 Land Records / Income Certificate) that can run locally or in sandbox for robust end-to-end demonstrations.

Deliverables:
- Initialize your progress.md and BRIEFING.md in c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_explorer_survey_3
- Write a comprehensive findings report to: c:\Users\Praka\OneDrive\Desktop\kiosk\.agents\teamwork_preview_explorer_survey_3\survey_report.md
- Write handoff.md in your directory.
- Send a message to your parent (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2) summarizing your findings.
