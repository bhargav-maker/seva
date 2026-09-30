"""
tests/test_phase1_schema.py
Validates Phase 1 Delivery Milestone:
100% valid JSON returned across 25 synthetic Marathi, Hindi, and English requests.
Checks strict adherence to schema:
  { "thought": str, "action": str, "selector": str, "value": str, "feedback": str }
  action in ["navigate", "click", "fill", "scroll", "wait", "finish"]
"""

import sys
import os
import json
from pathlib import Path

# Ensure Windows stdout/stderr supports Devanagari Unicode (Marathi/Hindi)
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.llm_client import (
    CloudLLMGateway,
    clean_json_response,
    prune_context,
    VALID_ACTIONS,
    fallback_decide,
    decide_action,
    GOVERNANCE_SERVICES
)
from backend.models import (
    LLMDecision,
    DOMElement,
    StepDelta,
    PrunedContext,
    SessionState,
    StartTaskRequest,
    StartTaskResponse,
    StepResponse,
    ResetResponse
)

SYNTHETIC_PROMPTS = [
    # Marathi Requests (10)
    ("मला उत्पन्नाचा दाखला काढायचा आहे", "mr-IN"),
    ("तहसीलदार साहेबांचा वार्षिक उत्पन्नाचा दाखला कसा मिळेल?", "mr-IN"),
    ("संजय गांधी निराधार पेन्शन योजना अर्ज भरायचा आहे", "mr-IN"),
    ("वृद्धापकाळ पेन्शनसाठी मला नोंदणी करायची आहे", "mr-IN"),
    ("आमच्या शेताचा सातबारा उतारा दाखवा", "mr-IN"),
    ("७/१२ गट क्रमांक ४२ चा फेरफार उतारा पाहिजे", "mr-IN"),
    ("जात प्रमाणपत्र पडताळणीसाठी काय करावे लागेल?", "mr-IN"),
    ("रेशन कार्डामध्ये नाव वाढवायचे आहे", "mr-IN"),
    ("नवीन शेतकरी अनुदानासाठी अर्ज करा", "mr-IN"),
    ("माझे आधार कार्ड लिंक आहे का तपासा", "mr-IN"),

    # Hindi Requests (10)
    ("मुझे आय प्रमाण पत्र बनवाना है", "hi-IN"),
    ("तहसील से 50000 रुपये का आय प्रमाण पत्र कैसे मिलेगा?", "hi-IN"),
    ("संजय गांधी निराधार योजना के लिए आवेदन करना है", "hi-IN"),
    ("वृद्धावस्था पेंशन फार्म भरना है", "hi-IN"),
    ("मुझे अपने खेत का खसरा खतौनी और 7/12 नकल चाहिए", "hi-IN"),
    ("भूलेख पोर्टल से जमीन का नक्शा डाउनलोड करो", "hi-IN"),
    ("जाति प्रमाण पत्र सत्यापन करना है", "hi-IN"),
    ("राशन कार्ड में नया सदस्य जोड़ना है", "hi-IN"),
    ("किसान सम्मान निधि का स्टेटस चेक करो", "hi-IN"),
    ("आवास योजना के लिए नया फार्म खोलिए", "hi-IN"),

    # English / Hinglish Requests (5)
    ("I want to apply for an Income Certificate", "en-IN"),
    ("Help me apply for Niradhar destitute pension scheme", "en-IN"),
    ("Download 7/12 Satbara land records for survey 42", "en-IN"),
    ("Check my ration card subsidy status", "en-IN"),
    ("Submit caste verification documents to collector office", "en-IN")
]


def test_clean_json_response():
    print("Testing clean_json_response() parser...")
    # Raw JSON
    valid_raw = '{"thought": "OK", "action": "click", "selector": "#btn", "value": "", "feedback": "क्लिक करत आहे"}'
    res = clean_json_response(valid_raw)
    assert res is not None, "Failed on raw valid JSON"
    assert res["action"] == "click"

    # Markdown wrapped
    markdown_wrapped = '```json\n{"thought": "Navigate to portal", "action": "navigate", "selector": "", "value": "https://gov.in", "feedback": "उघडत आहे"}\n```'
    res2 = clean_json_response(markdown_wrapped)
    assert res2 is not None, "Failed on markdown wrapped JSON"
    assert res2["action"] == "navigate"

    # Invalid action
    invalid_action = '{"thought": "bad", "action": "destroy", "selector": "", "value": "", "feedback": ""}'
    assert clean_json_response(invalid_action) is None, "Should reject invalid action"

    # Missing required keys
    missing_key = '{"thought": "bad", "action": "click"}'
    assert clean_json_response(missing_key) is None, "Should reject missing keys"

    print("  [PASS] clean_json_response() tests passed.")


