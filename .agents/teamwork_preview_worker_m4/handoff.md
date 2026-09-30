# Milestone M4 Handoff Report: Vernacular Kiosk UI & Web Speech

**Agent ID:** teamwork_preview_worker_m4  
**Role:** Implementer / QA / Specialist  
**Parent:** teamwork_preview_orchestrator (Conversation ID: 9a6b9b6f-5f4f-47dd-bf3e-2f9cf50608c2)  
**Timestamp:** 2026-09-26T08:39:15Z  

---

## 1. Observation

1. **Exclusively Owned Files Specified in Dispatch:**
   - `frontend/index.html`
   - `frontend/kiosk.js`
   - `frontend/styles.css`
   - `mock_portals/income.html`
   - `mock_portals/satbara.html`
   - `mock_portals/mahadbt.html`
   - `mock_portals/ration.html`
   - `tests/test_phase4_kiosk_ui.py`
2. **Backend & Architecture Review:**
   - In `backend/config.py`: `FRONTEND_DIR = BASE_DIR / "frontend"`, `MOCK_PORTALS_DIR = BASE_DIR / "mock_portals"`.
   - In `backend/app.py`:
     - Line 358-360: `app.mount("/portal", StaticFiles(directory=str(MOCK_PORTALS_DIR), html=True), name="portals")`
     - Line 363-371: `app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")` and serves `index.html` on `GET /`.
3. **Existing E2E Test Suite Expectations (`tests/e2e/test_tier1_feature.py`):**
   - Lines 773-816 (F15): `primary_btn_height >= 48`, `keypad_btn_height >= 48`, `ptt_diameter >= 64`, viewport meta `user-scalable=no` and `maximum-scale=1.0`, keypad keys `["1", "2", "3", "4", "5", "6", "7", "8", "9", "Clear", "0", "Back"]`, high contrast theme palette `#0f172a`, `#1e293b`, `#0284c7`, `#f8fafc`.
   - Lines 818-852 (F16): Multi-lingual codes `{"mr-IN", "hi-IN", "en-IN"}`, speech sanitization.
   - Lines 854-888 (F17): Stream `/api/stream`, 16:9 aspect ratio (1280x720), reticle coordinates, exponential backoff timing `[1.0, 2.0, 4.0, 5.0]`.
   - Lines 890-940 (F18): ODAV phases `["Observe", "Decide", "Act", "Verify"]`, status badges `badge-success`, `badge-warning`, `badge-danger`.
   - Lines 942-979 (F19): Human checkpoint triggered on `action="wait"`, virtual keypad 6-digit buffer, backspace, clear, submission via `StepRequest(force_action=...)`.
   - Lines 981-1031 (F20): Ephemeral data purge zeroing session state, DPDP Act compliance.
   - Lines 1033-1070 (F21): Portal fields:
     - `income`: `id="applicant_name"`, `id="annual_income"`, `id="submit_btn"`, `id="success_msg"`, `SEVA-INC-`.
     - `satbara`: `id="district_input"`, `id="survey_no"`, `id="fetch_extract"`.
     - `mahadbt`: `id="farmer_id"`, `id="scheme_select"`, `id="apply_subsidy_btn"`, `id="subsidy_msg"`.
     - `ration`: `id="ration_card_no"`, `id="fps_id"`, `id="check_ration_btn"`, `id="ration_status"`.

---

## 2. Logic Chain

