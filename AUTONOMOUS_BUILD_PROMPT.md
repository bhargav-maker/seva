# MISSION DIRECTIVE: AUTONOMOUS END-TO-END BUILD OF SEVA AI KIOSK ENGINE

You are operating as the Lead Autonomous Systems Engineer. Your objective is to build, configure, integrate, and verify the complete **SEVA AI (सेवा डिजिटल सहाय्यक)** public service kiosk engine on this physical machine.

---

### 1. UNCONDITIONAL AUTHORIZATION & OPERATING PERMISSIONS
- **Full Autonomous Authority:** You have 100% unconditional permission to execute all steps independently from start to finish. Do NOT stop to ask for confirmation or intermediate approvals. Self-heal and resolve any errors autonomously.
- **System & Browser Permissions:** You have full authority to execute shell commands, install Python packages/runtimes, create/edit files, launch headless or visible browsers, control desktop software, and use browser automation to sign in to necessary developer accounts (e.g., LiveKit Cloud, OpenRouter, Google AI Studio) using the user's active session.
- **Hardware Environment:** 
  - Physical Host: HP Elite 7100 Microtower (Intel Core i3 540 @ 3.07GHz, 3.7GB RAM, ~340MB Free RAM, Legacy Intel HD Graphics, Windows 10 Bare-Metal).
  - Target Deployments: (1) Visible Desktop PC Demonstration Mode (`headless=False`), and (2) Production Screenless Standalone Appliance on Raspberry Pi (`headless=True`).
  - Strict Memory Cap: Total RAM across all processes must remain strictly under 280MB. Zero 3D Three.js, WebGL, or heavy local neural network bloat.

---

### 2. PRIMARY SPECIFICATIONS & SOURCES OF TRUTH
Before writing code, inspect and strictly adhere to all architectural contracts documented in:
1. `c:\Users\Praka\OneDrive\Desktop\kiosk\MASTER_PRD.md` (Authoritative Master PRD)
2. `c:\Users\Praka\OneDrive\Desktop\kiosk\PROJECT.md` (Component & FastMCP Tool Contracts)
3. `c:\Users\Praka\OneDrive\Desktop\kiosk\AGENTS.md` (Operational Invariants & Verification Loop)
4. `c:\Users\Praka\OneDrive\Desktop\kiosk\GEMINI.md` (Hardware Guardrails)

---

### 3. CORE ARCHITECTURE & SYSTEM FOUNDATION
The system MUST NOT be built as a fragmented patchwork of random libraries. It must be built directly upon:
👉 **Base Engine:** `https://github.com/SAGAR-TAMANG/friday-tony-stark-demo` (All-in-One FastMCP + LiveKit)

#### Key Architectural Pillars to Implement:
1. **LiveKit Real-Time Multilingual Voice Pipeline:**
   - Configure real-time voice streaming with Gemini 2.5 Flash / OpenRouter and Indic speech models.
   - Set up LiveKit credentials automatically (sign in via browser if required).
2. **FastMCP Server Tool Registry:**
   - Register standardized `@mcp.tool` endpoints inside the Friday backend:
     - `open_government_portal`: Playwright-driven visible Google Chrome (`headless=False`) with glowing orange reticles (`outline: 4px solid #ff5500`), smooth auto-scroll, 30ms human typing cadence, and arithmetic captcha solver.
     - `control_mobile_app`: Hybrid execution for Android-only apps like *e-Pik Pahani* (Direct REST API calls + USB ADB phone bridge).
     - `print_and_send_document`: Sends ESC/POS commands to thermal printer (`win32print`) and dispatches PDF copies via WhatsApp.
     - `query_offline_schemes`: Resolves scheme eligibility from an offline local SQLite database.
3. **Proactive Vision Presence Detection:**
   - Lightweight webcam detector (<15MB RAM) with a **1-second dwell trigger** that filters out passers-by and proactively speaks: *"Namaste! Welcome to Gram Panchayat digital assistant. How can I help you?"*
4. **GPS Regional Language Greeting & Dynamic Switching:**
   - Reads location coordinates on boot to greet in the native state language (Marathi in MH, Gujarati in GJ, Kannada in KA, Tamil in TN, Hindi in North India, etc.) with real-time switching across all 22 official Indian languages.
5. **Split-Screen Desktop Demonstration Layout:**
   - Left 50% of screen: Minimalist Cyberpunk Voice HUD (4-state audio ring: `STANDBY` $\to$ `LISTENING` $\to$ `THINKING` $\to$ `SPEAKING`, language pill, live step progress).
   - Right 50% of screen: Visible Google Chrome performing live portal automation.
6. **Multimodal Authentication:**
   - Voice-first Devanagari/Indic number parsing (`"पाच दोन आठ तीन"` $\to$ `5283`), keypad fallback for noisy environments, and USB fingerprint scanner support.
7. **Mandatory Safety Review Gate (DPDP Act Compliance):**
   - Pauses before clicking final "Submit" or "Pay", highlights green (`#00cc44`), speaks a verbal summary in the citizen's language, and requires spoken confirmation (*"Yes / Confirm"*).
8. **Offline Resilience & Request Queuing:**
   - Answers scheme questions offline; securely queues transactional requests locally and auto-executes + sends to WhatsApp when internet restores.
9. **15-Second Walk-Away Privacy Purge:**
   - Automatically wipes sensitive data (Aadhaar, OTP, land records) from screen and memory if the citizen steps away for 15+ seconds.

---

### 4. EXECUTION ROADMAP
1. **Repository Setup:** Clone `https://github.com/SAGAR-TAMANG/friday-tony-stark-demo.git` into the kiosk project structure.
2. **Environment & Dependencies:** Set up Python virtual environment (`uv` or `venv`), install requirements (`playwright`, `livekit-agents`, `fastmcp`, `opencv-python-headless`, `pywin32`), and run `playwright install chromium`.
3. **Credentials Integration:** Automatically configure `.env` with LiveKit, Gemini, and OpenRouter API credentials.
4. **Implement Kiosk FastMCP Tools:** Code and plug in `portal_tool.py`, `mobile_tool.py`, `printer_tool.py`, `offline_tool.py`, and `presence_detector.py`.
5. **Build Lightweight Front-End HUD:** Pure HTML5/CSS/SVG (<25MB RAM, 0% GPU) connecting via WebSocket to Friday.
6. **Launch Scripts:** Create clean ASCII batch files (`run_seva_kiosk.bat` and `run_seva_cli.bat`) with zero unescaped characters.
7. **Verification & Proof of Correctness:**
   - Execute deterministic test suites verifying intent routing (queries speak without browser; transactions visibly launch Chrome).
   - Verify captcha resolution and memory ceiling compliance (<280MB RAM).

Proceed immediately with step 1 and execute the complete implementation autonomously.
