# SEVA AI (सेवा डिजिटल सहाय्यक)

**Voice-First Autonomous Gram Panchayat Kiosk Engine**  
Built on **Sagar Tamang's F.R.I.D.A.Y.** (FastMCP + LiveKit)

---

## 🎯 Overview

SEVA AI enables rural Indian citizens to access government services by simply **speaking in their mother tongue**. The kiosk autonomously:
- Detects citizen presence via webcam (1-second dwell trigger)
- Greets in regional language (GPS-based + 22-language switching)
- Opens visible Chrome to fill government portal forms
- Solves captchas, verifies OTPs, handles payments
- Prints thermal receipt + sends WhatsApp PDF copy
- Purges all data after 15-second walk-away (DPDP Act 2023)

---

## 🖥️ Dual-Mode Execution

| Aspect | **PC Demo Mode** (Current) | **Pi Production Mode** (Future) |
|--------|---------------------------|--------------------------------|
| **Hardware** | HP Elite 7100 (i3-540, 3.7GB RAM) | Raspberry Pi 4/5 + USB peripherals |
| **Browser** | `headless=False` (Visible Chrome) | `headless=True` (Background) |
| **Display** | Split-screen: HUD (50%) + Chrome (50%) | Screenless (Voice + Print only) |
| **Audio** | USB Webcam mic + Desktop speakers | Directional USB mic + 10W PA speaker |
| **Output** | Screen + Downloads + WhatsApp | Thermal paper + WhatsApp PDF |
| **RAM Cap** | **<280MB** hard limit | 512MB on Pi OS Lite |

---

## 📋 Prerequisites

### Windows (Demo Mode)
- Windows 10/11 (64-bit)
- Python 3.10+ (from python.org, **check "Add to PATH"**)
- Google Chrome installed (default path)
- Git for Windows (optional)
- Visual C++ Redistributable (for `pywin32`)

### Hardware (Required for Full Functionality)
| Device | Purpose | Demo Mode | Production |
|--------|---------|-----------|------------|
| USB Webcam | Presence detection | ✅ Required | ✅ Required |
| Thermal Printer (ESC/POS) | Physical receipts | ✅ Required | ✅ Required |
| Android Phone + USB | e-Pik Pahani via ADB | ✅ Required | ✅ Required |
| USB GPS / Network | Regional language detection | Optional | ✅ Required |
| Fingerprint Scanner | Aadhaar biometric | Optional | Optional |

---

## ⚡ Quick Installation (Windows)

```powershell
# 1. Open PowerShell as Administrator
# 2. Navigate to project
cd C:\Users\Praka\OneDrive\Desktop\kiosk

# 3. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 4. Upgrade pip & install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Install Playwright Chromium
playwright install chromium

# 6. Configure environment
copy .env.example .env
notepad .env   # Fill in your API keys (see Configuration below)

# 7. Start LiveKit server (KEEP THIS TERMINAL OPEN)
livekit-server --dev

# 8. In NEW terminal, run SEVA AI
cd C:\Users\Praka\OneDrive\Desktop\kiosk
venv\Scripts\activate
python main.py
```

---

## 🔧 Detailed Installation Steps

### Step 1: Python & Virtual Environment
```powershell
# Verify Python version (must be 3.10+)
python --version

# Create venv in project folder
python -m venv venv

# Activate (run every time you open new terminal)
venv\Scripts\activate

# Verify activation - prompt should show (venv)
```

### Step 2: Install Python Dependencies
```powershell
# Core dependencies (~2-3 minutes)
pip install -r requirements.txt

# Expected key packages:
# fastmcp, livekit-agents, livekit-plugins-google, livekit-plugins-openai
# playwright, opencv-python-headless, numpy, pywin32, pillow
# aiohttp, fastapi, uvicorn, pydantic, python-dotenv
# fitz (pymupdf), reportlab
```

### Step 3: Playwright Browser
```powershell
# Install Chromium + system dependencies
playwright install chromium

# Verify installation
playwright --version
python -c "from playwright.async_api import async_playwright; print('Playwright OK')"
```

### Step 4: LiveKit Server
```powershell
# Option A: Docker (recommended)
docker run --rm -p 7880:7880 livekit/livekit-server --dev

# Option B: Binary (download from livekit.io)
# Place livekit-server.exe in PATH or project folder
livekit-server --dev

# Option C: LiveKit Cloud (managed)
# Use cloud URL in LIVEKIT_URL env var
```