def test_context_pruning():
    print("Testing context pruning (rolling scratchpad)...")
    prompt = "मला उत्पन्नाचा दाखला हवा आहे"
    history = [
        {"action": "navigate", "selector": "", "status": "ok"},
        {"action": "click", "selector": "#lang", "status": "ok"},
        {"action": "click", "selector": "#services", "status": "ok"},
        {"action": "click", "selector": "#revenue", "status": "ok"},
        {"action": "fill", "selector": "#name", "status": "ok"},
    ]
    summary = prune_context(prompt, history)
    assert "Citizen Goal" in summary
    assert "Recent Steps (last 3):" in summary
    # Only 3 steps must remain
    lines = [l for l in summary.split("\n") if "Step " in l]
    assert len(lines) == 3, f"Expected 3 pruned steps, got {len(lines)}"

    # Empty history edge case
    empty_summary = prune_context(prompt, [])
    assert "Citizen Goal" in empty_summary
    assert "Recent Steps" not in empty_summary

    print("  [PASS] Context pruning tests passed.")


def test_pydantic_models():
    print("Testing Pydantic models in backend/models.py...")
    # LLMDecision valid instance
    decision = LLMDecision(
        thought="Navigating to portal",
        action="navigate",
        selector="",
        value="http://127.0.0.1:8000/portal/income",
        feedback="पोर्टल उघडत आहे"
    )
    d_dict = decision.to_dict()
    assert d_dict["action"] == "navigate"
    assert d_dict["value"] == "http://127.0.0.1:8000/portal/income"
    assert "thought" in d_dict
    assert "feedback" in d_dict

    # Action case normalization
    decision_upper = LLMDecision(
        thought="Clicking button",
        action="CLICK",  # type: ignore
        selector="#btn",
        value="",
        feedback="क्लिक करत आहे"
    )
    assert decision_upper.action == "click"

    # Invalid action rejected
    try:
        LLMDecision(
            thought="Bad",
            action="delete_database",  # type: ignore
            selector="",
            value="",
            feedback=""
        )
        assert False, "Should have raised ValueError on invalid action"
    except Exception:
        pass

    # DOMElement
    elem = DOMElement(tag="button", id="submit_btn", text="Submit", role="button")
    assert elem.tag == "button"
    assert elem.id == "submit_btn"

    # StepDelta & PrunedContext
    delta = StepDelta(step=1, action="navigate", status="ok", url="http://127.0.0.1:8000")
    pruned = PrunedContext(citizen_goal="Income cert", recent_steps=[delta])
    assert len(pruned.recent_steps) == 1
    assert "Citizen Goal: Income cert" in pruned.format_prompt_summary()

    # SessionState & REST responses
    st_req = StartTaskRequest(task="मला दाखला हवा", language="mr-IN")
    assert st_req.task == "मला दाखला हवा"

    st_resp = StartTaskResponse(session_id="test-uuid-1234")
    assert st_resp.status == "started"
    assert st_resp.session_id == "test-uuid-1234"

    step_resp = StepResponse(
        step=1,
        state_signature="abcdef0123456789",
        action=decision.to_dict(),
        stalled=False,
        status="progressing"
    )
    assert step_resp.step == 1
    assert step_resp.stalled is False

    sess = SessionState(session_id="test-uuid-1234", active=True, step=1)
    assert sess.active is True
    assert sess.max_steps == 8

    reset_resp = ResetResponse()
    assert reset_resp.purged is True

    print("  [PASS] Pydantic models tests passed.")


