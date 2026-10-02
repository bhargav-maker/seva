# SEVA AI (सेवा डिजिटल सहाय्यक) — Master Product Requirement Document (PRD)

**System Name:** SEVA AI (Voice-First Autonomous Gram Panchayat Kiosk Engine)  
**Base Architecture Foundation:** [SAGAR-TAMANG/friday-tony-stark-demo](https://github.com/SAGAR-TAMANG/friday-tony-stark-demo) (All-in-One FastMCP + LiveKit)  
**Target Hardware:**  
1. *Demonstration Mode (Current):* Physical Windows Desktop (`HP Elite 7100 Microtower`, Intel Core i3 540 @ 3.07GHz, 3.7GB RAM, ~340MB Free RAM, Legacy Intel HD Graphics)  
2. *Production Appliance Mode (Future):* Screenless standalone **Raspberry Pi** (with USB mic, speaker, thermal printer, and USB 4G dongle)  
**Operating Directive:** Zero Virtual Machines · Visible Bare-Metal Desktop Chrome (`headless=False` for PC Demo, `headless=True` for Pi) · Zero 3D Three.js / WebGL Bloat · Pure Lightweight FastMCP + Playwright Execution  

---

## 1. Executive Summary & Vision

**SEVA AI** (सेवा डिजिटल सहाय्यक) is an autonomous, voice-driven public service kiosk assistant engineered for rural Indian citizens (Gram Panchayats, Setu Kendras, and Common Service Centers) who are illiterate, non-English speakers, or cannot operate a computer.

The citizen simply walks up to the kiosk and speaks in their mother tongue. SEVA AI autonomously perceives their request, asks necessary clarifying questions, opens the appropriate state or central government portal, fills the forms visibly on screen, solves captchas, verifies OTPs, and delivers the final document both as a physical printed paper and as a digital PDF sent to their WhatsApp.

---

## 2. Core Base Architecture: Sagar Tamang's F.R.I.D.A.Y. Engine

To eliminate fragmented code and avoid building a fragile multi-repo patchwork from scratch, SEVA AI is built upon **Sagar Tamang's F.R.I.D.A.Y.** (`https://github.com/SAGAR-TAMANG/friday-tony-stark-demo`) as its unified, all-in-one system engine.

```
                          ┌────────────────────────────────────────────────────────┐
                          │         SEVA AI CORE (Powered by F.R.I.D.A.Y.)         │
                          └───────────────────────────┬────────────────────────────┘
                                                      │
             ┌────────────────────────────────────────┴────────────────────────────────────────┐
             ▼                                                                                 ▼
 ┌────────────────────────────────────────┐                       ┌────────────────────────────────────────┐
 │       THE REAL-TIME VOICE PIPELINE     │                       │           THE FASTMCP SERVER           │
 │       (LiveKit + Gemini 2.5 Flash)     │                       │         (Computer Hands & Tools)       │
 ├────────────────────────────────────────┤                       ├────────────────────────────────────────┤
 │ • Always-on continuous listening       │ ◄── Real-Time Audio ─►│ • Playwright Visible Browser Tool     │
 │ • Webcam presence proactive trigger    │     & Tool Calls      │ • Android ADB Mobile App Tool (e-Pik)  │
 │ • GPS regional language greeting       │                       │ • Windows Native UI Automation Tool    │
 │ • Multilingual Indic speech synthesis  │                       │ • Thermal Printer & WhatsApp Tool      │
 └────────────────────────────────────────┘                       └────────────────────────────────────────┘
```

### Why F.R.I.D.A.Y. is the Chosen Foundation:
1. **Model Context Protocol (FastMCP):** Every computer action (launching Chrome, clicking fields, controlling mobile apps, printing receipts) is exposed to the AI brain as a standardized Python tool decorated with `@mcp.tool`.
2. **Real-Time Voice Architecture (LiveKit):** Ultra-low latency voice streaming with native interruption handling and speech-to-speech turnaround.
3. **Indic Language Intelligence:** Leverages Gemini 2.5 Flash / Sarvam AI / OpenRouter for native understanding of all 22 official Indian languages and colloquial rural dialects.
4. **Zero GPU / Low RAM Footprint:** The heavy LLM inference runs via cloud API, consuming less than 150MB of local RAM on the host machine.

---

## 3. Hardware Calibrations & Dual-Environment Matrix

| Hardware Component | PC Demonstration Mode (Now) | Raspberry Pi Production Appliance (Future) |
| :--- | :--- | :--- |
| **Physical Display** | Physical PC Monitor (Split-Screen HUD + Chrome) | **Screenless** (Headless standalone kiosk enclosure) |
| **Browser Setting** | `headless = False` (Visible Google Chrome) | `headless = True` (Silent background browser) |
| **Audio I/O** | USB Webcam Mic + Desktop Speakers | High-gain USB directional mic + 10W PA speaker |
| **Document Delivery** | Screen display + Local Downloads + WhatsApp | Physical Thermal Paper Print + WhatsApp PDF |
| **Memory Ceiling** | **Hard Cap <280MB Total RAM usage** | Capped at 512MB RAM on Raspberry Pi OS Lite |
| **Graphics Load** | 0% GPU (No Three.js/WebGL; pure HTML5/CSS/SVG) | 0% GPU (Pure headless / CLI mode) |

---

## 4. Key Architectural Pillars (Resolved via `/grill-me`)

### Pillar 1: Proactive Presence Detection (Webcam Dwell Trigger)
- **1-Second Dwell Trigger:** Using lightweight OpenCV presence detection (<15MB RAM, 0% GPU), the kiosk monitors the area in front of it. When a citizen stands steadily for 1+ seconds, it ignores casual passers-by and initiates the conversation proactively.
- **Proactive Voice Greeting:** Speaks out:
  > *"Namaste! Welcome to Gram Panchayat Digital Assistant. Please tell me, how can I help you today?"*

### Pillar 2: GPS-Based Regional Language Selection
- **Location on Boot:** On startup, the kiosk reads its coordinates via USB GPS or network geofencing.
- **Regional Mapping:**
  - Maharashtra $	o$ Greets and operates primarily in **Marathi** (with Hindi/English fallback).
  - Gujarat $	o$ Greets and operates in **Gujarati**.
  - Karnataka $	o$ Greets and operates in **Kannada**.
  - Tamil Nadu $	o$ Greets and operates in **Tamil**.
  - North / Central India $	o$ Greets and operates in **Hindi**.
- **Dynamic Real-Time Switching:** The citizen can speak in any of the 22 Indian languages at any time. The LLM Brain detects the language within 0.1s and seamlessly replies in the same tongue.

### Pillar 3: PC Monitor Visual Experience (Split-Screen Layout)
During demonstration mode on the Windows monitor:
- **Left Side (50% Width): Kiosk HUD**
  - Dark cyberpunk aesthetic (`#0a0f1d`) inspired by Ultron.
  - 4-State reactive audio visualizer ring: `STANDBY` $	o$ `LISTENING` $	o$ `THINKING` $	o$ `SPEAKING`.
  - Live regional language indicator pill and real-time step progress log.
- **Right Side (50% Width): Visible Google Chrome**
  - Real Google Chrome window (`headless=False`) executing automated actions via Playwright.
  - Glowing orange borders (`#ff5500`) pulsing on active inputs.
  - Smooth auto-scrolling to bring active fields into view.
  - Floating top status pill: `[⚡ SEVA AI: कार्य प्रगतीपथावर]`.

### Pillar 4: Multimodal Citizen Authentication & OTP Flow
- **Voice-First Input:** Citizen speaks their 10-digit mobile number and SMS OTP aloud in their native dialect (e.g. Marathi: *"पाच दोन आठ तीन"* $	o$ normalized to `5283` in 0.01ms).
- **Keypad Fallback:** An on-screen/physical numeric pad is available if the village Gram Panchayat environment is excessively noisy.
- **Biometric Scanner Support:** Integrated USB fingerprint scanner support (Mantra MFS100 / Morpho) for instant Aadhaar verification without typing OTPs.

### Pillar 5: Mobile-Only Government Apps (*e-Pik Pahani*)
- **Hybrid Execution Strategy:**
  1. *Tier A (Direct REST API):* Where government mobile endpoints are accessible, SEVA AI dispatches direct encrypted HTTPS calls for instant 0.5-second execution with 0MB RAM overhead.
  2. *Tier B (USB Phone ADB Bridge):* For closed apps like *e-Pik Pahani* (ई-पीक पाहणी), a low-cost physical Android phone is connected to the kiosk via USB. Friday executes ADB commands (`adb shell input tap/text`) to autonomously launch the app, select crops, and submit data with zero emulation load on the PC.

### Pillar 6: Mandatory Safety Review Gate (DPDP Act Compliance)
- Before clicking the final **"Submit"** or **"Pay Now"** button on any portal:
  1. Friday halts automated execution and highlights the review screen green (`#00cc44`).
  2. Friday speaks a clear verbal summary in the citizen's language:
     > *"I have entered Survey Number 45 for Haveli Taluka under the name Ramesh Patil. The fee is Rs 15. Should I submit this application?"*
  3. Pauses and waits for the citizen's spoken confirmation (*"Yes / Confirm"*).

### Pillar 7: Offline & Weak Internet Resilience
- **Offline Scheme FAQs:** If internet connectivity drops, Friday immediately informs the citizen verbally and answers scheme eligibility, subsidy details, and document checklists using an offline local database.
- **Offline Request Queuing:** If the citizen wants a live document while offline, the kiosk securely records their parameters and mobile number locally. As soon as connectivity restores, the backend automatically runs the transaction and dispatches the completed document to their WhatsApp.

### Pillar 8: Dual Output Delivery
Once a task completes:
1. **Physical Thermal Paper Print:** Automatically prints a receipt or land record extract from the connected thermal printer.
2. **WhatsApp Digital PDF:** Dispatches an official digital copy of the certificate/receipt directly to the citizen's WhatsApp number.

### Pillar 9: 15-Second Walk-Away Privacy Purge
- To strictly comply with the **Digital Personal Data Protection (DPDP) Act 2023**:
  - The webcam continuously monitors citizen presence during an active session.
  - If the citizen walks away from the kiosk for more than **15 seconds**, all entered data (Aadhaar numbers, OTPs, phone numbers, land records) is instantly wiped from memory and the screen resets to the standby welcome HUD.

---

## 5. Software Stack & Tool Registration (FastMCP Server)

```python
# Conceptual Tool Definitions registered in Friday FastMCP server:

@mcp.tool
def open_government_portal(portal_name: str, parameters: dict) -> str:
    # Launches visible Chrome, navigates to portal, fills forms, solves captchas.
    ...

@mcp.tool
def control_mobile_app(app_package: str, action: str, data: dict) -> str:
    # Operates Android apps (e.g., e-Pik Pahani) via USB ADB or direct REST API.
    ...

@mcp.tool
def print_and_send_document(file_path: str, citizen_phone: str) -> str:
    # Sends document to thermal printer and dispatches PDF via WhatsApp.
    ...

@mcp.tool
def query_offline_schemes(scheme_name: str, category: str) -> str:
    # Answers government scheme eligibility queries from local offline database.
    ...
```

---

## 6. Verification & Acceptance Criteria

1. **Hardware Verification:** Total local RAM consumption across all processes (Friday + Playwright + Web HUD) strictly <= 280 MB.
2. **Voice Responsiveness:** End-to-end voice latency <= 1.8 seconds from end of speech to audible reply.
3. **Intent Differentiation:** Chit-chat / scheme inquiries must NEVER open a browser; transaction requests must visibly launch Chrome.
4. **Captcha Accuracy:** Arithmetic captchas (`12 + 5`) must be solved with 100% accuracy in <0.05 seconds.
5. **Safety Compliance:** 100% of final submissions must pause for citizen verbal confirmation before execution.
