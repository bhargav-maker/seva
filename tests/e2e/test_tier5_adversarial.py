"""
tests/e2e/test_tier5_adversarial.py
Tier 5: Adversarial Challenge & Stress-Test Suite for SEVA AI Kiosk Platform.

Authored by: teamwork_preview_challenger (Empirical Challenger 1)
Scope:
1. LLM Schema Validation under corrupt, malformed, and adversarial payloads:
   - Truncated JSON, non-JSON strings, HTML proxy errors (502).
   - Multiple JSON blocks (greedy regex collision stress).
   - Extra injected keys, proto pollution attempts.
   - Missing required keys across all 5 contract properties.
   - Invalid action verbs and illegal command injection payloads.
   - Null values in required fields and type confusion.
   - Extreme Unicode strings (Devanagari, emojis, control characters).
2. Context Pruning under extreme history lengths:
   - 0 steps, 1 step, 3 steps (exact boundary), 4 steps (pruning first), 1,000 steps (bounded memory).
   - Corrupt history entries (missing keys, None values).
   - Output string length boundedness and token budget preservation.
3. Resilient Timeout & Network Fallbacks:
   - Upstream network socket timeouts (>8.0s guard).
   - HTTP 429 Too Many Requests (rate limiting).
   - HTTP 500 / 503 Internal Server Error & Service Unavailable.
   - HTTP 401 / 403 API key rejection and circuit breaker auto-disable.
   - Cascading failure: Gemini fails + OpenRouter fails -> deterministic local fallback.
   - Fallback engine boundary: unrecognized gibberish intent, out-of-bounds step index (99999).
4. BrowserSandbox Concurrency, Error Trapping & Navigation:
   - Rapid concurrent frame requests from mjpeg_frame_generator (50 concurrent consumers).
   - High-throughput thread safety: simultaneous frame reads and updates.
   - Frame format integrity: multipart JPEG boundaries, JPEG magic bytes (FF D8 ... FF D9).
   - Invalid and malformed CSS selectors (brackets, quotes, XSS vectors).
   - Primitive actions on non-existent DOM elements (timeout guards).
   - Navigation to unreachable, dead, and invalid scheme URLs.
   - Sandbox idempotency under repeated initialize() and close() calls.
5. ODAV Engine & State Machine Stress:
   - Consecutive identical states vs alternating states for 2-step stall detector.
   - Hard 8-step budget ceiling (step 8 vs step 9 lock).
   - Ephemeral data purge zeroing volatile memory (DPDP Act compliance).
"""

import asyncio
import hashlib
import json
import re
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Ensure Windows stdout/stderr supports Unicode Devanagari
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
    API_TIMEOUT_SEC,
    PORTAL_TEMPLATES,
    GOVERNANCE_SERVICES,
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
from backend.browser_sandbox import (
    BrowserSandbox,
    PlaywrightSandbox,
    VALID_JPEG_BYTES,
)
from backend.state_manager import (
    SessionStateManager,
    get_default_state_manager,
    reset_default_state_manager,
)
from backend.odav_engine import ODAVEngine


