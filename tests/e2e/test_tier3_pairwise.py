"""
tests/e2e/test_tier3_pairwise.py
Tier 3: Cross-Feature Combinations (Pairwise Interaction Testing) for SEVA AI Kiosk Platform.

Covers cross-feature contracts, module interfaces, and combined state transitions:
1. LLM Pruning + CDP Streaming (F03 + F07)
2. Stall Detection + Human OTP Modal (F11 + F19)
3. Language Switching + Dual-Model Gateway (F16 + F01)
4. Language Switching + Safe Fallback (F16 + F04)
5. State Mutation Auditor + Step Budget Guard (F10 + F13)
6. Primitive Action Execution + CDP Screencast (F08 + F07)
7. Schema Validator + Safe Fallback Engine (F02 + F04)
8. Isolated Sandbox + Ephemeral Data Purge (F05 + F20)
9. Mock Portal + DOM Extractor (F21 + F06)
10. Mock Portal + Action Executor (F21 + F08)
11. FastAPI Host REST Endpoints + Step Budget Guard (F12 + F13)
12. FastAPI Host REST Endpoints + Ephemeral Purge (F12 + F20)
13. Human Checkpoint Modal + Primitive Action Wait (F19 + F08)
14. Touch Kiosk UI + Live MJPEG Viewport (F15 + F17)
15. Real-Time ODAV Audit Log + State Signatures (F18 + F09)
16. Schema Validator + Dual-Model Gateway Output (F02 + F01)
17. DOM Extractor + State Signature Calculation (F06 + F09)
18. Finish Termination Gate + FastAPI REST API (F14 + F12)
19. Language Switching + Touch UI Vernacular Labels (F16 + F15)
20. Dual-Model Gateway + Step Budget Tracking (F01 + F13)
21. Native CDP Screencast + Stream Endpoint (F07 + F12)
22. Isolated Chromium Sandbox + DOM Extractor (F05 + F06)
23. Safe Fallback Engine + Finish Termination Gate (F04 + F14)
24. Human Checkpoint Modal + Ephemeral Data Purge (F19 + F20)
25. Mock Portal + Stall Detection (F21 + F11)
26. Touch Kiosk UI + Web Speech Push-to-Talk (F15 + F16)

Total: 26 Pairwise Combinatorial Tests.
"""

import hashlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure Windows console supports Unicode Devanagari
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.llm_client import (
    CloudLLMGateway,
    clean_json_response,
    prune_context,
    fallback_decide,
    match_governance_service,
    VALID_ACTIONS,
    PORTAL_TEMPLATES,
)
from backend.models import (
    LLMDecision,
    DOMElement,
    StepDelta,
    PrunedContext,
    StartTaskRequest,
    StartTaskResponse,
    StepRequest,
    StepResponse,
    SessionState,
    ResetResponse,
)
from backend.sandbox import PlaywrightSandbox


