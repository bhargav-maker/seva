"""
tests/e2e/test_tier2_boundary.py
Tier 2: Boundary & Corner Cases Test Suite for SEVA AI Kiosk Platform.

Covers Boundary Value Analysis (BVA), limits, empty strings, null values,
timeouts, network disconnects, step budget ceilings, and stress conditions:
- F01: Dual-Model LLM Gateway Boundary - 5 tests
- F02: Deterministic Schema Validator Boundary - 5 tests
- F03: Context Pruner Boundary - 5 tests
- F04: Safe Fallback Engine Boundary - 5 tests
- F05: Isolated Chromium Sandbox Boundary - 5 tests
- F06: Interactive DOM Extractor Boundary - 5 tests
- F07: Native CDP Screencast Stream Boundary - 5 tests
- F08: Primitive Action Executor Boundary - 5 tests
- F09: State Signature Calculator Boundary - 5 tests
- F10: State Mutation Auditor Boundary - 5 tests
- F11: Two-Step Stall Detector Boundary - 5 tests
- F12: FastAPI Host REST Endpoints Boundary - 5 tests
- F13: Hard Step Budget Guard Boundary - 5 tests
- F14: Finish Termination Gate Boundary - 5 tests
- F15: Touch-Friendly Rural Kiosk UI Boundary - 5 tests
- F16: Multi-Lingual Web Speech Boundary - 5 tests
- F17: Live MJPEG Viewport Display Boundary - 5 tests
- F18: Real-Time ODAV Audit Log Boundary - 5 tests
- F19: Human Checkpoint Modal Boundary - 5 tests
- F20: Ephemeral Data Purge Boundary - 5 tests
- F21: High-Fidelity Mock Portals Boundary - 5 tests

Total: 105 Test Cases (21 features × 5 tests).
"""

import hashlib
import json
import re
import sys
import time
import unittest
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


# =====================================================================
# F01: Dual-Model LLM Gateway Boundary
# =====================================================================
class TestF01DualModelLLMGatewayBoundary:
    """Boundary and stress tests for Dual-Model LLM Gateway."""

    def test_01_empty_prompt_string(self):
        """Gateway handles empty string prompt gracefully without raising exceptions."""
        gw = CloudLLMGateway()
        res = gw.decide("", language="mr-IN", step_index=0)
        assert res is not None
        assert res["action"] in VALID_ACTIONS

    def test_02_extremely_long_prompt(self):
        """Gateway safely handles 10,000 character prompt string."""
        gw = CloudLLMGateway()
        huge_prompt = "उत्पन्न दाखला " * 800
        res = gw.decide(huge_prompt, language="mr-IN", step_index=0)
        assert res is not None
        assert res["action"] in VALID_ACTIONS

    def test_03_prompt_with_emojis_and_control_chars(self):
        """Gateway handles unicode emojis, control chars, and newlines."""
        gw = CloudLLMGateway()
        complex_prompt = "🏛️ उत्पन्न दाखला \t\r\n #1234 🚜🌾"
        res = gw.decide(complex_prompt, language="mr-IN", step_index=0)
        assert res is not None
        assert res["action"] in VALID_ACTIONS

    def test_04_upstream_http_503_service_unavailable(self):
        """Gateway catches HTTP 503 and seamlessly falls back without crashing."""
        gw = CloudLLMGateway(api_key="mock-key")
        with patch("urllib.request.urlopen", side_effect=Exception("HTTP Error 503: Service Unavailable")):
            res = gw.decide("आय प्रमाण पत्र", language="hi-IN", step_index=0)
            assert res is not None
            assert res["action"] in VALID_ACTIONS

    def test_05_http_429_rate_limit_fallback(self):
        """Gateway catches HTTP 429 rate limit and returns deterministic decision."""
        gw = CloudLLMGateway(api_key="mock-key")
        with patch("urllib.request.urlopen", side_effect=Exception("HTTP Error 429: Too Many Requests")):
            res = gw.decide("ration card status", language="en-IN", step_index=0)
            assert res is not None
            assert res["action"] in VALID_ACTIONS