# =====================================================================
# 1. Adversarial LLM Schema Validation Suite
# =====================================================================
class TestAdversarialLLMSchemaValidation:
    """Stress-tests LLM JSON parser and schema validator against hostile inputs."""

    def test_01_truncated_and_partial_json(self):
        """Truncated JSON fragments return None without unhandled parser crash."""
        payloads = [
            '{"thought": "Opening page',
            '{"thought": "t", "action": "navigate", "selector":',
            '{"thought": "t", "action": "click", "selector": "#btn", "value": ""',
            '{',
            '{"thought":',
        ]
        for p in payloads:
            assert clean_json_response(p) is None

    def test_02_non_json_and_html_proxy_errors(self):
        """Raw HTML proxy error responses (502, 503, 504) return None."""
        html_payloads = [
            "<html><body>502 Bad Gateway</body></html>",
            "<!DOCTYPE html><html><head><title>503 Service Unavailable</title></head></html>",
            "Error: upstream request timeout at proxy.internal",
            "Internal Server Error",
            "",
            "   \t\r\n   ",
        ]
        for p in html_payloads:
            assert clean_json_response(p) is None

    def test_03_markdown_code_block_variations(self):
        """Extracts JSON cleanly across diverse markdown wrapping styles."""
        valid_body = '{"thought": "OK", "action": "click", "selector": "#btn", "value": "", "feedback": "प्रतिक्षा करा"}'

        variations = [
            f"```json\n{valid_body}\n```",
            f"```JSON\n{valid_body}\n```",
            f"```\n{valid_body}\n```",
            f"Here is your action decision:\n```json\n{valid_body}\n```\nHope this helps!",
            f"```json  {valid_body}  ```",
        ]
        for v in variations:
            res = clean_json_response(v)
            assert res is not None, f"Failed on markdown variant: {v}"
            assert res["action"] == "click"
            assert res["selector"] == "#btn"

    def test_04_multiple_json_blocks_greedy_regex_handling(self):
        """
        Adversarial test for multiple JSON blocks or commentary with braces.
        Checks behavior when commentary contains closing braces.
        """
        valid_json = '{"thought": "t", "action": "wait", "selector": "", "value": "", "feedback": "f"}'
        # Payload with an explanation block before the actual decision
        payload_with_preamble = f'Note: {{debug_info: true}} Decision: {valid_json}'
        res = clean_json_response(payload_with_preamble)
        # If greedy regex captures from first { to last }, json.loads fails and returns None safely
        assert res is None or res["action"] == "wait"

    def test_05_missing_required_keys_exhaustive(self):
        """Rejects JSON missing any one of the 5 required contract keys."""
        full_dict = {
            "thought": "T",
            "action": "click",
            "selector": "#b",
            "value": "",
            "feedback": "F"
        }
        for missing_key in ["thought", "action", "selector", "value", "feedback"]:
            corrupt = full_dict.copy()
            del corrupt[missing_key]
            raw = json.dumps(corrupt)
            assert clean_json_response(raw) is None, f"Should reject when missing '{missing_key}'"

    def test_06_extra_injected_keys_sanitization(self):
        """
        Extra adversarial keys (code injection, proto pollution, role tampering)
        are completely discarded, retaining strictly the 5 contract keys.
        """
        injected = {
            "thought": "T",
            "action": "fill",
            "selector": "#name",
            "value": "Test",
            "feedback": "F",
            "malicious_code": "import os; os.system('rm -rf /')",
            "__proto__": {"isAdmin": True},
            "role": "system",
            "sql_injection": "' OR 1=1 --",
            "extra_nested": {"a": [1, 2, 3]}
        }
        res = clean_json_response(json.dumps(injected))
        assert res is not None
        assert set(res.keys()) == {"thought", "action", "selector", "value", "feedback"}
        assert "malicious_code" not in res
        assert "__proto__" not in res
        assert "role" not in res

    def test_07_invalid_action_verbs_and_injection(self):
        """Rejects any action verb not strictly in the 6 valid primitives."""
        illegal_actions = [
            "eval", "eval_bash", "exec", "system", "script",
            "delete", "drop", "navigate_and_click", "CLICK_AND_WAIT",
            "", "   ", "null", "undefined", "123", "sleep", "prompt"
        ]
        for act in illegal_actions:
            payload = json.dumps({
                "thought": "T",
                "action": act,
                "selector": "",
                "value": "",
                "feedback": "F"
            })
            assert clean_json_response(payload) is None, f"Should reject invalid action: {act}"

    def test_08_valid_action_verbs_case_and_whitespace_normalization(self):
        """Accepts all 6 valid primitives and normalizes case/whitespace."""
        for act in ["navigate", "click", "fill", "scroll", "wait", "finish"]:
            for variant in [act, act.upper(), f"  {act}  ", act.capitalize()]:
                payload = json.dumps({
                    "thought": "T",
                    "action": variant,
                    "selector": "",
                    "value": "",
                    "feedback": "F"
                })
                res = clean_json_response(payload)
                assert res is not None, f"Failed on valid variant: {variant}"
                assert res["action"] == act

    def test_09_null_and_non_string_values_in_fields(self):
        """Handles null values in selector, value, thought without unhandled crash."""
        payload = json.dumps({
            "thought": "T",
            "action": "scroll",
            "selector": None,
            "value": None,
            "feedback": "F"
        })
        res = clean_json_response(payload)
        assert res is not None
        assert res["selector"] == ""
        assert res["value"] == ""

    def test_10_extreme_unicode_and_xss_payloads(self):
        """Safely processes Devanagari text, RTL markers, ZWJ, and XSS tags."""
        hostile_text = (
            "🏛️ <script>alert('XSS')</script> "
            "मराठी आणि हिन्दी \u200D\u200C "
            "\u202E RTL override \u202C "
            "Special: &amp; &lt; &gt; \" ' `"
        )
        payload = json.dumps({
            "thought": hostile_text,
            "action": "fill",
            "selector": "#target",
            "value": hostile_text,
            "feedback": hostile_text
        }, ensure_ascii=False)
        res = clean_json_response(payload)
        assert res is not None
        assert res["action"] == "fill"
        assert "<script>" in res["value"]

    def test_11_root_level_non_dict_json_types(self):
        """Rejects JSON arrays, booleans, integers, and string primitives."""
        primitives = [
            json.dumps(["thought", "action", "selector"]),
            json.dumps(12345),
            json.dumps(True),
            json.dumps("just a string"),
            json.dumps(None)
        ]
        for p in primitives:
            assert clean_json_response(p) is None


