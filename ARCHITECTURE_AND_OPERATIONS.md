# SEVA AI Kiosk - Architecture & Operations Manual

## System Overview

**SEVA AI** (सेवा डिजिटल सहाय्यक) is a voice-first autonomous kiosk for Indian Gram Panchayats, built on **Sagar Tamang's F.R.I.D.A.Y.** engine (FastMCP + LiveKit).

### Dual-Mode Execution
| Mode | Hardware | Browser | Display |
|------|----------|---------|---------|
| **Demo** | HP Elite 7100 (i3-540, 3.7GB RAM) | `headless=False` (Visible Chrome) | Split-screen: HUD (50%) + Chrome (50%) |
| **Production** | Raspberry Pi 4/5 + USB peripherals | `headless=True` | Screenless (Voice + Thermal Print) |

### Memory Constraint
- **Hard Cap: <280MB total RAM** across all processes
- Mutex lock ensures single browser instance
- Zero GPU: No Three.js, WebGL, or Canvas 3D

---

## Repository Structure

```
c:\Users\Praka\OneDrive\Desktop\kiosk\
├── MASTER_PRD.md                 # Master PRD (authoritative)
├── PRD.md                        # Synchronized PRD
├── PROJECT.md                    # Technical contracts
├── ARCHITECTURE_AND_OPERATIONS.md # This document
├── AGENTS.md                     # Autonomous loop directives
├── GEMINI.md                     # System invariants
├── requirements.txt              # Python dependencies
├── main.py                       # Entry point
├── friday_core/
│   ├── server.py                 # FastMCP server (port 8000)
│   ├── voice_agent.py            # LiveKit + Gemini 2.5 Flash pipeline
│   └── tools/
│       ├── portal_tool.py        # Playwright visible Chrome automation
│       ├── mobile_tool.py        # Android ADB bridge (e-Pik Pahani)
│       ├── printer_tool.py       # Thermal printer (ESC/POS) + WhatsApp
│       └── offline_tool.py       # Offline FAQ DB + Request queue
├── vision/
│   └── presence_detector.py      # 1-sec dwell / 15-sec purge (OpenCV)
└── ui/
    ├── index.html                # Cyberpunk HUD (<25MB RAM)
    ├── styles.css                # Pure CSS/SVG animations
    └── app.js                    # Vanilla JS WebSocket client
```

---

## Core Components

### 1. FastMCP Server (`friday_core/server.py:1`)
- **Port**: 8000
- **Endpoints**: `/health`, `/tools`, WebSocket `/ws/hud`
- **Registered Tools**: 4 tool modules via `@mcp.tool` decorators

### 2. Voice Agent (`friday_core/voice_agent.py:1`)
- **Pipeline**: LiveKit → STT (Whisper) → LLM (Gemini 2.5 Flash) → TTS (OpenAI)
- **Languages**: 22 Indian languages via dynamic switching
- **Presence Integration**: Proactive greeting on 1-sec dwell

### 3. Portal Tool (`friday_core/tools/portal_tool.py:1`)
- **Engine**: Playwright Chromium (`headless=False` for demo)
- **Features**:
  - Glowing orange borders (`#ff5500`) on active fields
  - Human typing cadence (30ms/char)
  - Arithmetic captcha solver (100% accuracy)
  - ODAV loop: Observe → Decide → Act → Verify (max 8 steps)
  - Safety Review Gate: Green highlight (`#00cc44`) + verbal summary + voice confirmation

### 4. Mobile Tool (`friday_core/tools/mobile_tool.py:1`)
- **Tier A**: Direct REST API (0.5s, 0MB overhead)
- **Tier B**: USB ADB Bridge (`adb shell input tap/text`)
- **Primary Use**: e-Pik Pahani (Maharashtra crop survey)

### 5. Printer Tool (`friday_core/tools/printer_tool.py:1`)
- **Thermal**: ESC/POS via `win32print` (Windows) / CUPS (Pi)
- **WhatsApp**: Cloud API (PDF document delivery)

### 6. Offline Tool (`friday_core/tools/offline_tool.py:1`)
- **SQLite DB**: Schemes + Queued requests
- **9 Default Schemes**: PM-KISAN, Ayushman, KCC, Soil Health, PMAY, Ujjwala, Land Records (Hi/MR)
- **Queue**: Auto-executes on internet restore + WhatsApp delivery

### 7. Presence Detector (`vision/presence_detector.py:1`)
- **OpenCV MOG2**: <15MB RAM, 0% GPU
- **Dwell**: 1+ seconds stationary → proactive greeting
- **Purge**: 15+ seconds absence → instant memory wipe