### Step 5: Environment Configuration
```powershell
copy .env.example .env
notepad .env
```

**Required API Keys:**

| Variable | Source | Required |
|----------|--------|----------|
| `LIVEKIT_URL` | Local: `ws://localhost:7880` / Cloud: from LiveKit dashboard | ✅ Yes |
| `LIVEKIT_API_KEY` | LiveKit dashboard → API Keys | ✅ Yes |
| `LIVEKIT_API_SECRET` | LiveKit dashboard → API Keys | ✅ Yes |
| `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com) → Get API Key | ✅ Yes |
| `WHATSAPP_ACCESS_TOKEN` | [Meta Developer](https://developers.facebook.com) → WhatsApp → API Setup | For WhatsApp |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business Account → Phone Numbers | For WhatsApp |

**Optional:**
```env
SEVA_LANGUAGE=mr-IN          # Default: mr-IN (Marathi), hi-IN, gu-IN, kn-IN, ta-IN, en-IN
SEVA_HEADLESS=false          # true for Pi, false for PC demo
THERMAL_PRINTER_NAME=POS-58  # Run `wmic printer get name` to find exact name
ADB_PATH=adb                 # Full path if not in PATH
WEBCAM_INDEX=0               # Usually 0 for built-in, 1+ for USB
```

---

## 🚀 Running the Kiosk

### Terminal 1: LiveKit Server
```powershell
cd C:\Users\Praka\OneDrive\Desktop\kiosk
livekit-server --dev
# Keep running - shows "LiveKit server started on ws://0.0.0.0:7880"
```

### Terminal 2: SEVA AI Kiosk
```powershell
cd C:\Users\Praka\OneDrive\Desktop\kiosk
venv\Scripts\activate
python main.py
```

### Expected Startup Output
```
2024-01-15 10:30:00 - SEVA AI KIOSK STARTING
2024-01-15 10:30:00 - Voice-First Autonomous Gram Panchayat Assistant
2024-01-15 10:30:00 - Built on Sagar Tamang's F.R.I.D.A.Y. Engine
2024-01-15 10:30:01 - FastMCP Server started on http://0.0.0.0:8000
2024-01-15 10:30:01 - Voice Agent connected to LiveKit
2024-01-15 10:30:01 - Presence detector started (webcam)
2024-01-15 10:30:01 - SEVA AI Kiosk fully operational
```

### What You'll See (Demo Mode)
1. **Chrome window** opens on RIGHT half of screen (960x1080)
2. **HUD webpage** opens on LEFT half (or at `http://localhost:8000/ui`)
3. **Webcam LED** turns on (presence detection active)
4. **Audio visualizer** shows STANDBY pulsing ring
5. After 1+ seconds in front of camera → **Proactive greeting** in configured language

---

## 🌐 API Endpoints

### Health & Info
```bash
# Health check
curl http://localhost:8000/health
# {"status": "healthy", "service": "SEVA AI Kiosk"}

# List registered tools
curl http://localhost:8000/tools
# {"tools": ["open_government_portal", "close_portal_browser", "control_mobile_app", ...]}
```

### FastMCP Tool Calls (via HTTP)
```bash
# Open government portal (Mahabhumi 7/12 extract)
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "open_government_portal",
    "arguments": {
      "portal_name": "mahabhumi",
      "parameters": {
        "survey_number": "45",
        "taluka": "Haveli",
        "village": "Wagholi",
        "owner_name": "Ramesh Patil"
      },
      "headless": false
    }
  }'

# Query offline schemes
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "query_offline_schemes", "arguments": {"category": "कृषि", "language": "mr"}}'

# Queue offline request
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "queue_offline_request", "arguments": {"citizen_phone": "9876543210", "service": "pm_kisan", "parameters": {"aadhaar": "123456789012"}}}'

# Print & send document
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "print_and_send_document", "arguments": {"file_path": "C:\\path\\doc.pdf", "citizen_phone": "9876543210"}}'

# e-Pik Pahani via ADB
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "e_pik_pahani_workflow", "arguments": {"survey_number": "45", "taluka": "Haveli", "village": "Wagholi", "crop": "Soybean", "season": "Kharif", "owner_name": "Ramesh Patil"}}'
```

---