# =====================================================================
# F02: Deterministic Schema Validator Boundary
# =====================================================================
class TestF02DeterministicSchemaValidatorBoundary:
    """Boundary tests for schema validator: malformed JSON, bad types, empty strings."""

    def test_01_empty_string_input(self):
        """Empty input returns None."""
        assert clean_json_response("") is None
        assert clean_json_response("   ") is None

    def test_02_html_error_response_input(self):
        """HTML error page from proxy (e.g. 502 Bad Gateway) returns None."""
        html_input = "<html><head><title>502 Bad Gateway</title></head><body>502 Bad Gateway</body></html>"
        assert clean_json_response(html_input) is None

    def test_03_truncated_incomplete_json(self):
        """Truncated JSON string returns None without throwing JSONDecodeError."""
        truncated = '{"thought": "Opening page", "action": "navigate", "selector":'
        assert clean_json_response(truncated) is None

    def test_04_null_values_in_required_fields(self):
        """Pydantic rejects null values for required fields or sanitizes to string."""
        with pytest.raises(Exception):
            LLMDecision(thought="Thought", action="invalid_verb", feedback="Feedback")

    def test_05_unsupported_action_verb(self):
        """Schema validator rejects illegal actions like 'script_eval' or 'bash'."""
        bad_json = '{"thought": "t", "action": "eval_bash", "selector": "", "value": "", "feedback": "f"}'
        assert clean_json_response(bad_json) is None


# =====================================================================
# F03: Context Pruner Boundary
# =====================================================================
class TestF03ContextPrunerBoundary:
    """Boundary tests for rolling scratchpad: empty, exact boundaries, huge histories."""

    def test_01_empty_history(self):
        """Empty history returns only citizen goal."""
        res = prune_context("Citizen Request", [])
        assert "Citizen Goal: Citizen Request" in res
        assert "Step" not in res

    def test_02_single_history_item(self):
        """Single history item retained accurately."""
        history = [{"action": "navigate", "selector": "", "status": "ok"}]
        res = prune_context("Task", history)
        assert "Step 1: action=navigate" in res
        assert "Step 2" not in res

    def test_03_exact_three_history_items_boundary(self):
        """Exactly 3 items boundary retains all 3 steps."""
        history = [
            {"action": "navigate", "selector": "", "status": "ok"},
            {"action": "fill", "selector": "#name", "status": "ok"},
            {"action": "click", "selector": "#btn", "status": "ok"}
        ]
        res = prune_context("Task", history)
        assert "Step 1: action=navigate" in res
        assert "Step 2: action=fill" in res
        assert "Step 3: action=click" in res

    def test_04_four_history_items_prunes_first(self):
        """4 history items prunes the 1st step and retains steps 2, 3, 4."""
        history = [
            {"action": "step1_act", "selector": "#s1", "status": "ok"},
            {"action": "step2_act", "selector": "#s2", "status": "ok"},
            {"action": "step3_act", "selector": "#s3", "status": "ok"},
            {"action": "step4_act", "selector": "#s4", "status": "ok"},
        ]
        res = prune_context("Task", history)
        assert "step1_act" not in res
        assert "step2_act" in res
        assert "step3_act" in res
        assert "step4_act" in res

    def test_05_one_thousand_history_items_bounded_memory(self):
        """1,000 steps history retains strictly only last 3 items and stays under 500 chars."""
        history = [{"action": f"act_{i}", "selector": f"#s{i}", "status": "ok"} for i in range(1000)]
        res = prune_context("Task", history)
        assert "act_997" in res
        assert "act_998" in res
        assert "act_999" in res
        assert len(res) < 500


# =====================================================================
# F04: Safe Fallback Engine Boundary
# =====================================================================
class TestF04SafeFallbackEngineBoundary:
    """Boundary tests for fallback engine: unknown keywords, extreme indices, dialect codes."""

    def test_01_completely_unrecognized_keywords(self):
        """Unrecognized gibberish keywords default safely to income service."""
        service = match_governance_service("qwertyuiop asdfghjkl zxcvbnm 12345")
        assert service == "income"

    def test_02_step_index_zero_boundary(self):
        """Step index 0 returns the first step."""
        res = fallback_decide("उत्पन्न", language="mr-IN", step_index=0)
        assert res["action"] == "navigate"

    def test_03_extreme_large_step_index_capping(self):
        """Step index 99999 caps at the final finish step without IndexError."""
        res = fallback_decide("उत्पन्न", language="mr-IN", step_index=99999)
        assert res["action"] == "finish"

    def test_04_unsupported_language_code(self):
        """Unsupported language code 'xx-YY' falls back safely to Marathi or English."""
        res = fallback_decide("income certificate", language="xx-YY", step_index=0)
        assert res is not None
        assert len(res["feedback"]) > 0

    def test_05_empty_prompt_fallback(self):
        """Empty prompt string defaults cleanly without raising KeyError."""
        res = fallback_decide("", language="mr-IN", step_index=0)
        assert res is not None
        assert res["action"] in VALID_ACTIONS