### 8. HUD UI (`ui/index.html:1`)
- **Split-screen**: Left=HUD, Right=Chrome (demo mode)
- **Audio Visualizer**: 4-state ring (STANDBY/LISTENING/THINKING/SPEAKING)
- **Progress Log**: Real-time step tracking
- **System Stats**: RAM, CPU, Network, Camera

---

## Operational Commands

### Installation
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Playwright Chromium
playwright install chromium

# 3. Set environment variables
set LIVEKIT_URL=ws://localhost:7880
set LIVEKIT_TOKEN=your_token
set WHATSAPP_ACCESS_TOKEN=your_token
set WHATSAPP_PHONE_NUMBER_ID=your_id
```

### Running the Kiosk

#### Demo Mode (Windows PC)
```bash
# Start LiveKit server (separate terminal)
livekit-server --dev

# Start SEVA AI Kiosk
python main.py
```

#### Production Mode (Raspberry Pi)
```bash
# Build for Pi
pip install -r requirements.txt --target ./deps
playwright install chromium --with-deps

# Run headless
SEVA_HEADLESS=true python main.py
```

### API Testing
```bash
# Health check
curl http://localhost:8000/health

# List tools
curl http://localhost:8000/tools

# Call portal tool
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "open_government_portal", "arguments": {"portal_name": "mahabhumi", "parameters": {"survey_number": "45", "taluka": "Haveli"}}}'
```

---

## Verification & Acceptance Criteria

| # | Criterion | Test Method |
|---|-----------|-------------|
| 1 | RAM ≤ 280MB | `ps aux --sort=-%mem | head -20` |
| 2 | Voice latency ≤ 1.8s | LiveKit metrics dashboard |
| 3 | Intent differentiation | Unit tests: chit-chat → no browser |
| 4 | Captcha 100% accuracy | Automated test suite with 50 samples |
| 5 | Safety gate 100% | E2E test: submit → pause → confirm |

### Running Tests
```bash
# Unit tests
pytest tests/ -v

# Memory profiling
python -m memory_profiler main.py

# Load test
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## Key Invariants (NEVER VIOLATE)

1. **Chit-chat/FAQ** → NEVER open browser (use offline DB)
2. **Transactions** → MUST open visible Chrome (`headless=False`)
3. **Final Submit/Pay** → PAUSE, green highlight, verbal summary, wait for voice "हाँ/Yes"
4. **Captcha** → Arithmetic only, instant solve
5. **Indic Numbers** → "पाच दोन आठ तीन" → `5283` normalization
6. **Walk-away 15s** → Instant purge (DPDP Act 2023)
7. **Single Browser** → Mutex lock enforced
8. **Dual Output** → Thermal print + WhatsApp PDF (always)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Chrome not visible | Check `headless=False`, DISPLAY env var |
| ADB device not found | `adb devices`, enable USB debugging |
| WhatsApp fails | Verify token, phone number ID, template approval |
| High RAM | Restart browser mutex, check for leaks |
| Voice latency | Check LiveKit server, network RTT |
| Language not switching | Verify Gemini 2.5 Flash API key |

---

## Extending the System

### Adding New Portal
1. Add flow method in `portal_tool.py` (`_new_portal_flow`)
2. Register in `execute_portal_task` dispatcher
3. Add selectors to parameters schema

### Adding New Scheme
```python
# In offline_tool.py _load_schemes() or via direct DB insert
INSERT INTO schemes VALUES ('new_id', 'Name', 'Category', ...);
```

### Adding New Language
1. Add greeting in `voice_agent.py _proactive_greeting()`
2. Add language pill text in `ui/app.js`
3. Ensure Gemini supports it (22 official languages)

---

## Security & Compliance

- **DPDP Act 2023**: 15-second purge, no data retention
- **No PII Logging**: All logs anonymized
- **HTTPS Only**: LiveKit WSS, WhatsApp API TLS
- **Input Sanitization**: All user inputs validated
- **Rate Limiting**: Per-session tool call limits

---

## Monitoring & Observability

### Health Endpoints
- `GET /health` → Service status
- `GET /tools` → Registered MCP tools
- `WS /ws/hud` → Real-time HUD updates

### Key Metrics
- Voice E2E latency (target: <1.8s)
- Portal task success rate (target: >95%)
- Memory usage (target: <280MB)
- Offline queue depth

---

## License & Attribution

**Base Engine**: [SAGAR-TAMANG/friday-tony-stark-demo](https://github.com/SAGAR-TAMANG/friday-tony-stark-demo)  
**SEVA AI Extensions**: Custom implementation for Gram Panchayat use case

---

*Generated as part of SEVA AI autonomous build cycle. All specifications derived from MASTER_PRD.md, PRD.md, PROJECT.md, GEMINI.md, AGENTS.md.*