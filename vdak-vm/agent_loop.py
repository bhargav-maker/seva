"""
vdak-vm/agent_loop.py
Observe-Decide-Act-Verify (ODAV) Autonomous Browser Loop Engine for SEVA AI.
Coordinates the closed-circuit state cycle between vdak-vm and vdak-host.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("vdak.vm.agent_loop")

class ODAVAgentLoop:
    """
    Executes the 4-phase closed-circuit ODAV cycle:
    1. Observe: URL, title, top 25 DOM elements, compute S(t)
    2. Decide: Query Qwen 2.5 7B brain with k=3 context
    3. Act: Dispatch action with 5000ms guard and trigger audio cue
    4. Verify: Check state delta S(t) != S(t-1), detect stalls, enforce N=8 ceiling
    """

    def __init__(
        self,
        browser_controller,
        vm_client,
        state_manager,
        tts_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.browser = browser_controller
        self.brain = vm_client
        self.state_mgr = state_manager
        self.tts_callback = tts_callback
        self.is_running = False

    async def run_single_step(self) -> Dict[str, Any]:
        """Executes exactly one discrete ODAV iteration."""
        # 1. OBSERVE
        url, title, dom_elements = await self.browser.extract_interactive_elements()
        sig_before = self.state_mgr.compute_signature(url, title, dom_elements)

        # 2. DECIDE
        context = self.state_mgr.get_compacted_context()
        goal = context["goal"]
        lang = context["language"]
        history = context["recent_actions"]

        decision = await self.brain.decide_next_action(
            goal=goal,
            recent_history=history,
            url=url,
            dom_elements=dom_elements,
            language=lang
        )

        action = decision.get("action", "wait")
        selector = decision.get("selector", "")
        value = decision.get("value", "")
        feedback = decision.get("feedback", "")

        # Emit spoken vernacular audio confirmation if feedback present
        if feedback and self.tts_callback:
            try:
                self.tts_callback(feedback, lang)
            except Exception as e:
                logger.warning(f"[AgentLoop] TTS callback error: {e}")

        # 3. ACT
        success, exec_msg = await self.browser.execute_action(action, selector, value)

        # Allow slight delay for page mutation
        await asyncio.sleep(0.5)

        # 4. VERIFY
        new_url, new_title, new_dom = await self.browser.extract_interactive_elements()
        sig_after = self.state_mgr.compute_signature(new_url, new_title, new_dom)

        step_result = self.state_mgr.record_step(
            signature=sig_after,
            action_dict=decision,
            url=new_url,
            execution_success=success
        )

        # Handle 2-step stall breakout
        if step_result.get("stalled"):
            logger.warning("[AgentLoop] 2-Step stall detected. Executing recovery scroll.")
            await self.browser.execute_action("scroll", "", "300")
            if self.tts_callback:
                stall_msg = "पृष्ठ लोड होत आहे, कृपया प्रतीक्षा करा." if lang == "mr" else "पृष्ठ लोड हो रहा है, कृपया प्रतीक्षा करें."
                self.tts_callback(stall_msg, lang)

        return {
            "step": step_result["step"],
            "status": step_result["status"],
            "decision": decision,
            "signature_before": sig_before,
            "signature_after": sig_after,
            "mutated": sig_before != sig_after,
            "execution_success": success,
            "execution_msg": exec_msg,
            "stalled": step_result.get("stalled", False),
            "finished": step_result.get("finished", False)
        }

    async def run_full_session(self, max_steps: int = 8) -> Dict[str, Any]:
        """Runs the ODAV loop autonomously until finish, stall cap, or budget exhaustion."""
        self.is_running = True
        logger.info("[AgentLoop] Initiating autonomous ODAV session...")
        steps_executed = []

        try:
            while self.is_running:
                step_res = await self.run_single_step()
                steps_executed.append(step_res)

                if step_res["finished"]:
                    logger.info("[AgentLoop] Goal reached successfully. Terminating session.")
                    break

                if step_res["status"] == "budget_exhausted":
                    logger.warning("[AgentLoop] Budget ceiling of 8 steps reached. Cleanly terminating.")
                    break

                if step_res["step"] >= max_steps:
                    break

            return {
                "final_status": steps_executed[-1]["status"] if steps_executed else "empty",
                "total_steps": len(steps_executed),
                "steps": steps_executed
            }
        finally:
            self.is_running = False
