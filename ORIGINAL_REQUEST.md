# Original User Request

## 2026-10-02T12:10:03Z

Build, harden, and verify the production-grade SEVA AI Autonomous Public Service Kiosk Engine, unifying LiveKit cloud real-time voice, expanded Playwright government portal automation (Mahabhulekh, Aaple Sarkar, PM-Kisan, Ration), dual-delivery outputs (ESC/POS thermal printer and WhatsApp digital PDF), and continuous regression/stress benchmarking under strict hardware constraints (<280MB RAM).

Working directory: c:\Users\Praka\OneDrive\Desktop\kiosk
Integrity mode: development

## Requirements

### R1. Complete End-to-End Voice & Tool Kiosk Architecture
Integrate and harden the FastMCP tool backend with LiveKit real-time voice streaming (Gemini 2.5 Flash / Indic voice models), 1-second full-body presence dwell greeting, and 15-second DPDP privacy walk-away purge. Support Devanagari/Indic number parsing ("पाच दोन आठ तीन" -> 5283) and keypad fallback.

### R2. Comprehensive Government Portal & Browser Automation Suite
Automate end-to-end citizen service workflows via visible Google Chrome (right-half split screen) and headless modes for Mahabhulekh Satbara 7/12, Aaple Sarkar income certificates, PM-Kisan installment verification, and Ration card status. Implement deterministic arithmetic captcha solving (100% accuracy) and the mandatory green Safety Review Gate (#00cc44) pause before submission.

### R3. Dual-Channel Output Delivery & Offline Resilience
Spool clean ESC/POS thermal receipts and dispatch digital PDFs to citizen WhatsApp numbers for all completed transactions. Provide offline SQLite scheme search and local encrypted transaction queueing that automatically synchronizes upon network restoration.

### R4. Automated Continuous Testing & Benchmark Suite
Provide an automated continuous test daemon and scheduled stress suite verifying all citizen scenarios, memory leak prevention (strictly <280MB RAM across all processes), and zero emoji invariant compliance.

### R5. Controlled Infrastructure & Resource Isolation
Operate within a maximum of 1 concurrent browser instance enforced via a global mutex lock. Enforce 0% GPU load (no Three.js, WebGL, or heavy local neural models) to guarantee stability on legacy hardware (HP Elite 7100, 3.7GB RAM).

## Verification Resources
- Authentic citizen records: friday_core/friday/data/real_citizen_records.json
- Real-world task validation suite: tests/test_real_world_tasks.py
- Core invariant verification suite: tests/test_seva_engine.py

## Acceptance Criteria

### Kiosk Voice & Vision Pipeline
- [ ] 1-second dwell triggers native regional greeting based on GPS coordinates
- [ ] Indic number parser normalizes spoken Devanagari digits to ASCII numerals
- [ ] 15-second absence triggers DPDP privacy purge, clearing session data and open tabs

### Browser Portal Automation & Review Gate
- [ ] Chrome launches reliably in split-screen position (960x1080) without event-loop hangs
- [ ] Glowing orange borders (#ff5500) highlight active fields with human typing cadence
- [ ] Arithmetic captcha expressions (including Devanagari numbers) are solved accurately
- [ ] Form pauses and highlights green (#00cc44) at the Safety Review Gate before submission

### Delivery & Hardware Invariants
- [ ] ESC/POS thermal paper receipt spool files generated in friday_core/friday/receipts/
- [ ] Digital receipt dispatch logged for WhatsApp delivery
- [ ] Total system process RSS strictly under 280MB RAM ceiling
- [ ] Zero emoji characters present across all source files, documentation, and console output
- [ ] All 25 unit and real-world task tests pass with 0 failures
