"""
backend/odav_engine.py
Observe-Decide-Act-Verify (ODAV) Agentic Loop Engine for SEVA AI Kiosk Platform.

Coordinates:
  1. Observe:
     - Extracts current viewport URL and up to 25 interactive DOM selectors.
     - Computes deterministic SHA-256 state signature S(t) = SHA256(url + DOM)[:16].
  2. Decide:
     - Queries LLM client with context-pruned scratchpad (goal + last 3 step deltas)
     - Validates deterministic 5-key JSON schema.
  3. Act:
     - Dispatches primitive browser action (navigate, click, fill, scroll, wait, finish)
       to Playwright Browser Sandbox.
  4. Verify:
     - Audits state mutation S(t) != S(t-1).
     - Detects stalls across 2 consecutive identical states (flags stalled=True).
     - Enforces termination gates: action="finish" (receipt generated) or step >= 8 (budget_exceeded).
"""

import asyncio
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple

try:
    from backend.config import (
        MAX_STEPS,
        DOM_EXTRACTION_LIMIT,
        STATE_SIGNATURE_LENGTH,
        PORTAL_KEYWORD_MAP
    )
    from backend.models import (
        LLMDecision,
        StepResponse,
        DOMElement,
        compute_state_signature
    )
    from backend.browser_sandbox import BrowserSandbox
    from backend.state_manager import SessionStateManager, get_default_state_manager
    from backend.llm_client import decide_action, get_default_gateway
except ImportError:
    try:
        from config import (
            MAX_STEPS,
            DOM_EXTRACTION_LIMIT,
            STATE_SIGNATURE_LENGTH,
            PORTAL_KEYWORD_MAP
        )
        from models import (
            LLMDecision,
            StepResponse,
            DOMElement,
            compute_state_signature
        )
        from browser_sandbox import BrowserSandbox
        from state_manager import SessionStateManager, get_default_state_manager
        from llm_client import decide_action, get_default_gateway
    except ImportError:
        MAX_STEPS = 8
        DOM_EXTRACTION_LIMIT = 25
        STATE_SIGNATURE_LENGTH = 16
        PORTAL_KEYWORD_MAP = {}
        LLMDecision = None
        StepResponse = None
        DOMElement = None
        compute_state_signature = None
        BrowserSandbox = None
        SessionStateManager = None
        get_default_state_manager = None
        decide_action = None
        get_default_gateway = None

logger = logging.getLogger("seva.odav")


