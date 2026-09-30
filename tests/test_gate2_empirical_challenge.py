"""
tests/test_gate2_empirical_challenge.py
Gate 2 Adversarial Stress & Verification Test Suite for SEVA AI Kiosk Platform.

Empirically tests and challenges the 5 remediated components:
1. Hard 8-step budget ceiling clamp in SessionStateManager.
2. Two-step stall detection and mutation counter reset.
3. Ephemeral data purge & DPDP Act 2023 compliance in backend/app.py and SessionStateManager.
4. Navigation error handling for unreachable URLs in BrowserSandbox.
5. Non-greedy JSON extraction with balanced brace parsing in backend/llm_client.py.
"""

import asyncio
import concurrent.futures
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.state_manager import SessionStateManager
from backend.models import compute_state_signature
from backend.browser_sandbox import BrowserSandbox, PlaywrightSandbox
from backend.llm_client import clean_json_response, VALID_ACTIONS
import backend.app as app_module


# =====================================================================
# 1. Hard 8-Step Budget Ceiling Clamp
# =====================================================================
class TestGate2BudgetCeilingClamp:
    """Stress tests hard 8-step budget ceiling enforcement."""

    def test_01_increment_step_clamps_at_max_steps(self):
        """Repeatedly calling increment_step() past 8 never exceeds 8."""
        sm = SessionStateManager(max_steps=8)
        sm.start_session("Farmer subsidy query", "mr-IN")

        for i in range(1, 9):
            step = sm.increment_step()
            assert step == i
            assert sm.step == i

        # Step 8 reached: budget exceeded
        assert sm.is_budget_exceeded() is True

        # Now attempt 20 additional increments past the ceiling
        for extra in range(1, 21):
            clamped_step = sm.increment_step()
            assert clamped_step == 8, f"increment_step() exceeded ceiling! Returned {clamped_step}"
            assert sm.step == 8, f"sm.step exceeded ceiling! Value is {sm.step}"

        assert sm.is_budget_exceeded() is True

    def test_02_concurrent_increment_step_thread_safety(self):
        """Concurrent calls to increment_step() across 25 threads never breach ceiling."""
        sm = SessionStateManager(max_steps=8)
        sm.start_session("Concurrent budget test", "mr-IN")

        def worker_increment():
            return sm.increment_step()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_increment) for _ in range(50)]
            results = [f.result() for f in futures]

        # Max result must be 8 and final sm.step must be 8
        assert max(results) == 8
        assert sm.step == 8
        assert sm.is_budget_exceeded() is True


# =====================================================================
# 2. Two-Step Stall Detection and Mutation Reset
# =====================================================================
class TestGate2StallDetectionAndMutationReset:
    """Adversarially tests S(t) == S(t-1) 2-step stall detection."""

    def test_01_single_step_identical_does_not_flag_stall(self):
        """First occurrence of signature establishes baseline; does not flag stall."""
        sm = SessionStateManager()
        sm.start_session("Pension registration", "mr-IN")

        sig1 = "a1b2c3d4e5f67890"
        sm.record_step({"action": "navigate", "status": "ok"}, sig1)
        assert sm.stalled is False

        # Check against a different signature -> no stall
        is_stalled = sm.check_stall("f6e5d4c3b2a10987")
        assert is_stalled is False
        assert sm.stalled is False

    def test_02_consecutive_identical_signature_triggers_stall(self):
        """Identical signature across 2 consecutive cycles flags stalled=True."""
        sm = SessionStateManager()
        sm.start_session("Pension registration", "mr-IN")

        sig_fixed = "1122334455667788"
        sm.record_step({"action": "wait"}, sig_fixed)

        # Immediate repeat of same signature
        is_stalled = sm.check_stall(sig_fixed)
        assert is_stalled is True
        assert sm.stalled is True

    def test_03_mutation_resets_stall_flag(self):
        """Subsequent state mutation S(t) != S(t-1) immediately clears stalled flag."""
        sm = SessionStateManager()
        sm.start_session("Pension registration", "mr-IN")

        sig_fixed = "1122334455667788"
        sm.record_step({"action": "wait"}, sig_fixed)
        assert sm.check_stall(sig_fixed) is True
        assert sm.stalled is True

        # Mutation occurs
        sig_mutated = "9988776655443322"
        is_stalled = sm.check_stall(sig_mutated)
        assert is_stalled is False
        assert sm.stalled is False

    def test_04_empty_or_zero_signature_guards(self):
        """Empty or dummy zeros signature does not trigger false positive stall."""
        sm = SessionStateManager()
        sm.start_session("Pension registration", "mr-IN")

        sm.record_step({"action": "wait"}, "0000000000000000")
        assert sm.check_stall("0000000000000000") is False
        assert sm.check_stall("") is False
        assert sm.stalled is False