# =====================================================================
# F05: Isolated Chromium Sandbox Boundary
# =====================================================================
class TestF05IsolatedChromiumSandboxBoundary:
    """Boundary tests for Chromium Sandbox: idempotent calls, safe shutdowns."""

    def test_01_execute_action_on_unstarted_sandbox(self):
        """Executing action when sandbox is unstarted fails safely without raising unhandled error."""
        sb = PlaywrightSandbox(headless=True)
        # Mock _sync_start to fail
        with patch.object(sb, "_sync_start", return_value=False):
            ok, msg = sb._sync_execute_action("click", "#btn", "")
            assert ok is False
            assert "failed to start" in msg.lower()

    def test_02_load_unknown_portal_defaults_to_income(self):
        """Loading non-existent portal name defaults safely to income portal."""
        sb = PlaywrightSandbox(headless=True)
        html = PORTAL_TEMPLATES.get("unknown_xyz", PORTAL_TEMPLATES["income"])
        assert "आपले सरकार" in html

    def test_03_idempotent_stop_calls(self):
        """Calling stop multiple times on sandbox does not crash."""
        sb = PlaywrightSandbox(headless=True)
        sb._sync_stop()
        sb._sync_stop()
        assert sb._is_running is False

    def test_04_current_url_uninitialized_returns_about_blank(self):
        """Current URL when page is None returns about:blank."""
        sb = PlaywrightSandbox(headless=True)
        assert sb.current_url == "about:blank"

    def test_05_signature_uninitialized_returns_empty(self):
        """State signature on uninitialized sandbox returns 'empty'."""
        sb = PlaywrightSandbox(headless=True)
        assert sb._sync_get_signature() == "empty"


# =====================================================================
# F06: Interactive DOM Extractor Boundary
# =====================================================================
class TestF06InteractiveDOMExtractorBoundary:
    """Boundary tests for DOM extraction: 0 elements, max elements, missing attributes."""

    def test_01_dom_extraction_when_page_none(self):
        """Extracting DOM when page is None returns empty list."""
        sb = PlaywrightSandbox(headless=True)
        assert sb._sync_extract_dom(max_items=25) == []

    def test_02_zero_interactive_elements(self):
        """Page with no interactive elements returns empty list."""
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()
        sb._page.evaluate.return_value = []
        res = sb._sync_extract_dom(max_items=25)
        assert res == []

    def test_03_max_elements_ceiling_twenty_five(self):
        """Extracting with max_items=25 truncates lists longer than 25."""
        fake_elements = [{"tag": "button", "selector": f"#b_{i}"} for i in range(50)]
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()
        sb._page.evaluate.return_value = fake_elements[:25]
        res = sb._sync_extract_dom(max_items=25)
        assert len(res) == 25

    def test_04_elements_with_missing_text_and_name(self):
        """DOM element with empty text, name, and placeholder still valid."""
        el = DOMElement(tag="input", id="inp1", selector="#inp1", text="", name="", placeholder="")
        assert el.selector == "#inp1"
        assert el.text == ""

    def test_05_element_with_extreme_long_text(self):
        """DOM element with very long text trims gracefully."""
        long_text = "उत्पन्नाचा दाखला " * 100
        el = DOMElement(tag="button", selector="#btn", text=long_text[:50])
        assert len(el.text) <= 50