## 🗣️ Voice Interaction Examples

### Citizen Walk-up Flow
```
1. Citizen stands in front of kiosk for 1+ second
2. SEVA AI: "नमस्कार! ग्राम पंचायत डिजिटल सहाय्यकात स्वागत आहे. आज मी तुम्हाला कशी मदत करू शकतो?"
3. Citizen: "मला ७/१२ उत्तर घ्यायचा आहे" (I need 7/12 extract)
4. SEVA AI: "कृपया सर्वे नंबर, तालुका, गाव आणि मालकाचे नाव सांगा"
4. Citizen speaks details in Marathi
5. Chrome opens Mahabhumi portal, fills form with glowing orange borders
6. Captcha solved automatically
7. Before Submit: Green highlight + "मैने रमेश पाटील यांचे सर्वे नंबर ४५, हवेली तालुका साठी ७/१२ भरा आहे. शुल्क १५ रुपये. सबमिट करू का?"
8. Citizen: "होय" / "Yes"
9. Submit clicked → Document downloaded
10. Thermal printer prints receipt + WhatsApp PDF sent
```

### Offline Scheme Query
```
Citizen: "पीएम किसान योजनेचा लाभ कोणाला मिळतो?"
SEVA AI: (No browser opened - answers from local DB)
"पीएम-किसान योजनेअंतर्गत २ हेक्टरपर्यंत जमीन असलेल्या शेतकऱ्यांना वर्षी ₹६००० मिळते. आधार, ७/१२, बँक पासबुक लागेल."
```

### Language Switching
```
Citizen: "ગુજરાતીમાં બોલો" (Speak in Gujarati)
SEVA AI: (Instantly switches) "નમસ્તે! હું તમને કેવી રીતે મદદ કરી શકું?"
```

---

## 🔍 Verification & Testing

### Automated Checks
```powershell
# 1. Syntax validation
python -m py_compile main.py friday_core\server.py friday_core\voice_agent.py friday_core\tools\portal_tool.py friday_core\tools\mobile_tool.py friday_core\tools\printer_tool.py friday_core\tools\offline_tool.py vision\presence_detector.py

# 2. Import test
python -c "
import friday_core.server
import friday_core.voice_agent
import friday_core.tools.portal_tool
import friday_core.tools.mobile_tool
import friday_core.tools.printer_tool
import friday_core.tools.offline_tool
import vision.presence_detector
print('All modules import OK')
"

# 3. Memory baseline (run for 30s, check Task Manager)
# Target: <280MB total for python.exe + chrome.exe processes

# 4. API health
curl http://localhost:8000/health
curl http://localhost:8000/tools
```

### Manual Verification Checklist

| Test | Expected | Pass? |
|------|----------|-------|
| LiveKit connects | Voice Agent shows "connected" | ☐ |
| Webcam activates | LED on, presence detector running | ☐ |
| Chrome visible (demo) | Opens on right half, 960x1080 | ☐ |
| HUD loads | `http://localhost:8000/ui` shows cyberpunk UI | ☐ |
| Proactive greeting | Speaks after 1s dwell | ☐ |
| Marathi voice input | STT works, fills form | ☐ |
| Captcha solve | Arithmetic (12+5=17) instant | ☐ |
| Safety gate | Green highlight + verbal summary + waits | ☐ |
| Thermal print | Receipt prints on POS-58 | ☐ |
| WhatsApp send | PDF delivered to test number | ☐ |
| Walk-away purge | 15s absence → data wiped, HUD resets | ☐ |
| Offline FAQ | Answers without internet | ☐ |
| Queue + sync | Queued request executes when online | ☐ |
| RAM usage | <280MB sustained | ☐ |

---

## 🛠️ Troubleshooting

### Chrome Not Visible / Crashes
```powershell
# Check Chrome path
where chrome

# Run with debug
python -c "
import asyncio
from playwright.async_api import async_playwright
async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-gpu'])
        page = await browser.new_page()
        await page.goto('https://google.com')
        await page.wait_for_timeout(5000)
        await browser.close()
asyncio.run(test())
"

# Common fixes:
# - Disable antivirus temporarily
# - Run: playwright install chromium --with-deps
# - Check: SEVA_HEADLESS=false in .env
```

