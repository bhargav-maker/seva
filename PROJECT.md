# Project Technical Specification: SEVA AI (सेवा डिजिटल सहाय्यक)

**Engine Foundation:** [SAGAR-TAMANG/friday-tony-stark-demo](https://github.com/SAGAR-TAMANG/friday-tony-stark-demo) (All-in-One FastMCP + LiveKit)  
**Hardware Profile:** HP Elite 7100 Microtower (Core i3 540, 3.7GB RAM, ~340MB Free RAM) & Screenless Raspberry Pi Appliance  
**Deployment Modes:** Visible Desktop Demonstration (`headless=False`) & Standalone Screenless Appliance (`headless=True`)  

---

## 1. System Components & Repository Structure

```
c:\Users\Praka\OneDrive\Desktop\kiosk\
├── MASTER_PRD.md             # Master PRD specification (authoritative source of truth)
├── PRD.md                    # Synchronized duplicate master PRD
├── PROJECT.md                # Technical component contracts and interfaces
├── README.md                 # Project operational manual and usage guide
├── AGENTS.md                 # Autonomous loop engine directives
├── GEMINI.md                 # System guardrails and invariants
├── friday_core/              # Sagar Tamang's F.R.I.D.A.Y. Engine Base
│   ├── server.py             # FastMCP backend server (port 8000)
│   ├── voice_agent.py        # LiveKit real-time multilingual voice pipeline
│   └── tools/                # Registered Kiosk MCP Tools
│       ├── portal_tool.py    # Playwright visible Chrome automation
│       ├── mobile_tool.py    # Android ADB bridge for e-Pik Pahani
│       ├── printer_tool.py   # Thermal printer driver & WhatsApp dispatcher
│       └── offline_tool.py   # Offline scheme FAQ & request queue engine
├── vision/                   # Ultra-lightweight vision presence detector
│   └── presence_detector.py  # 1-second dwell trigger & 15-second walk-away purge
└── ui/                       # Kiosk Front-End HUD (Split-screen display)
    ├── index.html            # Lightweight HTML5 cyberpunk interface (<25MB RAM)
    └── styles.css            # 0% GPU CSS/SVG glowing audio ring & telemetry
```

---

## 2. FastMCP Tool Interface Contracts

### 2.1. Portal Tool Contract (`portal_tool.py`)
- **Inputs:** `service_key: str`, `parameters: dict`, `headless: bool`
- **Output:** `{"status": "SUCCESS" | "FAILED", "document_path": str, "fee_paid": float, "summary": str}`
- **Execution Invariants:**
  - Highlights active field with `outline: 4px solid #ff5500`.
  - Types with 30ms human cadence.
  - Automatically solves arithmetic captchas.
  - Pauses for spoken confirmation before final submit.

### 2.2. Mobile App Tool Contract (`mobile_tool.py`)
- **Inputs:** `app_id: str`, `action: str`, `payload: dict`
- **Output:** `{"status": "SUCCESS" | "FAILED", "transaction_id": str}`
- **Strategy:** Calls direct REST API if available; otherwise sends `adb shell input tap/text` to USB-connected Android phone.

### 2.3. Printer & WhatsApp Tool Contract (`printer_tool.py`)
- **Inputs:** `file_path: str`, `citizen_phone: str`, `print_paper: bool`
- **Actions:**
  - Sends ESC/POS raw data to USB thermal printer (`win32print`).
  - Calls WhatsApp Cloud API to deliver the PDF document to the citizen.

---

## 3. Hardware & Memory Enforcement Guardrails

1. **Total RAM Ceiling:** Memory usage of the entire Python + Chromium process tree must never exceed **280MB**.
2. **Zero GPU Utilization:** Absolutely no Three.js, WebGL, or Canvas 3D rendering. All visual elements are pure HTML5/CSS3.
3. **No Virtual Machines:** Everything runs 100% bare-metal on the physical Windows PC.