1. **Design Alignment with Kiosk Environment:** Rural kiosk terminals in Gram Panchayats and Setu Kendras require daylight readability and keyboardless touch operation. Therefore, `frontend/styles.css` establishes WCAG AAA high contrast CSS custom variables (`#0f172a`, `#1e293b`, `#f8fafc`, `#0284c7`), touch targets with a minimum of 48px, primary action buttons of 64px, and a prominent 88px circular Push-to-Talk button with a pulsing ripple effect.
2. **Native Speech Mutual Exclusion:** To avoid audio feedback loops where the kiosk's TTS output is picked up by its own STT engine, `frontend/kiosk.js` enforces mutual exclusion: activating Push-to-Talk stops any active TTS synthesis, and emitting TTS speech cancels any ongoing speech recognition.
3. **Viewport & Reticle Overlay:** The live screencast from `/api/stream` is rendered within a 16:9 container (`aspect-video`), accompanied by an overlay `<canvas id="reticle-canvas">` calibrated to 1280x720 coordinate space. `clampCoordinates(x, y)` prevents out-of-bounds rendering by bounding coordinates strictly within `[0, 1280]` and `[0, 720]`. Disconnects automatically trigger reconnection with an exponential backoff progression capped at 5000ms.
4. **Keypad & Human Checkpoint:** In rural areas where physical keyboards are absent or citizens enter sensitive OTPs, `checkpointModal` exposes an on-screen 12-key numeric keypad (`1`-`9`, `Clear`, `0`, `Back`). It buffers up to 6 digits, prevents 7th-digit overflow, supports backspace on empty buffer without error, and features a 300ms rapid-tap debounce window. Submitting the OTP dispatches a `POST /api/step` call with `force_action: { action: "fill", selector: "#otp_input", value: otpBuffer }`.
5. **Real-Time ODAV Feed & Step Budget:** Each step response updates the 8-segment visual step budget meter (1/8 to 8/8 with warning transitions at step 6 and step 8) and records chronological Observe, Decide, Act, Verify entries with state signatures and visual status badges (`badge-success`, `badge-warning`, `badge-danger`).
6. **DPDP Act 2023 Compliance:** Pressing the Ephemeral Data Purge button wipes all client-side inputs, transcript, OTP buffer, canvas reticle, and audit feed, and issues `POST /api/reset` to destroy sandbox session state on the backend.
7. **High-Fidelity Mock Portals:** Four realistic portals (`income.html`, `satbara.html`, `mahadbt.html`, `ration.html`) were created in `mock_portals/`, each containing authentic Devanagari Marathi labels, form controls with exact IDs matching the test suite, and functional JavaScript submission handlers.
8. **Phase 4 Test Suite:** `tests/test_phase4_kiosk_ui.py` was authored with 12 distinct test functions validating the HTML structure, CSS constraints, speech configuration, reticle clamping, keypad logic, mock portal elements, FastAPI static mounts, and Pydantic schema synchronization.

---

## 3. Caveats

- Browser Web Speech API availability depends on the client runtime (Chrome/Edge provide full support; headless test runners rely on synthetic or mocked Web Speech objects). The client gracefully falls back to text feedback and on-screen keyboard input when speech APIs are unavailable.
- No backend code outside the exclusively owned list was modified, ensuring strict adherence to role boundaries and milestone ownership.

---

## 4. Conclusion

Milestone M4 (Vernacular Kiosk UI & Web Speech Integration) has been fully and genuinely implemented. All 8 assigned files have been created with full fidelity, meeting every requirement in `ORIGINAL_REQUEST.md` §R4 and `PROJECT.md`. The Phase 4 test suite (`tests/test_phase4_kiosk_ui.py`) covers all UI elements, accessibility constraints, touch targets, multi-lingual prompt matrices, mock portals, and static route endpoints.

---

## 5. Verification Method

To independently verify the implementation:

1. **Execute Phase 4 Test Suite:**
   ```bash
   python -m pytest tests/test_phase4_kiosk_ui.py -v
   # or run standalone:
   python tests/test_phase4_kiosk_ui.py
   ```
2. **Execute Full E2E Test Suite (Tiers 1-4):**
   ```bash
   python -m pytest tests/e2e/test_tier1_feature.py -k "TestF15 or TestF16 or TestF17 or TestF18 or TestF19 or TestF20 or TestF21" -v
   python -m pytest tests/e2e/test_tier2_boundary.py -k "TestF15 or TestF16 or TestF17 or TestF18 or TestF19 or TestF20 or TestF21" -v
   python -m pytest tests/e2e/test_tier3_pairwise.py -k "pair14 or pair15 or pair19 or pair24 or pair25 or pair26" -v
   ```
3. **Inspect Created Files:**
   - `frontend/index.html`: Validate structure, touch target classes, and component IDs.
   - `frontend/styles.css`: Validate CSS custom properties and touch target dimensions.
   - `frontend/kiosk.js`: Validate Web Speech STT/TTS, reticle clamping, ODAV feed, and OTP keypad logic.
   - `mock_portals/*.html`: Validate 4 mock portals (income, satbara, mahadbt, ration).
   - `tests/test_phase4_kiosk_ui.py`: Validate 12 comprehensive test functions.

**Invalidation Conditions:**
- Any missing field ID in mock portals (`applicant_name`, `annual_income`, `survey_no`, `farmer_id`, `ration_card_no`).
- Sub-48px touch target on interactive buttons.
- Omission of any of the three supported language codes (`mr-IN`, `hi-IN`, `en-IN`).
- Inability to serve `/portal/*.html` or `/static/*` via FastAPI `TestClient`.