### ADB Device Not Found
```powershell
# On Android: Settings → About → Tap Build Number 7x → Developer Options → USB Debugging
# Connect USB, allow debugging on phone
adb devices
# Should show: <serial>    device

# If not:
adb kill-server
adb start-server
adb devices
```

### WhatsApp Not Sending
```powershell
# 1. Verify token not expired (24h for user tokens, permanent for system user)
# 2. Check phone number ID matches Business Account
# 3. Template must be approved for non-session messages
# 4. Test with curl:
curl -X POST "https://graph.facebook.com/v18.0/<PHONE_ID>/messages" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"messaging_product":"whatsapp","to":"919876543210","type":"template","template":{"name":"hello_world","language":{"code":"en"}}}'
```

### High Memory Usage
```powershell
# Check processes
Get-Process python*, chrome* | Select-Object Name, WorkingSet | Sort-Object WorkingSet -Descending

# Fixes:
# - Ensure only 1 browser instance (mutex in portal_tool.py)
# - Restart kiosk periodically (cron/Task Scheduler)
# - Reduce Chrome cache: --disk-cache-size=50000000
```

### LiveKit Connection Failed
```powershell
# Check LiveKit server running
netstat -an | findstr 7880

# Test WebSocket
python -c "
import websocket
ws = websocket.create_connection('ws://localhost:7880')
print('Connected')
ws.close()
"

# Firewall: Allow port 7880 inbound/outbound
```

### Language Not Switching
- Verify `GOOGLE_API_KEY` has Gemini 2.5 Flash access
- Check LiveKit agent logs for language detection
- Ensure `SEVA_LANGUAGE` matches supported codes

---

## 📁 Complete File Structure

```
kiosk/
├── MASTER_PRD.md                 # Master PRD (source of truth)
├── PRD.md                        # Synchronized PRD
├── PROJECT.md                    # Technical contracts
├── GEMINI.md                     # System invariants
├── AGENTS.md                     # Autonomous directives
├── ARCHITECTURE_AND_OPERATIONS.md # This architecture doc
├── README.md                     # This file
├── requirements.txt              # Python deps
├── .env.example                  # Env template
├── .gitignore                    # Git ignore
├── main.py                       # Entry point
│
├── friday_core/
│   ├── server.py                 # FastMCP server (port 8000)
│   ├── voice_agent.py            # LiveKit + Gemini pipeline
│   └── tools/
│       ├── portal_tool.py        # Playwright automation
│       ├── mobile_tool.py        # ADB / REST bridge
│       ├── printer_tool.py       # Thermal + WhatsApp
│       └── offline_tool.py       # SQLite FAQ + queue
│
├── vision/
│   └── presence_detector.py      # OpenCV presence (15MB RAM)
│
├── ui/
│   ├── index.html                # HUD HTML
│   ├── styles.css                # Cyberpunk CSS/SVG
│   └── app.js                    # WebSocket client
│
└── data/                         # Created at runtime
    ├── seva_offline.db           # SQLite schemes + queue
    └── schemes.json              # Scheme definitions
```

---

## 🔐 Security & Compliance

| Requirement | Implementation |
|-------------|----------------|
| **DPDP Act 2023** | 15-second walk-away purge, no PII retention |
| **Data Encryption** | HTTPS/WSS only, AES-256 for queued requests |
| **Access Control** | Local-only FastMCP, no external tool exposure |
| **Audit Trail** | All tool calls logged with timestamp |
| **Consent** | Mandatory voice confirmation before submit |

---

## 📊 Monitoring

### Key Metrics to Watch
```bash
# Voice latency (target <1.8s)
# Portal success rate (target >95%)
# Memory usage (target <280MB)
# Offline queue depth
# WhatsApp delivery rate
```

### Log Locations
```powershell
# Application logs: Console output (stdout/stderr)
# LiveKit logs: LiveKit server terminal
# Chrome logs: %USERPROFILE%\AppData\Local\Google\Chrome\User Data\Default\Chrome_debug.log
# ADB logs: adb logcat
```

---

## 🧪 Development

### Running Tests
```powershell
# Install test deps
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v --cov=friday_core --cov=vision

# Memory profiling
pip install memory_profiler
python -m memory_profiler main.py
```

### Adding New Portal
1. Add flow method in `friday_core/tools/portal_tool.py`:
   ```python
   async def _new_portal_flow(self, params: Dict) -> Dict:
       # Navigate, fill, captcha, safety gate, submit
   ```
