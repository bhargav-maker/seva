"""
vdak-host/bridge/vm_client.py
OpenRouter API Client & Strict JSON Action Schema Validator for SEVA AI.
Communicates with Qwen 2.5 7B Instruct to synthesize discrete browser actions.
Enforces the 6-key JSON contract and handles timeouts with resilient local fallbacks.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger("vdak.bridge.vm_client")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen-2.5-7b-instruct"
DEFAULT_TIMEOUT_SEC = 8.0

REQUIRED_SCHEMA_KEYS = ["thought", "intent", "action", "selector", "value", "feedback"]
VALID_ACTIONS = ["navigate", "click", "fill", "scroll", "wait", "finish", "fail"]
VALID_INTENTS = ["search_service", "fill_form", "navigate_menu", "click_action", "verify_output", "finish", "error_recovery"]

SYSTEM_PROMPT = """You are SEVA AI, an autonomous browser engine executing citizen public services on Indian government portals.
You operate strictly within an Observe-Decide-Act-Verify (ODAV) loop.

Analyze the active page URL and the extracted top 25 interactive DOM nodes.
Select the single next browser action to advance towards the citizen's goal.

MANDATORY OUTPUT FORMAT:
You MUST respond ONLY with a raw JSON object (zero markdown formatting, zero backticks).
The JSON object MUST contain exactly these 6 keys:
{
  "thought": "<Technical deduction from the observed DOM nodes>",
  "intent": "<search_service | fill_form | navigate_menu | click_action | verify_output | finish>",
  "action": "<navigate | click | fill | scroll | wait | finish | fail>",
  "selector": "<CSS selector or element text/ID>",
  "value": "<Text to type, URL to open, or empty string>",
  "feedback": "<Short spoken voice confirmation in citizen language>"
}
"""

def sanitize_json_markdown(raw_text: str) -> str:
    """Strips Markdown code fences and leading/trailing whitespace."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def validate_action_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    """Validates adherence to the PRD Section 5.1 JSON action contract."""
    for key in REQUIRED_SCHEMA_KEYS:
        if key not in payload:
            raise ValueError(f"Schema violation: missing required key '{key}'")
        if not isinstance(payload[key], str):
            payload[key] = str(payload[key])

    action = payload["action"].lower()
    if action not in VALID_ACTIONS:
        raise ValueError(f"Schema violation: invalid action '{action}'. Must be one of {VALID_ACTIONS}")
    payload["action"] = action

    return {k: payload[k] for k in REQUIRED_SCHEMA_KEYS}

class VMClient:
    """Manages inference communication with OpenRouter and schema enforcement."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model
        self.timeout = DEFAULT_TIMEOUT_SEC

    async def decide_next_action(
        self,
        goal: str,
        recent_history: List[Dict[str, Any]],
        url: str,
        dom_elements: List[Dict[str, Any]],
        language: str = "mr"
    ) -> Dict[str, str]:
        """
        Sends the compacted ODAV context to the Qwen 2.5 7B brain.
        Falls back to local heuristic rules if the network times out (> 8s) or fails.
        """
        user_prompt = {
            "citizen_goal": goal,
            "language": language,
            "current_url": url,
            "recent_actions": recent_history,
            "top_dom_nodes": dom_elements[:25]
        }

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False, indent=2)}
        ]

        if not self.api_key:
            logger.warning("[VMClient] OPENROUTER_API_KEY not set. Using local deterministic fallback.")
            return self._local_heuristic_fallback(goal, url, dom_elements, language)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://seva-ai.kiosk.internal",
            "X-Title": "SEVA AI Kiosk Platform"
        }

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 350
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(OPENROUTER_API_URL, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                
                cleaned = sanitize_json_markdown(raw_content)
                parsed = json.loads(cleaned)
                validated = validate_action_payload(parsed)
                return validated
        except Exception as e:
            logger.error(f"[VMClient] Inference failed ({type(e).__name__}: {e}). Triggering fallback.")
            return self._local_heuristic_fallback(goal, url, dom_elements, language)

    def _local_heuristic_fallback(
        self,
        goal: str,
        url: str,
        dom_elements: List[Dict[str, Any]],
        language: str
    ) -> Dict[str, str]:
        """
        Deterministic, rule-based fallback for standard citizen services
        ensuring the kiosk never crashes on network loss.
        """
        lower_goal = goal.lower()
        feedback_mr = "सरकारी पोर्टल तपासत आहे."
        feedback_hi = "सरकारी पोर्टल की जांच की जा रही है."
        feedback = feedback_mr if language == "mr" else feedback_hi

        # If not on any portal yet, navigate to portal hub
        if not url or url == "about:blank":
            if "income" in lower_goal or "उत्पन्न" in goal:
                return {
                    "thought": "Direct navigation to Aaple Sarkar Income Certificate portal.",
                    "intent": "navigate_menu",
                    "action": "navigate",
                    "selector": "",
                    "value": "http://localhost:8000/mock_portals/income.html",
                    "feedback": "उत्पन्नाचा दाखला पोर्टल उघडत आहे." if language == "mr" else "आय प्रमाण पत्र पोर्टल खोला जा रहा है."
                }
            elif "7/12" in lower_goal or "सातबारा" in goal or "land" in lower_goal:
                return {
                    "thought": "Direct navigation to Mahabhulekh 7/12 Land Records portal.",
                    "intent": "navigate_menu",
                    "action": "navigate",
                    "selector": "",
                    "value": "http://localhost:8000/mock_portals/satbara.html",
                    "feedback": "७/१२ उतारा पोर्टल उघडत आहे." if language == "mr" else "७/१२ भूलेख पोर्टल खोला जा रहा है."
                }
            elif "ration" in lower_goal or "रेशन" in goal:
                return {
                    "thought": "Direct navigation to AePDS Ration Services portal.",
                    "intent": "navigate_menu",
                    "action": "navigate",
                    "selector": "",
                    "value": "http://localhost:8000/mock_portals/ration.html",
                    "feedback": "रेशन कार्ड पोर्टल उघडत आहे." if language == "mr" else "राशन कार्ड पोर्टल खोला जा रहा है."
                }

        # Check for submit / finish buttons
        for elem in dom_elements:
            text = elem.get("text", "").lower()
            tag = elem.get("tag", "").lower()
            sel = elem.get("selector", "")
            if "submit" in text or "अर्ज करा" in text or "दाखल करा" in text:
                return {
                    "thought": f"Submitting active form via {sel}.",
                    "intent": "click_action",
                    "action": "click",
                    "selector": sel,
                    "value": "",
                    "feedback": "अर्ज सादर करत आहे." if language == "mr" else "आवेदन जमा किया जा रहा है."
                }
            if "download" in text or "पावती" in text or "receipt" in text:
                return {
                    "thought": "Transaction complete. Emitting finish action.",
                    "intent": "finish",
                    "action": "finish",
                    "selector": sel,
                    "value": "",
                    "feedback": "आपला अर्ज पूर्ण झाला आहे." if language == "mr" else "आपका आवेदन पूर्ण हो गया है."
                }

        return {
            "thought": "Awaiting page readiness.",
            "intent": "verify_output",
            "action": "wait",
            "selector": "",
            "value": "1000",
            "feedback": feedback
        }