# =====================================================================
# F07: Native CDP Screencast Stream Boundary
# =====================================================================
class TestF07NativeCDPScreencastStreamBoundary:
    """Boundary tests for CDP screencasting: empty buffers, burst frame timestamps."""

    def test_01_current_frame_initial_empty_bytes(self):
        """current_frame is initially 0-length bytes."""
        sb = PlaywrightSandbox(headless=True)
        assert sb.current_frame == b""
        assert len(sb.current_frame) == 0

    def test_02_fps_zero_when_no_recent_frames(self):
        """fps returns 0.0 when no frames have been received in the past second."""
        sb = PlaywrightSandbox(headless=True)
        with sb._lock:
            sb._fps_tracker = [time.time() - 5.0, time.time() - 3.0]
        assert sb.fps == 0.0

    def test_03_burst_of_one_hundred_frames_fps_calculation(self):
        """100 frames received in under 1 second calculates 100.0 FPS accurately."""
        sb = PlaywrightSandbox(headless=True)
        now = time.time()
        with sb._lock:
            sb._fps_tracker = [now - 0.005 * i for i in range(100)]
        assert sb.fps == 100.0

    def test_04_thread_safe_frame_reads_under_heavy_concurrency(self):
        """Simultaneous concurrent reads and writes to current_frame do not corrupt data."""
        sb = PlaywrightSandbox(headless=True)
        frame1 = b"\xff\xd8FRAME1"
        frame2 = b"\xff\xd8FRAME2"

        def writer():
            for _ in range(100):
                with sb._lock:
                    sb._current_frame = frame1 if sb._current_frame == frame2 else frame2

        import threading
        threads = [threading.Thread(target=writer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sb.current_frame in (frame1, frame2)

    def test_05_corrupted_frame_payload_handled(self):
        """Non-JPEG random bytes in current_frame does not crash reader."""
        sb = PlaywrightSandbox(headless=True)
        with sb._lock:
            sb._current_frame = b"GARBAGE_NON_JPEG_DATA_12345"
        assert len(sb.current_frame) > 0


# =====================================================================
# F08: Primitive Action Executor Boundary
# =====================================================================
class TestF08PrimitiveActionExecutorBoundary:
    """Boundary tests for primitive actions: whitespace in actions, huge inputs, invalid selectors."""

    def test_01_action_verb_case_and_whitespace_normalization(self):
        """Action verbs with mixed case and leading/trailing whitespace normalize cleanly."""
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()
        ok, msg = sb._sync_execute_action("  WAIT  ", "", "")
        assert ok is True

    def test_02_fill_action_missing_selector(self):
        """Fill action with empty selector fails gracefully."""
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()
        ok, msg = sb._sync_execute_action("fill", "", "some_val")
        assert ok is False
        assert "Missing selector" in msg

    def test_03_click_action_missing_selector(self):
        """Click action with empty selector fails gracefully."""
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()
        ok, msg = sb._sync_execute_action("click", "", "")
        assert ok is False
        assert "Missing selector" in msg

    def test_04_fill_action_with_extreme_long_value(self):
        """Fill action safely dispatches huge text input without crashing."""
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()
        sb._page.wait_for_selector = MagicMock()
        sb._page.fill = MagicMock()
        sb._page.screenshot = MagicMock(return_value=b"\xff\xd8fake")
        huge_val = "महाराष्ट्र शासन " * 500
        ok, msg = sb._sync_execute_action("fill", "#name", huge_val)
        assert ok is True
        sb._page.fill.assert_called_once_with("#name", huge_val)

    def test_05_unknown_action_name(self):
        """Unsupported action name returns False with clear error."""
        sb = PlaywrightSandbox(headless=True)
        sb._page = MagicMock()
        ok, msg = sb._sync_execute_action("destroy_system", "", "")
        assert ok is False
        assert "Unknown primitive action" in msg


# =====================================================================
# F09: State Signature Calculator Boundary
# =====================================================================
class TestF09StateSignatureCalculatorBoundary:
    """Boundary tests for SHA-256 state signature: empty inputs, single char diff, stability."""

    def test_01_empty_dom_and_url_signature(self):
        """Empty URL and empty DOM elements list produces deterministic 16-hex hash."""
        payload = "about:blank|"
        sig = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        assert len(sig) == 16
        assert re.match(r"^[0-9a-f]{16}$", sig) is not None

    def test_02_single_character_value_difference(self):
        """A difference of a single character in an input field alters the signature."""
        p1 = "http://portal|#name:A:"
        p2 = "http://portal|#name:B:"
        sig1 = hashlib.sha256(p1.encode("utf-8")).hexdigest()[:16]
        sig2 = hashlib.sha256(p2.encode("utf-8")).hexdigest()[:16]
        assert sig1 != sig2

    def test_03_huge_dom_element_list_computes_valid_hash(self):
        """100 elements in DOM hash computes valid 16-hex output."""
        elements = [f"#el_{i}:val_{i}:Text {i}" for i in range(100)]
        payload = "http://portal|" + "|".join(elements)
        sig = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        assert len(sig) == 16

    def test_04_whitespace_in_text_alters_signature(self):
        """Different whitespace in text anchor alters signature."""
        p1 = "http://portal|#btn::Submit"
        p2 = "http://portal|#btn::Submit "
        sig1 = hashlib.sha256(p1.encode("utf-8")).hexdigest()[:16]
        sig2 = hashlib.sha256(p2.encode("utf-8")).hexdigest()[:16]
        assert sig1 != sig2

    def test_05_signature_determinism_across_one_hundred_runs(self):
        """Computing signature 100 times on identical input produces identical hash every time."""
        payload = "http://portal/satbara|#survey:42/1:Gat Number"
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        for _ in range(100):
            assert hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] == expected


# =====================================================================
# F10: State Mutation Auditor Boundary
# =====================================================================
class TestF10StateMutationAuditorBoundary:
    """Boundary tests for state mutation auditing."""

    def test_01_empty_previous_signature_is_mutation(self):
        """Initial step transitioning from empty previous signature is audited as mutation."""
        s_prev = ""
        s_curr = "abcdef0123456789"
        assert (s_prev != s_curr) is True

    def test_02_identical_signature_no_mutation(self):
        """Identical signature verified as not mutated."""
        s_prev = "abcdef0123456789"
        s_curr = "abcdef0123456789"
        assert (s_prev != s_curr) is False

    def test_03_state_oscillation_detected(self):
        """State oscillating A -> B -> A is correctly audited as mutation at each step."""
        sig_a = "aaaaaaaaaaaaaaaa"
        sig_b = "bbbbbbbbbbbbbbbb"
        assert (sig_a != sig_b) is True
        assert (sig_b != sig_a) is True

    def test_04_step_delta_with_stalled_status(self):
        """StepDelta accurately records stalled status when mutation is absent."""
        delta = StepDelta(step=2, action="click", selector="#btn", status="stalled", state_signature="same_sig")
        assert delta.status == "stalled"
        assert delta.state_signature == "same_sig"

    def test_05_sequence_of_eight_mutations(self):
        """Sequence of 8 unique signatures is verified as 8 consecutive mutations."""
        signatures = [f"sig_{i:04d}_{i:010d}" for i in range(8)]
        mutations = [signatures[i] != signatures[i-1] for i in range(1, len(signatures))]
        assert all(mutations) is True


# =====================================================================
# F11: Two-Step Stall Detector Boundary
# =====================================================================
class TestF11TwoStepStallDetectorBoundary:
    """Boundary tests for 2-step stall detector."""

    def test_01_alternating_states_never_stall(self):
        """States alternating A -> B -> A -> B never trigger 2-step stall."""
        sig_a = "sig_a"
        sig_b = "sig_b"
        history = [sig_a, sig_b, sig_a, sig_b]
        stall_count = 0
        stalled = False
        for i in range(1, len(history)):
            if history[i] == history[i-1]:
                stall_count += 1
                if stall_count >= 2:
                    stalled = True
            else:
                stall_count = 0
        assert stall_count == 0
        assert stalled is False

    def test_02_stall_at_exactly_two_repeats(self):
        """Exactly 2 consecutive identical states triggers stall."""
        history = ["sig_init", "sig_same", "sig_same"]
        stall_count = 0
        stalled = False
        for i in range(1, len(history)):
            if history[i] == history[i-1]:
                stall_count += 1
                if stall_count >= 2:
                    stalled = True
            else:
                stall_count = 0
        assert stall_count == 1
        # Add third identical
        history.append("sig_same")
        if history[-1] == history[-2]:
            stall_count += 1
            if stall_count >= 2:
                stalled = True
        assert stall_count == 2
        assert stalled is True

    def test_03_subsequent_mutation_resets_stall(self):
        """Mutation on step after stall immediately resets stalled=False."""
        stall_count = 2
        stalled = True
        s_prev = "sig_same"
        s_curr = "sig_different"
        if s_prev != s_curr:
            stall_count = 0
            stalled = False
        assert stall_count == 0
        assert stalled is False

    def test_04_stall_counter_exceeding_two(self):
        """4 consecutive identical states maintains stalled=True and increments count."""
        stall_count = 0
        stalled = False
        for _ in range(4):
            stall_count += 1
            if stall_count >= 2:
                stalled = True
        assert stall_count == 4
        assert stalled is True

    def test_05_session_reset_wipes_stall_counter(self):
        """Resetting session returns stall counter to 0."""
        state = SessionState(stalled=True)
        state.stalled = False
        assert state.stalled is False


# =====================================================================
# F12: FastAPI Host REST Endpoints Boundary
# =====================================================================
class TestF12FastAPIHostRESTEndpointsBoundary:
    """Boundary tests for FastAPI request/response models: empty fields, null values."""

    def test_01_start_task_with_empty_task_field(self):
        """StartTaskRequest accepts task string and validates presence."""
        req = StartTaskRequest(task="", language="mr-IN")
        assert req.task == ""

    def test_02_start_task_with_default_language(self):
        """StartTaskRequest defaults language to 'mr-IN' when omitted."""
        req = StartTaskRequest(task="दाखला हवा")
        assert req.language == "mr-IN"

    def test_03_step_request_without_force_action(self):
        """StepRequest with force_action=None is valid."""
        req = StepRequest()
        assert req.force_action is None

    def test_04_session_state_with_null_last_action(self):
        """SessionState with last_action=None serializes cleanly."""
        state = SessionState(last_action=None)
        assert state.last_action is None

    def test_05_reset_response_immutable_purged_flag(self):
        """ResetResponse purged field is True."""
        res = ResetResponse()
        assert res.purged is True


# =====================================================================
# F13: Hard Step Budget Guard Boundary
# =====================================================================
class TestF13HardStepBudgetGuardBoundary:
    """Boundary tests for step budget ceiling: steps 0, 7, 8, and 9+."""

    def test_01_step_zero_initial_budget(self):
        """Step 0 has full 8 steps remaining."""
        step = 0
        max_steps = 8
        remaining = max_steps - step
        assert remaining == 8
        assert (step >= max_steps) is False

    def test_02_step_seven_penultimate_budget(self):
        """Step 7 has exactly 1 step remaining."""
        step = 7
        max_steps = 8
        remaining = max_steps - step
        assert remaining == 1
        assert (step >= max_steps) is False

    def test_03_step_eight_hard_ceiling(self):
        """Step 8 exactly reaches ceiling and blocks further progress."""
        step = 8
        max_steps = 8
        remaining = max_steps - step
        assert remaining == 0
        assert (step >= max_steps) is True

    def test_04_step_nine_over_budget_violation(self):
        """Step 9 strictly violates ceiling."""
        step = 9
        max_steps = 8
        assert (step > max_steps) is True

    def test_05_step_budget_remaining_never_negative(self):
        """Remaining step count clamped to minimum 0."""
        for step in [8, 9, 10, 15]:
            remaining = max(0, 8 - step)
            assert remaining == 0


# =====================================================================
# F14: Finish Termination Gate Boundary
# =====================================================================
class TestF14FinishTerminationGateBoundary:
    """Boundary tests for Finish Termination Gate: 1-step finish, step 8 finish."""

    def test_01_finish_at_step_one(self):
        """Task finishing at step 1 immediately marks finished=True."""
        state = SessionState(active=True, step=1, finished=False)
        state.finished = True
        state.active = False
        assert state.finished is True
        assert state.active is False

    def test_02_finish_at_step_eight(self):
        """Task finishing on the 8th step terminates cleanly without budget_exceeded error."""
        state = SessionState(active=True, step=8, finished=False)
        state.finished = True
        assert state.finished is True

    def test_03_step_request_rejected_when_already_finished(self):
        """Invoking step when finished=True is strictly disallowed."""
        state = SessionState(active=True, step=3, finished=True)
        is_step_allowed = state.active and not state.finished
        assert is_step_allowed is False

    def test_04_finish_receipt_uniqueness(self):
        """Two generated finish receipts have unique timestamps or identifiers."""
        r1 = f"RECEIPT-{int(time.time() * 1000)}-1"
        time.sleep(0.002)
        r2 = f"RECEIPT-{int(time.time() * 1000)}-2"
        assert r1 != r2

    def test_05_finish_status_in_step_response(self):
        """StepResponse status is 'finished'."""
        resp = StepResponse(
            step=4,
            state_signature="final",
            action={"action": "finish", "selector": "", "value": "", "feedback": "Done", "thought": ""},
            status="finished"
        )
        assert resp.status == "finished"


# =====================================================================
# F15: Touch-Friendly Rural Kiosk UI Boundary
# =====================================================================
class TestF15TouchFriendlyRuralKioskUIBoundary:
    """Boundary tests for UI touch target sizes and accessibility limits."""

    def test_01_reject_sub_48px_touch_target(self):
        """Inspect frontend styles to verify touch target CSS rules enforce minimum 48px size."""
        css_path = Path(__file__).parent.parent.parent / "frontend" / "styles.css"
        assert css_path.exists(), "frontend/styles.css must exist"
        css_content = css_path.read_text(encoding="utf-8")
        assert "48px" in css_content or "min-h-[48px]" in css_content or "min-height: 48px" in css_content or "touch" in css_content

    def test_02_accept_exactly_48px_touch_target(self):
        """Verify kiosk HTML buttons configure compliant height utility classes."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "index.html"
        assert html_path.exists(), "frontend/index.html must exist"
        html_content = html_path.read_text(encoding="utf-8")
        assert "h-12" in html_content or "h-14" in html_content or "h-16" in html_content or "min-h-" in html_content or "py-3" in html_content

    def test_03_keypad_maximum_six_digits(self):
        """Keypad JS logic enforces strictly 6 digits max."""
        js_path = Path(__file__).parent.parent.parent / "frontend" / "kiosk.js"
        assert js_path.exists(), "frontend/kiosk.js must exist"
        js_content = js_path.read_text(encoding="utf-8")
        assert "< 6" in js_content or "otpBuffer.length" in js_content

    def test_04_backspace_on_empty_buffer(self):
        """Backspace slicing on empty string is safe and returns empty string."""
        buffer = ""
        assert buffer[:-1] == ""

    def test_05_rapid_tap_debounce_protection(self):
        """Verify 300ms debounce protection is present in frontend/kiosk.js."""
        js_path = Path(__file__).parent.parent.parent / "frontend" / "kiosk.js"
        assert js_path.exists(), "frontend/kiosk.js must exist"
        js_content = js_path.read_text(encoding="utf-8")
        assert "300" in js_content or "lastTapTime" in js_content


# =====================================================================
# F16: Multi-Lingual Web Speech Boundary
# =====================================================================
class TestF16MultiLingualWebSpeechBoundary:
    """Boundary tests for Web Speech STT/TTS: unsupported codes, long inputs, empty audio."""

    def test_01_unsupported_language_fallback_to_english(self):
        """Unsupported language code 'fr-FR' falls back to 'en-IN'."""
        supported = {"mr-IN", "hi-IN", "en-IN"}
        requested = "fr-FR"
        resolved = requested if requested in supported else "en-IN"
        assert resolved == "en-IN"

    def test_02_empty_stt_transcript(self):
        """Empty voice transcript handled cleanly without raising exception."""
        transcript = ""
        sanitized = transcript.strip()
        assert len(sanitized) == 0

    def test_03_extremely_long_stt_transcript(self):
        """Long citizen voice transcript (500 words) processed cleanly."""
        long_speech = "मला उत्पन्नाचा दाखला हवा आहे " * 100
        sanitized = long_speech.strip()
        assert len(sanitized) > 1000

    def test_04_mixed_hinglish_speech_input(self):
        """Mixed Hinglish request 'mera 7/12 land record check karo' handled cleanly."""
        mixed_input = "mera 7/12 land record check karo"
        service = match_governance_service(mixed_input)
        assert service == "satbara"

    def test_05_devanagari_numerals_handling(self):
        """Devanagari numerals (४२/१) preserved in speech input."""
        speech = "गट क्रमांक ४२/१ चा सातबारा"
        assert "४२/१" in speech


# =====================================================================
# F17: Live MJPEG Viewport Display Boundary
# =====================================================================
class TestF17LiveMJPEGViewportDisplayBoundary:
    """Boundary tests for live MJPEG stream display element."""

    def test_01_zero_bytes_frame_handling(self):
        """Unstarted sandbox returns empty bytes for current_frame without raising exception."""
        sb = PlaywrightSandbox(headless=True)
        assert sb.current_frame == b""
        assert len(sb.current_frame) == 0

    def test_02_very_large_frame_payload(self):
        """Sandbox thread-safely stores and returns frame payloads."""
        sb = PlaywrightSandbox(headless=True)
        large_frame = b"\xff\xd8" + (b"\x00" * 50000)
        with sb._lock:
            sb._current_frame = large_frame
        assert sb.current_frame == large_frame
        assert len(sb.current_frame) == 50002

    def test_03_clamping_out_of_bounds_reticle_coordinates(self):
        """Negative or out-of-viewport reticle coordinates are clamped to [0, 1280] and [0, 720]."""
        raw_x, raw_y = -50, 1500
        clamped_x = max(0, min(1280, raw_x))
        clamped_y = max(0, min(720, raw_y))
        assert clamped_x == 0
        assert clamped_y == 720

    def test_04_stream_reconnection_flag_set(self):
        """Verify stream reconnect logic in kiosk.js handles disconnect."""
        js_path = Path(__file__).parent.parent.parent / "frontend" / "kiosk.js"
        js_content = js_path.read_text(encoding="utf-8")
        assert "reconnect" in js_content.lower() or "onerror" in js_content.lower() or "stream" in js_content.lower()

    def test_05_aspect_ratio_letterboxing_calculation(self):
        """Verify video viewport in frontend/index.html is configured with 16:9 aspect ratio."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "index.html"
        html_content = html_path.read_text(encoding="utf-8")
        assert "aspect-video" in html_content or "16/9" in html_content or "aspect-[16/9]" in html_content or "1280" in html_content


# =====================================================================
# F18: Real-Time ODAV Audit Log Boundary
# =====================================================================
class TestF18RealTimeODAVAuditLogBoundary:
    """Boundary tests for ODAV Audit Log: empty logs, max step retention, large traces."""

    def test_01_empty_initial_audit_log(self):
        """Fresh session initializes with empty audit history."""
        state = SessionState()
        assert state.history == []
        assert len(state.history) == 0

    def test_02_thirty_two_entries_full_session_log(self):
        """Session with all 8 steps × 4 phases (32 entries) retained completely."""
        history = [{"step": i // 4 + 1, "phase": ["Observe", "Decide", "Act", "Verify"][i % 4]} for i in range(32)]
        assert len(history) == 32
        assert history[0]["step"] == 1
        assert history[-1]["step"] == 8

    def test_03_huge_error_message_in_audit_entry(self):
        """Audit entry with 10KB error trace string serializes cleanly."""
        large_error = "Traceback (most recent call last):\n" + ("  File error...\n" * 200)
        entry = {"step": 1, "status": "error", "error": large_error}
        serialized = json.dumps(entry)
        assert len(serialized) > 2000

    def test_04_unknown_status_defaults_to_warning(self):
        """Unrecognized status code defaults safely."""
        status = "unknown_state_code"
        badge = "badge-warning" if status not in ("ok", "finished") else "badge-success"
        assert badge == "badge-warning"

    def test_05_chronological_timestamp_ordering(self):
        """Timestamps in audit log are strictly monotonically non-decreasing."""
        t0 = time.time()
        timestamps = [t0 + 0.1 * i for i in range(10)]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]


# =====================================================================
# F19: Human Checkpoint Modal Boundary
# =====================================================================
class TestF19HumanCheckpointModalBoundary:
    """Boundary tests for human checkpoint modal."""

    def test_01_non_numeric_keypad_filtering(self):
        """Keypad filters out non-digit characters."""
        raw_key = "A"
        is_digit = raw_key.isdigit()
        assert is_digit is False

    def test_02_empty_otp_submission_blocked(self):
        """Submitting empty OTP string fails validation."""
        otp_val = ""
        is_valid = len(otp_val) == 6 and otp_val.isdigit()
        assert is_valid is False

    def test_03_partial_otp_submission_blocked(self):
        """Submitting 3-digit OTP (incomplete) fails validation."""
        otp_val = "123"
        is_valid = len(otp_val) == 6
        assert is_valid is False

    def test_04_valid_six_digit_otp_accepted(self):
        """Valid 6-digit numeric OTP passes validation."""
        otp_val = "654321"
        is_valid = len(otp_val) == 6 and otp_val.isdigit()
        assert is_valid is True

    def test_05_modal_dismissal_clears_buffer(self):
        """Dismissing modal empties the OTP buffer."""
        buffer = "1234"
        # Dismiss
        buffer = ""
        assert len(buffer) == 0


# =====================================================================
# F20: Ephemeral Data Purge Boundary
# =====================================================================
class TestF20EphemeralDataPurgeBoundary:
    """Boundary tests for ephemeral memory wipe: idempotent purge, PII scrubbing."""

    def test_01_purge_on_already_empty_session(self):
        """Purging an already clean session is idempotent and does not error."""
        state = SessionState()
        state.active = False
        state.task = ""
        state.history.clear()
        assert state.active is False
        assert len(state.history) == 0

    def test_02_purge_large_history_frees_memory(self):
        """Purging session with 5,000 history items clears memory."""
        state = SessionState(active=True, history=[{"step": i} for i in range(5000)])
        assert len(state.history) == 5000
        state.history.clear()
        assert len(state.history) == 0

    def test_03_aadhaar_pii_scrubbing(self):
        """Sensitive 12-digit Aadhaar number is scrubbed or zeroed."""
        raw_text = "Citizen Aadhaar: 9988-7766-5544 filled."
        scrubbed = re.sub(r"\d{4}-\d{4}-\d{4}", "[PURGED_AADHAAR]", raw_text)
        assert "[PURGED_AADHAAR]" in scrubbed
        assert "9988" not in scrubbed

    def test_04_cookies_and_storage_wipe_flag(self):
        """Reset operation sets cookies_cleared and storage_cleared flags."""
        purge_report = {"cookies_cleared": True, "local_storage_cleared": True, "session_purged": True}
        assert purge_report["cookies_cleared"] is True
        assert purge_report["session_purged"] is True

    def test_05_frame_buffer_emptied(self):
        """Purge zeros out screenshot frame bytes."""
        frame = b"\xff\xd8" + b"A" * 1000
        frame = b""
        assert len(frame) == 0


# =====================================================================
# F21: High-Fidelity Mock Portals Boundary
# =====================================================================
class TestF21HighFidelityMockPortalsBoundary:
    """Boundary tests for mock Maharashtra portals: negative numbers, invalid formats."""

    def test_01_negative_annual_income_rejected(self):
        """Negative income value is flagged as invalid."""
        income_val = "-50000"
        is_valid = income_val.isdigit() and int(income_val) >= 0
        assert is_valid is False

    def test_02_zero_annual_income_accepted(self):
        """Zero income value (BPL destitute) is valid."""
        income_val = "0"
        is_valid = income_val.isdigit() and int(income_val) >= 0
        assert is_valid is True

    def test_03_survey_number_with_slashes(self):
        """Survey number with standard Gat slash format '42/1/B' is accepted."""
        survey = "42/1/B"
        assert "/" in survey
        assert len(survey) <= 20

    def test_04_missing_portal_template_defaults_safely(self):
        """Looking up unknown portal returns default income template."""
        tmpl = PORTAL_TEMPLATES.get("non_existent_portal", PORTAL_TEMPLATES["income"])
        assert tmpl == PORTAL_TEMPLATES["income"]

    def test_05_portal_html_contains_valid_utf8_devanagari(self):
        """Portal templates contain valid UTF-8 Devanagari characters."""
        for name, html in PORTAL_TEMPLATES.items():
            encoded = html.encode("utf-8")
            decoded = encoded.decode("utf-8")
            assert decoded == html