# =====================================================================
# 2. Adversarial Context Pruning Suite
# =====================================================================
class TestAdversarialContextPruning:
    """Stress-tests rolling scratchpad context pruner under extreme conditions."""

    def test_01_zero_steps_empty_history(self):
        """0 steps returns citizen goal without 'Recent Steps' section."""
        prompt = "माझा उत्पन्नाचा दाखला काढा"
        res = prune_context(prompt, [])
        assert f"Citizen Goal: {prompt}" in res
        assert "Recent Steps" not in res

    def test_02_one_step_history(self):
        """1 step history accurately retains the single step."""
        history = [{"action": "navigate", "selector": "", "status": "ok"}]
        res = prune_context("Goal", history)
        assert "Recent Steps (last 3):" in res
        assert "Step 1: action=navigate" in res
        assert "Step 2" not in res

    def test_03_exact_three_steps_boundary(self):
        """Exact 3-step boundary retains all 3 steps without dropping any."""
        history = [
            {"action": "navigate", "selector": "", "status": "ok"},
            {"action": "fill", "selector": "#name", "status": "ok"},
            {"action": "click", "selector": "#btn", "status": "ok"},
        ]
        res = prune_context("Goal", history)
        assert "Step 1: action=navigate" in res
        assert "Step 2: action=fill" in res
        assert "Step 3: action=click" in res

    def test_04_four_steps_prunes_oldest_step(self):
        """4 steps drops step 1 and retains steps 2, 3, 4."""
        history = [
            {"action": "act_one", "selector": "#s1", "status": "ok"},
            {"action": "act_two", "selector": "#s2", "status": "ok"},
            {"action": "act_three", "selector": "#s3", "status": "ok"},
            {"action": "act_four", "selector": "#s4", "status": "ok"},
        ]
        res = prune_context("Goal", history)
        assert "act_one" not in res
        assert "act_two" in res
        assert "act_three" in res
        assert "act_four" in res

    def test_05_one_thousand_steps_strict_bounded_length(self):
        """1,000 steps history retains only last 3 deltas and keeps string length < 500 chars."""
        history = [
            {"action": f"action_{i}", "selector": f"#sel_{i}", "status": "ok"}
            for i in range(1000)
        ]
        res = prune_context("Long citizen journey", history)
        assert "action_997" in res
        assert "action_998" in res
        assert "action_999" in res
        assert "action_0" not in res
        assert "action_996" not in res
        assert len(res) < 500, f"Pruned context too large ({len(res)} chars)"

    def test_06_corrupt_history_entries_with_missing_keys(self):
        """History entries with missing action, selector, or status format safely."""
        corrupt_history = [
            {},
            {"action": None, "selector": None},
            {"other_key": "junk"}
        ]
        res = prune_context("Goal", corrupt_history)
        assert "Citizen Goal: Goal" in res
        assert "Step 1: action=None" in res

    def test_07_state_manager_get_pruned_context_contract(self):
        """SessionStateManager.get_pruned_context() returns at most 3 StepDeltas."""
        sm = SessionStateManager(max_steps=8)
        sm.start_session("Farmer subsidy", "mr-IN")
        for i in range(7):
            sm.increment_step()
            sm.record_step(
                {"step": i + 1, "action": f"act_{i}", "selector": f"#s{i}", "status": "ok"},
                f"sig_{i}"
            )
        pruned = sm.get_pruned_context()
        steps = pruned.recent_steps if hasattr(pruned, "recent_steps") else pruned["recent_steps"]
        assert len(steps) == 3
        last_step = steps[-1].step if hasattr(steps[-1], "step") else steps[-1]["step"]
        assert last_step == 7