2. Register in `execute_portal_task()` dispatcher
3. Add test case in `tests/test_portals.py`

### Adding New Scheme
```python
# In offline_tool.py or direct SQL:
INSERT INTO schemes (id, name, category, description, eligibility, documents, benefits, application_process, official_portal, helpline, language)
VALUES ('new_scheme', 'Scheme Name', 'Category', 'Description', 'Eligibility', '["Doc1", "Doc2"]', 'Benefits', 'Process', 'https://portal.gov.in', '1800-xxx-xxxx', 'hi');
```

### Adding New Language
1. Add greeting in `voice_agent.py:_proactive_greeting()`
2. Add language pill in `ui/app.js:setLanguage()`
3. Verify Gemini 2.5 Flash supports it

---

## 📦 Production Deployment (Raspberry Pi)

### Pi Setup
```bash
# On Raspberry Pi OS Lite (64-bit)
sudo apt update && sudo apt install -y python3-venv python3-pip chromium-browser \
  libatlas-base-dev libopenblas-dev libjpeg-dev zlib1g-dev \
  cups cups-client printer-driver-escpr \
  adb udev

# Clone project
git clone <repo> /home/pi/seva-kiosk
cd /home/pi/seva-kiosk

# Python venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps

# Configure
cp .env.example .env
nano .env  # Set SEVA_HEADLESS=true, LIVEKIT_URL=wss://your-cloud.livekit.cloud

# Systemd service
sudo tee /etc/systemd/system/seva-kiosk.service > /dev/null <<'EOF'
[Unit]
Description=SEVA AI Kiosk
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/seva-kiosk
Environment=PATH=/home/pi/seva-kiosk/venv/bin
ExecStart=/home/pi/seva-kiosk/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable seva-kiosk
sudo systemctl start seva-kiosk

# Check status
sudo systemctl status seva-kiosk
journalctl -u seva-kiosk -f
```

### Pi Hardware Connections
| Device | Connection | Config |
|--------|------------|--------|
| Thermal Printer | USB | `lsusb` → add udev rule, `lpadmin -p POS58 -v usb://... -E` |
| Webcam | USB | `/dev/video0` (WEBCAM_INDEX=0) |
| Android Phone | USB + ADB | `adb devices` → authorize |
| Speaker | 3.5mm / USB | `aplay -l` to verify |
| GPS | USB | `gpsd /dev/ttyUSB0` |

---

## 🆘 Support

### Common Issues Quick Reference
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "ModuleNotFoundError" | venv not activated | `venv\Scripts\activate` |
| "Playwright not installed" | Missing browser | `playwright install chromium` |
| "LiveKit connection failed" | Server not running | Start `livekit-server --dev` |
| "Webcam not found" | Index wrong / in use | Change `WEBCAM_INDEX`, close other apps |
| "Printer not printing" | Wrong name / driver | `wmic printer get name`, install ESC/POS driver |
| "ADB unauthorized" | Phone not authorized | Replug USB, allow on phone screen |
| "WhatsApp 401" | Token expired | Regenerate in Meta Developer Console |
| "RAM > 280MB" | Browser leak / multiple instances | Restart kiosk, check mutex |

### Logs to Collect for Bug Reports
```powershell
# 1. Kiosk startup logs (full console output)
# 2. LiveKit server logs
# 3. Chrome debug log (if portal fails)
# 4. adb logcat (if mobile tool fails)
# 5. Memory snapshot: Get-Process python*,chrome* | Format-Table Name,WS
```

---

## 📄 License & Credits

**Base Engine**: [SAGAR-TAMANG/friday-tony-stark-demo](https://github.com/SAGAR-TAMANG/friday-tony-stark-demo) - MIT License  
**SEVA AI Extensions**: Custom implementation for Gram Panchayat Digital Assistant

### Acknowledgments
- **LiveKit** - Real-time voice infrastructure
- **Google Gemini 2.5 Flash** - Multilingual LLM
- **Playwright** - Browser automation
- **OpenCV** - Lightweight computer vision
- **Meta WhatsApp Cloud API** - Document delivery

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-15 | Initial build: Full dual-mode kiosk with all 9 pillars |

---

**Ready to serve citizens! 🇮🇳**

*For issues, check `ARCHITECTURE_AND_OPERATIONS.md` for complete technical documentation.*