# =====================================================================
# 3. Ephemeral Data Purge & DPDP Act Compliance
# =====================================================================
class TestGate2EphemeralDataPurge:
    """Verifies complete eradication of citizen PII and session singletons."""

    def test_01_state_manager_purge_zeros_all_fields(self):
        """purge_ephemeral_data() wipes task, PII, history, and receipts."""
        sm = SessionStateManager()
        sm.start_session("Aadhaar 9999-8888-7777 Land Registry", "mr-IN")
        sm.increment_step()
        sm.record_step({"action": "fill", "value": "9999-8888-7777"}, "sig_aadhaar")
        sm.finish_task()

        assert sm.active is False
        assert sm.finished is True
        assert len(sm.history) == 1
        assert sm.receipt is not None

        # Execute DPDP purge
        sm.purge_ephemeral_data()

        assert sm.session_id == ""
        assert sm.task == ""
        assert sm.step == 0
        assert sm.active is False
        assert sm.finished is False
        assert sm.stalled is False
        assert sm.status == "reset"
        assert len(sm.history) == 0
        assert len(sm.signature_history) == 0
        assert sm.last_action is None
        assert sm.receipt is None
        assert sm.error_message is None
        assert sm.current_url == ""
        assert sm.current_signature == ""

    @pytest.mark.asyncio
    async def test_02_app_reset_session_nullifies_sandbox_singleton(self):
        """reset_session() in app.py closes sandbox and nullifies _sandbox global."""
        # Setup mock active sandbox
        mock_sandbox = AsyncMock()
        mock_sandbox.is_running = True
        mock_sandbox.close = AsyncMock()

        app_module._sandbox = mock_sandbox
        app_module._odav_engine = MagicMock()

        response = await app_module.reset_session()
        assert response.status == "reset"
        assert response.purged is True

        # Verify sandbox was closed
        mock_sandbox.close.assert_awaited_once()

        # Verify global singletons were explicitly nullified
        assert app_module._sandbox is None
        assert app_module._odav_engine is None

    @pytest.mark.asyncio
    async def test_03_sandbox_close_clears_internal_buffers(self):
        """BrowserSandbox.close() zeros frames, tracker, active portal and flags."""
        sb = BrowserSandbox(headless=True)
        sb._current_frame = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        sb._frame_count = 50
        sb._fps_tracker = [1.0, 2.0, 3.0]
        sb._active_portal = "income"
        sb._submitted = True
        sb._is_running = True

        await sb.close()

        assert sb.is_running is False
        assert sb.current_frame == b""
        assert sb._frame_count == 0
        assert len(sb._fps_tracker) == 0
        assert sb._active_portal == ""
        assert sb._submitted is False