def test_decide_action_contract():
    print("Testing PROJECT.md decide_action() interface contract...")
    res = decide_action(
        goal="मला उत्पन्नाचा दाखला काढायचा आहे",
        history=[],
        url="http://127.0.0.1:8000",
        dom_elements=[{"tag": "button", "id": "apply_btn"}],
        language="mr"
    )
    assert isinstance(res, dict), "decide_action must return dict"
    for field in ["thought", "action", "selector", "value", "feedback"]:
        assert field in res, f"Missing required field: {field}"
        assert isinstance(res[field], str), f"Field {field} must be str"
    assert res["action"] in VALID_ACTIONS
    assert len(res["feedback"]) > 0
    print("  [PASS] decide_action() contract test passed.")


def test_governance_services_coverage():
    print("Testing Maharashtra governance services coverage (Income, Pension, Satbara, Ration)...")
    core_services = ["income", "pension", "satbara", "ration"]
    for svc in core_services:
        assert svc in GOVERNANCE_SERVICES, f"Missing core service: {svc}"
        s_data = GOVERNANCE_SERVICES[svc]
        assert len(s_data["steps"]) >= 4, f"Service {svc} has insufficient step definitions"
        # Check all steps have valid actions and multi-lingual feedbacks
        for step in s_data["steps"]:
            assert step["action"] in VALID_ACTIONS, f"Invalid action {step['action']} in {svc}"
            fb = step["feedback"]
            assert "mr" in fb and len(fb["mr"]) > 0, f"Missing Marathi feedback in {svc}"
            assert "hi" in fb and len(fb["hi"]) > 0, f"Missing Hindi feedback in {svc}"
            assert "en" in fb and len(fb["en"]) > 0, f"Missing English feedback in {svc}"
    print("  [PASS] Governance services coverage tests passed.")


def test_25_synthetic_requests():
    print("\nTesting 25 Synthetic Vernacular Requests (Phase 1 Acceptance Metric)...")
    gateway = CloudLLMGateway()

    passed = 0
    total = len(SYNTHETIC_PROMPTS)

    for i, (prompt, lang) in enumerate(SYNTHETIC_PROMPTS, 1):
        decision = gateway.decide(
            prompt=prompt,
            language=lang,
            current_url="http://127.0.0.1:8000/portal",
            dom_elements=[{"tag": "button", "id": "submit_btn", "text": "Submit"}],
            history=[],
            step_index=0
        )

        # Validate schema contract
        assert isinstance(decision, dict), f"Request {i}: Return type must be dict"
        for field in ["thought", "action", "selector", "value", "feedback"]:
            assert field in decision, f"Request {i}: Missing required field '{field}'"
            assert isinstance(decision[field], str), f"Request {i}: Field '{field}' must be str"

        assert decision["action"] in VALID_ACTIONS, f"Request {i}: Invalid action '{decision['action']}'"
        assert len(decision["feedback"]) > 0, f"Request {i}: Feedback string is empty"

        print(f"  [{i:02d}/{total}] [{lang}] \"{prompt[:30]}...\" -> {decision['action']} | \"{decision['feedback'][:30]}...\"")
        passed += 1

    success_rate = (passed / total) * 100
    print(f"\n=======================================================")
    print(f"Phase 1 Success Rate: {success_rate:.1f}% ({passed}/{total} Valid JSON Responses)")
    print(f"=======================================================")
    assert passed == total, f"Expected 100% pass rate, got {passed}/{total}"


def test_multi_step_progression():
    print("Testing multi-step workflow progression...")
    # Trace complete multi-step journey for Income Certificate in Marathi
    for step_i in range(6):
        dec = fallback_decide("मला उत्पन्नाचा दाखला हवा", "mr-IN", step_i)
        assert dec["action"] in VALID_ACTIONS
        assert len(dec["feedback"]) > 0

    # Trace Ration card in Hindi
    for step_i in range(6):
        dec = fallback_decide("राशन कार्ड में नया नाम जोड़ना है", "hi-IN", step_i)
        assert dec["action"] in VALID_ACTIONS
        assert len(dec["feedback"]) > 0

    print("  [PASS] Multi-step progression test passed.")


if __name__ == "__main__":
    test_clean_json_response()
    test_context_pruning()
    test_pydantic_models()
    test_decide_action_contract()
    test_governance_services_coverage()
    test_multi_step_progression()
    test_25_synthetic_requests()
    print("\nALL PHASE 1 TESTS PASSED SUCCESSFULLY! (100% Schema Validation)")