class ODAVEngine:
    """
    Coordinates the Observe-Decide-Act-Verify (ODAV) loop cycle.
    """

    def __init__(
        self,
        sandbox: Optional[BrowserSandbox] = None,
        state_manager: Optional[SessionStateManager] = None,
        llm_gateway: Optional[Any] = None
    ):
        self.sandbox: BrowserSandbox = sandbox or BrowserSandbox()
        self.state_manager: SessionStateManager = state_manager or get_default_state_manager()
        self.llm_gateway = llm_gateway or (get_default_gateway() if get_default_gateway else None)

    async def observe(self) -> Tuple[str, List[Dict[str, Any]], str]:
        """
        Observe Phase:
        Inspects browser state, extracts up to 25 interactive DOM elements,
        and computes deterministic state signature S(t) = SHA256(url + DOM)[:16].
        """
        if not self.sandbox.is_running:
            await self.sandbox.initialize()

        url, elements = await self.sandbox.extract_interactive_elements()
        # Cap interactive elements strictly at DOM_EXTRACTION_LIMIT (25)
        elements = elements[:DOM_EXTRACTION_LIMIT]

        if compute_state_signature is not None:
            signature = compute_state_signature(url, elements)
        else:
            tokens = [
                f"{e.get('tag')}:{e.get('selector')}:{e.get('value')}:{e.get('text')}:{e.get('id')}"
                for e in elements
            ]
            payload = f"{url}|" + "|".join(tokens)
            signature = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:STATE_SIGNATURE_LENGTH]

        logger.debug(f"[ODAV:OBSERVE] URL: {url} | Elements: {len(elements)} | Sig: {signature}")
        return url, elements, signature

    async def decide(
        self,
        goal: str,
        history: List[Dict[str, Any]],
        url: str,
        dom_elements: List[Dict[str, Any]],
        language: str = "mr-IN",
        force_action: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Decide Phase:
        Queries Cloud LLM Decision Engine with rolling scratchpad (pruned context)
        or applies manual human checkpoint override action.
        """
        if force_action:
            logger.info(f"[ODAV:DECIDE] Applying manual force_action override: {force_action.get('action')}")
            if LLMDecision is not None:
                parsed = LLMDecision(**force_action)
                return parsed.to_dict()
            return {
                "thought": str(force_action.get("thought", "Manual override")),
                "action": str(force_action.get("action", "wait")),
                "selector": str(force_action.get("selector", "")),
                "value": str(force_action.get("value", "")),
                "feedback": str(force_action.get("feedback", "कृती चालू आहे."))
            }

        # Query Cloud LLM Gateway via interface contract
        if decide_action is not None:
            # Retain only last 3 step deltas for prompt token pruning
            pruned_history = history[-3:] if history else []
            decision = decide_action(
                goal=goal,
                history=pruned_history,
                url=url,
                dom_elements=dom_elements,
                language=language
            )
            return decision

        # Safe local fallback if decide_action not importable
        return {
            "thought": "Fallback decision engine triggered",
            "action": "wait",
            "selector": "",
            "value": "",
            "feedback": "कृपया प्रतीक्षा करा, प्रक्रिया चालू आहे."
        }

    async def act(self, decision: Dict[str, str]) -> Tuple[bool, str]:
        """
        Act Phase:
        Dispatches primitive action (navigate, click, fill, scroll, wait, finish)
        to the Playwright browser sandbox with timeout guards.
        """
        action = decision.get("action", "wait")
        selector = decision.get("selector", "")
        value = decision.get("value", "")

        logger.info(f"[ODAV:ACT] Executing action='{action}' selector='{selector}' value='{value[:30]}'")
        success, detail = await self.sandbox.execute_action(action, selector, value)
        return success, detail

    async def verify(
        self,
        pre_signature: str,
        decision: Dict[str, str],
        act_success: bool,
        act_detail: str
    ) -> Tuple[str, bool, str, str]:
        """
        Verify Phase:
        Re-inspects browser state after action execution.
        Audits state mutation S(t) != S(t-1) and detects 2-step stalls.
        Returns: (post_signature, stalled, status, post_url).
        """
        # Brief yield to allow DOM rendering
        await asyncio.sleep(0.05)

        post_url, post_elements, post_signature = await self.observe()
        mutated = (post_signature != pre_signature)

        # Detect stalls across 2 consecutive identical states
        stalled = self.state_manager.check_stall(post_signature)

        if not act_success:
            status = "error"
        elif stalled:
            status = "stalled"
        else:
            status = "progressing"

        logger.info(
            f"[ODAV:VERIFY] Mutated: {mutated} (Pre: {pre_signature} -> Post: {post_signature}) | "
            f"Stalled: {stalled} | Status: {status}"
        )
        return post_signature, stalled, status, post_url

    async def step(self, force_action: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a single Observe-Decide-Act-Verify (ODAV) cycle.
        Enforces:
          - Hard step budget guard (max 8 iterations per session)
          - Finish termination gate (receipt generation)
          - State mutation audit & 2-step stall detection
        """
        # 1. Session Guard Checks
        if not self.state_manager.active:
            if self.state_manager.finished:
                return {
                    "step": self.state_manager.step,
                    "state_signature": self.state_manager.current_signature,
                    "action": self.state_manager.last_action or {"action": "finish", "thought": "Task already completed", "selector": "", "value": "", "feedback": "सेवा पूर्ण झाली आहे."},
                    "stalled": False,
                    "status": "finished",
                    "feedback": "अर्ज प्रक्रिया आधीच पूर्ण झाली आहे.",
                    "receipt": self.state_manager.receipt
                }
            if self.state_manager.is_budget_exceeded():
                return {
                    "step": self.state_manager.step,
                    "state_signature": self.state_manager.current_signature,
                    "action": self.state_manager.last_action or {"action": "wait", "thought": "Budget ceiling reached", "selector": "", "value": "", "feedback": "मर्यादा संपली आहे."},
                    "stalled": False,
                    "status": "budget_exceeded",
                    "feedback": "कमाल पायऱ्या पूर्ण झाल्या आहेत (8/8)."
                }
            raise RuntimeError("No active citizen session. Call start-task before step.")

        # Hard step budget guard: if already at or beyond max steps, stop immediately
        if self.state_manager.is_budget_exceeded():
            self.state_manager.mark_budget_exceeded()
            return {
                "step": self.state_manager.step,
                "state_signature": self.state_manager.current_signature,
                "action": self.state_manager.last_action or {"action": "wait", "thought": "Budget ceiling reached", "selector": "", "value": "", "feedback": "मर्यादा संपली आहे."},
                "stalled": False,
                "status": "budget_exceeded",
                "feedback": "कमाल पायऱ्या पूर्ण झाल्या आहेत (8/8)."
            }

        # 2. Observe
        pre_url, dom_elements, pre_signature = await self.observe()

        # 3. Decide
        decision = await self.decide(
            goal=self.state_manager.task,
            history=self.state_manager.history,
            url=pre_url,
            dom_elements=dom_elements,
            language=self.state_manager.language,
            force_action=force_action
        )

        action_name = decision.get("action", "wait")

        # 4. Termination Gate: Finish Action
        if action_name == "finish":
            current_step = self.state_manager.increment_step()
            receipt = self.state_manager.finish_task()
            await self.sandbox.execute_action("finish", "", "")

            step_delta = {
                "step": current_step,
                "action": "finish",
                "selector": decision.get("selector", ""),
                "value": receipt,
                "status": "finished",
                "url": pre_url,
                "state_signature": pre_signature,
                "thought": decision.get("thought", "Workflow completed"),
                "feedback": decision.get("feedback", "आपला अर्ज यशस्वीरीत्या जमा झाला आहे."),
                "action_dict": decision,
                "receipt": receipt
            }
            self.state_manager.record_step(step_delta, pre_signature)

            return {
                "step": current_step,
                "state_signature": pre_signature,
                "action": decision,
                "stalled": False,
                "status": "finished",
                "feedback": decision.get("feedback", "आपला अर्ज यशस्वीरीत्या जमा झाला आहे."),
                "receipt": receipt
            }

        # 5. Act
        act_success, act_detail = await self.act(decision)

        # 6. Verify
        post_sig, stalled, verify_status, post_url = await self.verify(
            pre_signature=pre_signature,
            decision=decision,
            act_success=act_success,
            act_detail=act_detail
        )

        # 7. Record Step & Update State
        current_step = self.state_manager.increment_step()

        # Check if this step reached the hard budget ceiling
        if self.state_manager.is_budget_exceeded():
            self.state_manager.mark_budget_exceeded()
            final_status = "budget_exceeded"
        elif stalled:
            final_status = "stalled"
        else:
            final_status = verify_status

        step_delta = {
            "step": current_step,
            "action": action_name,
            "selector": decision.get("selector", ""),
            "value": decision.get("value", ""),
            "status": final_status,
            "url": post_url,
            "state_signature": post_sig,
            "thought": decision.get("thought", ""),
            "feedback": decision.get("feedback", ""),
            "action_dict": decision,
            "act_success": act_success,
            "act_detail": act_detail,
            "stalled": stalled
        }
        self.state_manager.record_step(step_delta, post_sig)

        return {
            "step": current_step,
            "state_signature": post_sig,
            "action": decision,
            "stalled": stalled,
            "status": final_status,
            "feedback": decision.get("feedback", "")
        }