# =====================================================================
# 4. Navigation Error Handling for Unreachable URLs
# =====================================================================
class TestGate2NavigationErrorHandling:
    """Tests navigation rejection for unreachable and invalid URLs."""

    @pytest.mark.asyncio
    async def test_01_execute_action_unreachable_ip(self):
        """execute_action rejects RFC 5737 testnet unreachable IP 192.0.2.1."""
        sb = BrowserSandbox(headless=True)
        # Mock initialize to avoid launching browser process during unit test
        sb.initialize = AsyncMock(return_value=True)
        sb._is_running = True
        sb._page = MagicMock()

        success, msg = await sb.execute_action("navigate", value="http://192.0.2.1:9999")
        assert success is False
        assert "unreachable" in msg.lower() or "failed" in msg.lower()

    @pytest.mark.asyncio
    async def test_02_execute_action_unreachable_keyword(self):
        """execute_action rejects URLs containing 'unreachable'."""
        sb = BrowserSandbox(headless=True)
        sb.initialize = AsyncMock(return_value=True)
        sb._is_running = True
        sb._page = MagicMock()

        success, msg = await sb.execute_action("navigate", selector="http://unreachable-host.gov.in")
        assert success is False
        assert "unreachable" in msg.lower()

    def test_03_sync_execute_action_unreachable_ip(self):
        """_sync_execute_action rejects unreachable IP."""
        sb = BrowserSandbox(headless=True)
        sb._is_running = True

        success, msg = sb._sync_execute_action("navigate", value="http://192.0.2.1:8080")
        assert success is False
        assert "unreachable" in msg.lower()

    @pytest.mark.asyncio
    async def test_04_execute_action_missing_url(self):
        """execute_action returns False when URL is empty."""
        sb = BrowserSandbox(headless=True)
        sb.initialize = AsyncMock(return_value=True)
        sb._is_running = True
        sb._page = MagicMock()

        success, msg = await sb.execute_action("navigate", selector="", value="")
        assert success is False
        assert "missing url" in msg.lower()


# =====================================================================
# 5. Non-Greedy JSON Extraction with Balanced Braces
# =====================================================================
class TestGate2NonGreedyJSONExtraction:
    """Tests clean_json_response against adversarial inputs with trailing braces."""

    def test_01_trailing_commentary_with_braces(self):
        """Trailing text containing braces does not corrupt root JSON extraction."""
        raw = (
            'Here is the requested action:\n'
            '{\n'
            '  "thought": "Open the income certificate portal",\n'
            '  "action": "navigate",\n'
            '  "selector": "/portal/income",\n'
            '  "value": "/portal/income",\n'
            '  "feedback": "उत्पन्नाचा दाखला उघडत आहे."\n'
            '}\n'
            'Note to user: The parameter {service_id} will be mapped to {portal_name}.'
        )
        parsed = clean_json_response(raw)
        assert parsed is not None
        assert parsed["action"] == "navigate"
        assert parsed["selector"] == "/portal/income"
        assert parsed["feedback"] == "उत्पन्नाचा दाखला उघडत आहे."

    def test_02_markdown_wrapped_json_with_codeblock(self):
        """Markdown codeblocks ```json ... ``` are cleanly unwrapped."""
        raw = (
            '```json\n'
            '{\n'
            '  "thought": "Submit the form",\n'
            '  "action": "click",\n'
            '  "selector": "#submit_btn",\n'
            '  "value": "",\n'
            '  "feedback": "अर्ज सादर करत आहे."\n'
            '}\n'
            '```'
        )
        parsed = clean_json_response(raw)
        assert parsed is not None
        assert parsed["action"] == "click"
        assert parsed["selector"] == "#submit_btn"

    def test_03_paired_braces_inside_string_values(self):
        """Paired curly braces inside string values (e.g. templates) are preserved."""
        raw = (
            '{\n'
            '  "thought": "Checking template selector {btn_id}",\n'
            '  "action": "wait",\n'
            '  "selector": "",\n'
            '  "value": "",\n'
            '  "feedback": "कृपया प्रतीक्षा करा {5s}."\n'
            '}'
        )
        parsed = clean_json_response(raw)
        assert parsed is not None
        assert parsed["action"] == "wait"
        assert "{btn_id}" in parsed["thought"]

    def test_04_invalid_action_rejected(self):
        """JSON with unrecognized action primitive is rejected."""
        raw = (
            '{\n'
            '  "thought": "Illegal action",\n'
            '  "action": "delete_database",\n'
            '  "selector": "",\n'
            '  "value": "",\n'
            '  "feedback": "error"\n'
            '}'
        )
        parsed = clean_json_response(raw)
        assert parsed is None

    def test_05_missing_required_keys_rejected(self):
        """JSON missing required schema keys returns None."""
        raw = '{"thought": "incomplete", "action": "wait"}'
        parsed = clean_json_response(raw)
        assert parsed is None