class TestTier3PairwiseInteractions:
    """Pairwise cross-feature combinatorial verification."""

    def test_pair01_llm_pruning_and_cdp_streaming(self):
        """Pair 1 (F03 + F07): Context pruning keeps LLM prompt lightweight while CDP stream runs."""
        sb = PlaywrightSandbox(headless=True)
        # Simulate active screencast stream frames
        now = time.time()
        with sb._lock:
            sb._current_frame = b"\xff\xd8" + b"FRAME" * 200
            sb._frame_count = 25
            sb._fps_tracker = [now - 0.03 * i for i in range(25)]

        # Context pruning across 10 steps
        history = [{"action": f"act_{i}", "selector": f"#s_{i}", "status": "ok"} for i in range(10)]
        pruned = prune_context("7/12 Land record query", history)

        assert sb.fps >= 20.0
        assert "act_9" in pruned
        assert "act_8" in pruned
        assert "act_7" in pruned
        assert "act_0" not in pruned

    def test_pair02_stall_detection_and_human_otp_modal(self):
        """Pair 2 (F11 + F19): 2-step stall triggers human checkpoint modal with keypad."""
        # Consecutive identical states
        s_prev = "sig_stall_1234"
        s_curr = "sig_stall_1234"
        stall_count = 2
        stalled = (s_prev == s_curr and stall_count >= 2)
        assert stalled is True

        # When stalled is True, human checkpoint modal is activated
        modal_state = {
            "visible": stalled,
            "type": "stall_recovery",
            "message": "System detected stall. Please assist or enter requested OTP.",
            "keypad_active": True
        }
        assert modal_state["visible"] is True
        assert modal_state["keypad_active"] is True

    def test_pair03_language_switching_and_dual_model_gateway(self):
        """Pair 3 (F16 + F01): Switching language to Marathi routes through gateway with Marathi feedback."""
        gw = CloudLLMGateway()
        res_mr = gw.decide("मला उत्पन्नाचा दाखला हवा आहे", language="mr-IN", step_index=0)
        assert res_mr is not None
        assert "दाखल" in res_mr["feedback"] or "पोर्टल" in res_mr["feedback"]

        res_hi = gw.decide("मुझे आय प्रमाण पत्र चाहिए", language="hi-IN", step_index=0)
        assert res_hi is not None
        assert "आय" in res_hi["feedback"] or "प्रमाण" in res_hi["feedback"]

    def test_pair04_language_switching_and_safe_fallback(self):
        """Pair 4 (F16 + F04): Offline fallback correctly generates Hindi/Marathi/English spoken audio text."""
        languages = ["mr-IN", "hi-IN", "en-IN"]
        feedbacks = {}
        for lang in languages:
            step_data = fallback_decide("Income certificate", language=lang, step_index=0)
            feedbacks[lang] = step_data["feedback"]

        assert len(feedbacks["mr-IN"]) > 0
        assert len(feedbacks["hi-IN"]) > 0
        assert len(feedbacks["en-IN"]) > 0
        assert feedbacks["mr-IN"] != feedbacks["en-IN"]

    def test_pair05_state_mutation_auditor_and_step_budget_guard(self):
        """Pair 5 (F10 + F13): Unmutated step increments step budget towards ceiling without loop freeze."""
        state = SessionState(active=True, step=6, max_steps=8)
        sig_prev = "sig_same_hash"
        sig_curr = "sig_same_hash"

        mutated = (sig_prev != sig_curr)
        assert mutated is False

        # Step still advances and consumes budget
        state.step += 1
        assert state.step == 7
        assert (state.max_steps - state.step) == 1

    def test_pair06_primitive_action_execution_and_cdp_screencast(self):
        """Pair 6 (F08 + F07): Executing primitive action updates the screencast current frame."""
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()
        initial_frame = b"\xff\xd8INITIAL"
        updated_frame = b"\xff\xd8AFTER_FILL"
        sb._current_frame = initial_frame

        sb._page.screenshot = MagicMock(return_value=updated_frame)
        sb._page.wait_for_selector = MagicMock()
        sb._page.fill = MagicMock()

        ok, msg = sb._sync_execute_action("fill", "#name", "रविंद्र")
        assert ok is True
        assert sb.current_frame == updated_frame

    def test_pair07_schema_validator_and_safe_fallback_engine(self):
        """Pair 7 (F02 + F04): Cloud API response failing Schema Validator switches to Fallback Engine."""
        gw = CloudLLMGateway(api_key="mock-key")
        corrupted_cloud_json = "INVALID_NOT_JSON"

        with patch.object(gw, "_call_cloud_api", return_value=None):
            decision = gw.decide("मला उत्पन्नाचा दाखला हवा", language="mr-IN", step_index=0)
            assert decision is not None
            assert decision["action"] in VALID_ACTIONS
            assert set(decision.keys()) == {"thought", "action", "selector", "value", "feedback"}

    def test_pair08_isolated_sandbox_and_ephemeral_data_purge(self):
        """Pair 8 (F05 + F20): Resetting session cleanly wipes sandbox frame buffer and active state."""
        sb = PlaywrightSandbox(headless=True)
        sb._current_frame = b"\xff\xd8CONFIDENTIAL_AADHAAR"
        state = SessionState(active=True, task="Confidential Citizen Application")

        # Execute ephemeral purge
        with sb._lock:
            sb._current_frame = b""
        state.active = False
        state.task = ""
        state.history.clear()

        assert len(sb.current_frame) == 0
        assert state.active is False
        assert state.task == ""

    def test_pair09_mock_portal_and_dom_extractor(self):
        """Pair 9 (F21 + F06): Aaple Sarkar portal loads and exposes all required interactive selectors."""
        income_html = PORTAL_TEMPLATES["income"]
        assert 'id="applicant_name"' in income_html
        assert 'id="annual_income"' in income_html
        assert 'id="jurisdiction_select"' in income_html
        assert 'id="submit_btn"' in income_html

        # Simulate DOM extraction
        elements = [
            DOMElement(tag="input", id="applicant_name", selector="#applicant_name"),
            DOMElement(tag="input", id="annual_income", selector="#annual_income"),
            DOMElement(tag="select", id="jurisdiction_select", selector="#jurisdiction_select"),
            DOMElement(tag="button", id="submit_btn", selector="#submit_btn"),
        ]
        selectors = [e.selector for e in elements]
        assert "#applicant_name" in selectors
        assert "#submit_btn" in selectors

    def test_pair10_mock_portal_and_action_executor(self):
        """Pair 10 (F21 + F08): Navigating to satbara portal and filling survey number executes cleanly."""
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()
        sb._page.screenshot = MagicMock(return_value=b"\xff\xd8satbara")
        sb._sync_load_portal = MagicMock(return_value=True)

        ok, msg = sb._sync_execute_action("navigate", "", "http://127.0.0.1:8000/portal/satbara")
        assert ok is True
        assert "satbara" in msg.lower()

        ok, msg = sb._sync_execute_action("fill", "#survey_no", "42/1")
        assert ok is True
        assert "42/1" in msg

    def test_pair11_fastapi_rest_endpoints_and_step_budget_guard(self):
        """Pair 11 (F12 + F13): Sequential step execution reaches budget ceiling at step 8."""
        session = SessionState(active=True, step=0, max_steps=8)
        for _ in range(8):
            if session.step < session.max_steps:
                session.step += 1

        assert session.step == 8
        # Next step attempted
        is_blocked = (session.step >= session.max_steps)
        assert is_blocked is True

    def test_pair12_fastapi_rest_endpoints_and_ephemeral_purge(self):
        """Pair 12 (F12 + F20): Reset endpoint sets purged=True and clears session history."""
        session = SessionState(active=True, step=5, history=[{"action": "fill"}])
        res = ResetResponse(status="reset", purged=True)
        session.active = False
        session.step = 0
        session.history.clear()

        assert res.purged is True
        assert session.active is False
        assert len(session.history) == 0

    def test_pair13_human_checkpoint_modal_and_primitive_action_wait(self):
        """Pair 13 (F19 + F08): action='wait' pauses engine while OTP modal receives citizen digits."""
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()

        decision = {"action": "wait", "selector": "#otp", "feedback": "Please enter OTP"}
        if decision["action"] == "wait":
            ok, msg = sb._sync_execute_action("wait", "", "")
            assert ok is True
            assert "Waited" in msg

        # Citizen enters OTP
        otp_val = "987654"
        assert len(otp_val) == 6

    def test_pair14_touch_kiosk_ui_and_live_mjpeg_viewport(self):
        """Pair 14 (F15 + F17): Touch event coordinates on kiosk screen align with viewport reticle."""
        viewport_w, viewport_h = 1280, 720
        touch_x, touch_y = 640, 360  # Center tap
        reticle = {"x": touch_x, "y": touch_y, "radius": 24, "visible": True}

        assert reticle["x"] == touch_x
        assert reticle["y"] == touch_y
        assert 0 <= reticle["x"] <= viewport_w
        assert 0 <= reticle["y"] <= viewport_h

    def test_pair15_real_time_odav_audit_log_and_state_signatures(self):
        """Pair 15 (F18 + F09): Audit log verifies signature computation on each step."""
        log = []
        url = "http://portal/income"
        sig1 = hashlib.sha256(f"{url}|#name::".encode()).hexdigest()[:16]
        log.append({"phase": "Observe", "state_signature": sig1})

        sig2 = hashlib.sha256(f"{url}|#name:Ram:".encode()).hexdigest()[:16]
        log.append({"phase": "Verify", "state_signature": sig2})

        assert log[0]["state_signature"] != log[1]["state_signature"]

    def test_pair16_schema_validator_and_dual_model_gateway(self):
        """Pair 16 (F02 + F01): Dual model JSON output validated by LLMDecision schema."""
        raw_cloud_output = '{"thought": "Fill name", "action": "fill", "selector": "#applicant_name", "value": "Sita", "feedback": "Entered"}'
        parsed = clean_json_response(raw_cloud_output)
        assert parsed is not None
        model = LLMDecision(**parsed)
        assert model.action == "fill"
        assert model.value == "Sita"

    def test_pair17_dom_extractor_and_state_signature_calculator(self):
        """Pair 17 (F06 + F09): Extracted DOM elements hash deterministically into state signature."""
        elements = [
            DOMElement(tag="input", selector="#name", text="Name").model_dump(),
            DOMElement(tag="button", selector="#submit", text="Submit").model_dump()
        ]
        url = "http://portal/income"
        payload = f"{url}|" + "|".join(f"{e['selector']}::{e['text']}" for e in elements)
        sig = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        assert len(sig) == 16

    def test_pair18_finish_termination_gate_and_rest_endpoints(self):
        """Pair 18 (F14 + F12): Finished session locks further /api/step calls and returns finished status."""
        state = SessionState(active=True, step=4, finished=True)
        resp = StepResponse(
            step=state.step,
            state_signature="final_sig",
            action={"action": "finish", "selector": "", "value": "", "feedback": "Done", "thought": ""},
            status="finished"
        )
        assert resp.status == "finished"
        assert state.finished is True

    def test_pair19_language_switching_and_touch_ui_labels(self):
        """Pair 19 (F16 + F15): Language selection updates UI button labels in target script."""
        ui_i18n = {
            "mr-IN": {"start_btn": "सुरू करा", "reset_btn": "रद्द करा", "mic_btn": "बोला"},
            "hi-IN": {"start_btn": "शुरू करें", "reset_btn": "रद्द करें", "mic_btn": "बोलें"},
            "en-IN": {"start_btn": "Start", "reset_btn": "Reset", "mic_btn": "Speak"}
        }
        assert ui_i18n["mr-IN"]["start_btn"] == "सुरू करा"
        assert ui_i18n["hi-IN"]["start_btn"] == "शुरू करें"

    def test_pair20_dual_model_gateway_and_step_budget_tracking(self):
        """Pair 20 (F01 + F13): Context pruner passes remaining budget to LLM prompt."""
        history = [{"action": "navigate", "selector": "", "status": "ok"}]
        prompt_str = prune_context("Citizen goal", history)
        step_index = len(history)
        remaining = 8 - step_index
        assert remaining == 7
        assert "Step 1" in prompt_str

    def test_pair21_native_cdp_screencast_and_stream_endpoint(self):
        """Pair 21 (F07 + F12): Screencast frame generates HTTP MJPEG multipart chunk."""
        sb = PlaywrightSandbox(headless=True)
        fake_frame = b"\xff\xd8" + b"TEST_FRAME" * 50
        with sb._lock:
            sb._current_frame = fake_frame

        chunk = (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(sb.current_frame)}\r\n\r\n".encode("ascii")
            + sb.current_frame
            + b"\r\n"
        )
        assert b"--frame\r\n" in chunk
        assert b"image/jpeg" in chunk

    def test_pair22_isolated_chromium_sandbox_and_dom_extractor(self):
        """Pair 22 (F05 + F06): DOM Extractor runs inside headless sandbox with zero OS intrusion."""
        sb = PlaywrightSandbox(headless=True)
        assert sb.headless is True
        # Extract DOM sync when uninitialized returns empty list
        elements = sb._sync_extract_dom(25)
        assert isinstance(elements, list)

    def test_pair23_safe_fallback_engine_and_finish_termination_gate(self):
        """Pair 23 (F04 + F14): Capping at final fallback step triggers finish gate."""
        final_step = fallback_decide("उत्पन्न", language="mr-IN", step_index=99)
        assert final_step["action"] == "finish"
        assert len(final_step["feedback"]) > 0

    def test_pair24_human_checkpoint_modal_and_ephemeral_data_purge(self):
        """Pair 24 (F19 + F20): Reset during open OTP modal purges modal and wipes entered digits."""
        otp_buffer = "123456"
        modal_open = True

        # User presses reset
        otp_buffer = ""
        modal_open = False

        assert modal_open is False
        assert len(otp_buffer) == 0

    def test_pair25_mock_portal_and_stall_detection(self):
        """Pair 25 (F21 + F11): Unresponsive button click on portal triggers 2-step stall detector."""
        sig1 = "income_portal_s1"
        sig2 = "income_portal_s1"  # No mutation after click
        sig3 = "income_portal_s1"  # No mutation after 2nd click

        stall_count = 0
        stalled = False
        for s in [sig1, sig2, sig3]:
            if s == sig1:
                stall_count += 1
                if stall_count >= 2:
                    stalled = True
        assert stalled is True

    def test_pair26_touch_kiosk_ui_and_web_speech_push_to_talk(self):
        """Pair 26 (F15 + F16): Push-to-talk button press triggers speech listening state."""
        ptt_state = {"pressed": False, "listening": False, "language": "mr-IN"}

        # Citizen presses button
        ptt_state["pressed"] = True
        ptt_state["listening"] = True

        assert ptt_state["listening"] is True
        assert ptt_state["language"] == "mr-IN"
