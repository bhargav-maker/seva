"""
Unit tests validating PRD contracts, schema enforcement, and loop invariants for SEVA AI.
Strictly checks:
1. Strict 6-key JSON Schema (thought, intent, action, selector, value, feedback)
2. Markdown code-fence stripping
3. Context compaction (k=3 rolling window)
4. State signature calculation & 2-step stall detector
5. Hard step budget ceiling (N=8)
"""

import json
import hashlib
from typing import Dict, Any, List

REQUIRED_SCHEMA_KEYS = ["thought", "intent", "action", "selector", "value", "feedback"]
VALID_ACTIONS = ["navigate", "click", "fill", "scroll", "wait", "finish", "fail"]

def validate_action_schema(data: Any) -> Dict[str, str]:
    """Validates raw data or string against PRD Section 5.1 JSON contract."""
    if isinstance(data, str):
        # Strip code fences if present
        text = data.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        payload = json.loads(text)
    elif isinstance(data, dict):
        payload = data
    else:
        raise ValueError(f"Expected dict or JSON str, got {type(data)}")

    for key in REQUIRED_SCHEMA_KEYS:
        if key not in payload:
            raise ValueError(f"Missing required key: '{key}'")
        if not isinstance(payload[key], str):
            raise TypeError(f"Value for '{key}' must be str, got {type(payload[key])}")

    if payload["action"] not in VALID_ACTIONS:
        raise ValueError(f"Invalid action '{payload['action']}'. Must be one of {VALID_ACTIONS}")

    return {k: payload[k] for k in REQUIRED_SCHEMA_KEYS}

def compute_state_signature(url: str, title: str, dom_summary: str) -> str:
    """Computes deterministic 16-hex character state signature S(t)."""
    raw = f"{url}|{title}|{dom_summary}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

def prune_context(goal: str, history: List[Dict[str, Any]], k: int = 3) -> Dict[str, Any]:
    """Prunes history to retain original goal and last k steps."""
    return {
        "goal": goal,
        "recent_steps": history[-k:] if len(history) > k else list(history),
        "total_steps_executed": len(history)
    }

class ODAVStateMachine:
    """Mock state machine verifying ODAV loop invariants (budget ceiling and stall counter)."""
    def __init__(self, max_steps: int = 8):
        self.max_steps = max_steps
        self.step_count = 0
        self.last_signature = None
        self.stall_count = 0
        self.finished = False

    def step(self, new_signature: str, action: str) -> Dict[str, Any]:
        if self.step_count >= self.max_steps:
            return {"status": "budget_exhausted", "step": self.step_count}
        
        self.step_count += 1
        
        if self.last_signature is not None and new_signature == self.last_signature:
            self.stall_count += 1
        else:
            self.stall_count = 0
            
        self.last_signature = new_signature

        if action == "finish":
            self.finished = True
            return {"status": "finished", "step": self.step_count}

        if self.stall_count >= 2:
            return {"status": "stalled", "step": self.step_count, "stall_count": self.stall_count}

        if self.step_count >= self.max_steps:
            return {"status": "budget_exhausted", "step": self.step_count}

        return {"status": "in_progress", "step": self.step_count}

# Test Cases
def test_schema_valid():
    valid_raw = {
        "thought": "Locate search input",
        "intent": "search_service",
        "action": "fill",
        "selector": "#search-box",
        "value": "Income Certificate",
        "feedback": "उत्पन्नाचा दाखला शोधत आहे"
    }
    result = validate_action_schema(valid_raw)
    assert result == valid_raw

def test_schema_markdown_stripping():
    wrapped = "```json\n{\n  \"thought\": \"Click apply\",\n  \"intent\": \"click_action\",\n  \"action\": \"click\",\n  \"selector\": \".btn-apply\",\n  \"value\": \"\",\n  \"feedback\": \"अर्ज बटनावर क्लिक करत आहे\"\n}\n```"
    result = validate_action_schema(wrapped)
    assert result["action"] == "click"
    assert result["intent"] == "click_action"

def test_schema_missing_key():
    invalid = {
        "thought": "Missing action",
        "intent": "search",
        "selector": "",
        "value": "",
        "feedback": ""
    }
    try:
        validate_action_schema(invalid)
        assert False, "Should raise ValueError for missing action"
    except ValueError as e:
        assert "action" in str(e)

def test_schema_invalid_action():
    invalid = {
        "thought": "Invalid action name",
        "intent": "search",
        "action": "jump",
        "selector": "",
        "value": "",
        "feedback": ""
    }
    try:
        validate_action_schema(invalid)
        assert False, "Should raise ValueError for invalid action"
    except ValueError as e:
        assert "Invalid action 'jump'" in str(e)

def test_context_compaction():
    history = [{"step": i, "action": f"action_{i}"} for i in range(10)]
    compact = prune_context("Get 7/12 record", history, k=3)
    assert compact["goal"] == "Get 7/12 record"
    assert len(compact["recent_steps"]) == 3
    assert compact["recent_steps"][0]["step"] == 7
    assert compact["recent_steps"][2]["step"] == 9
    assert compact["total_steps_executed"] == 10

def test_state_signature_deterministic():
    s1 = compute_state_signature("https://aaplesarkar.mahaonline.gov.in", "Home", "12 buttons")
    s2 = compute_state_signature("https://aaplesarkar.mahaonline.gov.in", "Home", "12 buttons")
    s3 = compute_state_signature("https://aaplesarkar.mahaonline.gov.in", "Services", "12 buttons")
    assert s1 == s2
    assert len(s1) == 16
    assert s1 != s3

def test_budget_ceiling_max_8():
    sm = ODAVStateMachine(max_steps=8)
    for i in range(7):
        res = sm.step(f"sig_{i}", "click")
        assert res["status"] == "in_progress"
        assert res["step"] == i + 1
    # 8th step
    res = sm.step("sig_7", "click")
    assert res["status"] == "budget_exhausted"
    assert res["step"] == 8

def test_stall_detector_2_steps():
    sm = ODAVStateMachine(max_steps=8)
    res1 = sm.step("sig_A", "click")
    assert res1["status"] == "in_progress"
    
    # First identical signature (stall_count = 1)
    res2 = sm.step("sig_A", "click")
    assert res2["status"] == "in_progress"
    
    # Second identical signature (stall_count = 2) -> triggers stall recovery
    res3 = sm.step("sig_A", "click")
    assert res3["status"] == "stalled"
    assert res3["stall_count"] == 2

def test_finish_action_terminates():
    sm = ODAVStateMachine(max_steps=8)
    res = sm.step("sig_1", "finish")
    assert res["status"] == "finished"
    assert sm.finished is True

if __name__ == "__main__":
    test_schema_valid()
    test_schema_markdown_stripping()
    test_schema_missing_key()
    test_schema_invalid_action()
    test_context_compaction()
    test_state_signature_deterministic()
    test_budget_ceiling_max_8()
    test_stall_detector_2_steps()
    test_finish_action_terminates()
    print("ALL PRD CONTRACT ASSERTIONS PASSED (100%)")