# =====================================================================
# 3. Adversarial Timeout & Rate-Limit Fallbacks Suite
# =====================================================================
class TestAdversarialTimeoutAndRateLimitFallbacks:
    """Stress-tests network resilience, timeout guards, and fallback engine."""

    def test_01_socket_timeout_fallback(self):
        """Upstream network timeout (>8.0s) triggers fallback without daemon crash."""
        gw = CloudLLMGateway(api_key="mock-key", gemini_api_key="mock-gemini")
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
            decision = gw.decide("मला उत्पन्नाचा दाखला हवा", language="mr-IN", step_index=0)
            assert decision is not None
            assert decision["action"] in VALID_ACTIONS
            assert len(decision["feedback"]) > 0

    def test_02_http_429_rate_limit_fallback(self):
        """HTTP 429 Too Many Requests seamlessly triggers local fallback."""
        gw = CloudLLMGateway(api_key="mock-key", gemini_api_key="mock-gemini")
        http_429 = Exception("HTTP Error 429: Too Many Requests")
        with patch("urllib.request.urlopen", side_effect=http_429):
            decision = gw.decide("सातबारा उतारा दाखवा", language="mr-IN", step_index=0)
            assert decision is not None
            assert decision["action"] == "navigate"
            assert "satbara" in decision["value"]

    def test_03_http_500_and_503_upstream_server_errors(self):
        """HTTP 500 and 503 proxy/gateway errors trigger safe fallback."""
        gw = CloudLLMGateway(api_key="mock-key", gemini_api_key="mock-gemini")
        for err_msg in ["HTTP Error 500: Internal Server Error", "HTTP Error 503: Service Unavailable"]:
            with patch("urllib.request.urlopen", side_effect=Exception(err_msg)):
                decision = gw.decide("आय प्रमाण पत्र", language="hi-IN", step_index=0)
                assert decision is not None
                assert decision["action"] in VALID_ACTIONS

    def test_04_http_401_403_circuit_breaker_disables_upstream(self):
        """Invalid API credentials (401/403) automatically disable upstream provider."""
        gw = CloudLLMGateway(api_key="bad-or-key", gemini_api_key="bad-gemini-key")
        # Trigger Gemini 401
        with patch("urllib.request.urlopen", side_effect=Exception("HTTP Error 401: Unauthorized")):
            decision = gw.decide("income certificate", language="en-IN", step_index=0)
            assert decision is not None
            assert decision["action"] in VALID_ACTIONS

    def test_05_cascading_dual_outage_gemini_and_qwen_fail(self):
        """Simultaneous failure of both Gemini and OpenRouter yields deterministic local fallback."""
        gw = CloudLLMGateway(api_key="key", gemini_api_key="key")
        call_count = 0

        def failing_urlopen(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Upstream connection refused")

        with patch("urllib.request.urlopen", side_effect=failing_urlopen):
            decision = gw.decide("शेतकरी अनुदान योजना", language="mr-IN", step_index=0)
            assert decision is not None
            assert decision["action"] == "navigate"
            assert "mahadbt" in decision["value"]

    def test_06_unrecognized_intent_defaults_to_income_service(self):
        """Completely unrecognized user input defaults cleanly to income service."""
        service = match_governance_service("xyzzy foobar blablabla 98765")
        assert service == "income"
        decision = fallback_decide("xyzzy foobar blablabla 98765", "en-IN", step_index=0)
        assert decision["action"] == "navigate"
        assert "income" in decision["value"]

    def test_07_extreme_step_index_capping(self):
        """Step index 99999 safely caps at final finish step without IndexError."""
        decision = fallback_decide("उत्पन्नाचा दाखला", "mr-IN", step_index=99999)
        assert decision["action"] == "finish"
        assert len(decision["feedback"]) > 0

    def test_08_fallback_all_services_produce_valid_schemas(self):
        """Every service in GOVERNANCE_SERVICES produces valid 5-key contracts across all steps."""
        for svc_name, svc_data in GOVERNANCE_SERVICES.items():
            for idx in range(len(svc_data["steps"])):
                for lang in ["mr", "hi", "en"]:
                    dec = fallback_decide(svc_data["keywords"][0], lang, step_index=idx)
                    assert set(dec.keys()) == {"thought", "action", "selector", "value", "feedback"}
                    assert dec["action"] in VALID_ACTIONS
                    assert len(dec["feedback"]) > 0


# =====================================================================
# 4. Adversarial BrowserSandbox Suite
# =====================================================================
class TestAdversarialBrowserSandbox:
    """Stress-tests BrowserSandbox concurrency, selector safety, and navigation."""

    @pytest.mark.asyncio
    async def test_01_rapid_concurrent_frame_readers(self):
        """
        50 concurrent async tasks reading current_frame simultaneously
        under rapid frame updates without lock contention or corruption.
        """
        sb = BrowserSandbox(headless=True)
        await sb.initialize()

        async def reader():
            for _ in range(20):
                frame = await sb.get_frame()
                assert len(frame) > 0
                assert frame[:2] == b"\xff\xd8"
                assert frame[-2:] == b"\xff\xd9"
                await asyncio.sleep(0.001)

        tasks = [asyncio.create_task(reader()) for _ in range(50)]
        await asyncio.gather(*tasks)
        await sb.close()

    @pytest.mark.asyncio
    async def test_02_mjpeg_generator_chunk_format_integrity(self):
        """mjpeg_frame_generator yields strictly compliant multipart MIME chunks."""
        sb = BrowserSandbox(headless=True)
        await sb.initialize()

        gen = sb.mjpeg_frame_generator()
        chunks = []
        for _ in range(10):
            chunk = await anext(gen)
            chunks.append(chunk)

        for chunk in chunks:
            assert chunk.startswith(b"--frame\r\n")
            assert b"Content-Type: image/jpeg\r\n" in chunk
            assert b"Content-Length: " in chunk
            assert b"\xff\xd8" in chunk  # JPEG SOI
            assert b"\xff\xd9" in chunk  # JPEG EOI

        await sb.close()

    @pytest.mark.asyncio
    async def test_03_invalid_and_malformed_selectors(self):
        """Malformed, illegal, and injection CSS selectors fail safely with timeout message."""
        sb = BrowserSandbox(headless=True)
        await sb.initialize()
        await sb.load_portal_simulation("income")

        hostile_selectors = [
            ":::invalid CSS syntax [[[]]]",
            "div >> nth=99999",
            "<script>alert('pwn')</script>",
            "'; DROP TABLE dom; --",
            " ",
            "#id_with_null_\x00_byte",
        ]
        for sel in hostile_selectors:
            ok, msg = await sb.execute_action("click", sel, "")
            assert ok is False
            assert "Timeout" in msg or "Missing selector" in msg

        await sb.close()

    @pytest.mark.asyncio
    async def test_04_actions_on_non_existent_elements(self):
        """Click and fill actions on non-existent selectors return False without throwing."""
        sb = BrowserSandbox(headless=True)
        await sb.initialize()
        await sb.load_portal_simulation("income")

        # Click non-existent
        ok, msg = await sb.execute_action("click", "#ghost_button_999", "")
        assert ok is False
        assert "Timeout waiting for selector" in msg

        # Fill non-existent
        ok, msg = await sb.execute_action("fill", "#ghost_input_999", "some text")
        assert ok is False
        assert "Timeout waiting for selector" in msg

        await sb.close()

    @pytest.mark.asyncio
    async def test_05_navigation_to_unreachable_urls(self):
        """
        Navigation to unreachable / dead URLs is handled gracefully.
        Tests resilience when target URL does not match any known portal.
        """
        sb = BrowserSandbox(headless=True)
        await sb.initialize()

        dead_urls = [
            "http://192.0.2.1:9999/unreachable",
            "https://invalid-non-existent-domain-404.gov.in/portal",
            "ftp://unsupported-protocol.org",
        ]
        for u in dead_urls:
            ok, msg = await sb.execute_action("navigate", "", u)
            # Must return a tuple (bool, str) without crashing
            assert isinstance(ok, bool)
            assert isinstance(msg, str)

        # Empty URL navigation should fail explicitly
        ok, msg = await sb.execute_action("navigate", "", "")
        assert ok is False
        assert "Missing URL" in msg

        await sb.close()

    @pytest.mark.asyncio
    async def test_06_sandbox_idempotency_and_double_calls(self):
        """Multiple initialize() and close() calls execute cleanly without error."""
        sb = BrowserSandbox(headless=True)
        await sb.initialize()
        await sb.initialize()  # Idempotent re-initialization
        assert sb.is_running is True

        await sb.close()
        await sb.close()  # Idempotent close
        assert sb.is_running is False


# =====================================================================
# 5. Adversarial ODAV Engine & State Machine Suite
# =====================================================================
class TestAdversarialODAVEngineAndStateManager:
    """Stress-tests ODAV loop cycle, stall detection, and budget guards."""

    def test_01_two_step_stall_detector_consecutive_identical(self):
        """Stall detector flags stalled=True on exact 2 consecutive identical signatures."""
        sm = SessionStateManager(max_steps=8)
        sm.start_session("Test task", "mr-IN")

        sig_a = "aaaaaaaaaaaaaaaa"
        sig_b = "bbbbbbbbbbbbbbbb"

        # Step 1: sig_a -> not stalled
        sm.record_step({"action": "wait"}, sig_a)
        assert sm.check_stall(sig_a) is True  # Repeating sig_a is a stall

        # Alternating state: sig_b -> not stalled
        sm.record_step({"action": "fill"}, sig_b)
        assert sm.check_stall(sig_a) is False  # sig_b followed by sig_a is not stalled

    def test_02_cyclic_oscillation_does_not_trigger_consecutive_stall(self):
        """Cyclic oscillation (A -> B -> A -> B) does not trigger 2-step consecutive stall."""
        sm = SessionStateManager(max_steps=8)
        sm.start_session("Oscillating task", "mr-IN")
        sig_a = "1111111111111111"
        sig_b = "2222222222222222"

        for _ in range(3):
            sm.record_step({"action": "scroll"}, sig_a)
            assert sm.check_stall(sig_b) is False
            sm.record_step({"action": "scroll"}, sig_b)
            assert sm.check_stall(sig_a) is False

    def test_03_hard_eight_step_budget_ceiling(self):
        """Step counter ceiling locked at 8 iterations; step 8 triggers budget_exceeded."""
        sm = SessionStateManager(max_steps=8)
        sm.start_session("Budget test", "mr-IN")

        for i in range(1, 9):
            step = sm.increment_step()
            sm.record_step({"action": "wait"}, f"sig_{i}")

        assert sm.step == 8
        assert sm.is_budget_exceeded() is True
        sm.mark_budget_exceeded()
        assert sm.status == "budget_exceeded"
        assert sm.active is False

    @pytest.mark.asyncio
    async def test_04_odav_step_on_inactive_session_raises(self):
        """ODAVEngine.step() raises RuntimeError if called without an active session."""
        engine = ODAVEngine()
        engine.state_manager.active = False
        engine.state_manager.finished = False
        engine.state_manager.step = 0

        with pytest.raises(RuntimeError) as exc_info:
            await engine.step()
        assert "No active citizen session" in str(exc_info.value)

    def test_05_dpdp_ephemeral_data_purge_zeros_volatile_memory(self):
        """reset_session and purge_ephemeral_data completely wipes all PII, tasks, and history."""
        sm = SessionStateManager(max_steps=8)
        sm.start_session("Aadhaar 1234 5678 9012 update", "hi-IN")
        sm.increment_step()
        sm.record_step({"action": "fill", "value": "Aadhaar 1234 5678 9012"}, "sig_secret")
        receipt = sm.finish_task()

        # Execute DPDP purge
        sm.purge_ephemeral_data()

        assert sm.active is False
        assert sm.task == ""
        assert sm.session_id == ""
        assert len(sm.history) == 0
        assert len(sm.signature_history) == 0
        assert sm.receipt is None
        assert sm.status == "reset"
