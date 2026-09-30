"""
vdak-host/bridge/state_manager.py
Session State & ODAV Context Compaction Manager for SEVA AI Kiosk.
Strictly enforces:
1. Step Budget Ceiling (N = 8)
2. Rolling Scratchpad Context Compaction (k = 3)
3. Deterministic State Signature S(t) = SHA256(URL + Title + DOM)[:16]
4. Two-Step Stall Detector & Breakout Gate
5. Live STATE.md audit artifact writing
6. Immediate ephemeral PII purge upon completion
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vdak.bridge.state_manager")

MAX_STEP_BUDGET = 8
CONTEXT_WINDOW_SIZE = 3
STATE_MD_PATH = Path(__file__).parent.parent / "STATE.md"

class StateManager:
    def __init__(self, max_steps: int = MAX_STEP_BUDGET, k_window: int = CONTEXT_WINDOW_SIZE):
        self.max_steps = max_steps
        self.k_window = k_window
        self.reset()

    def reset(self) -> None:
        """Purges all in-memory state and PII."""
        self.active_session_id: Optional[str] = None
        self.citizen_goal: str = ""
        self.language: str = "mr"
        self.current_step: int = 0
        self.history: List[Dict[str, Any]] = []
        self.last_signature: Optional[str] = None
        self.stall_count: int = 0
        self.is_finished: bool = False
        self.is_stalled: bool = False
        self.is_budget_exhausted: bool = False
        self._write_state_md("System idle / State purged.")

    def start_session(self, session_id: str, goal: str, language: str = "mr") -> None:
        """Initializes a new citizen session."""
        self.reset()
        self.active_session_id = session_id
        self.citizen_goal = goal
        self.language = language
        logger.info(f"[StateManager] Session {session_id} started. Goal: '{goal}', Lang: {language}")
        self._write_state_md(f"Session started for goal: {goal}")

    def compute_signature(self, url: str, title: str, dom_elements: List[Dict[str, Any]]) -> str:
        """Computes deterministic 16-hex state signature S(t)."""
        dom_repr = json.dumps(dom_elements[:25], sort_keys=True)
        raw = f"{url}|{title}|{dom_repr}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def get_compacted_context(self) -> Dict[str, Any]:
        """
        Retains only the original citizen goal and the last k=3 step deltas.
        Prevents context overflow and minimizes cloud inference token cost.
        """
        recent = self.history[-self.k_window:] if len(self.history) > self.k_window else list(self.history)
        return {
            "goal": self.citizen_goal,
            "language": self.language,
            "step_count": self.current_step,
            "recent_actions": recent,
            "budget_remaining": max(0, self.max_steps - self.current_step)
        }

    def record_step(
        self,
        signature: str,
        action_dict: Dict[str, str],
        url: str,
        execution_success: bool = True
    ) -> Dict[str, Any]:
        """
        Updates session state, checks budget ceiling, audits state mutation, and flags stalls.
        """
        self.current_step += 1

        # Check stall condition
        if self.last_signature is not None and signature == self.last_signature:
            self.stall_count += 1
        else:
            self.stall_count = 0
        self.last_signature = signature

        step_record = {
            "step": self.current_step,
            "signature": signature,
            "url": url,
            "action": action_dict,
            "success": execution_success,
            "stall_count": self.stall_count
        }
        self.history.append(step_record)

        # Invariant checks
        if action_dict.get("action") == "finish":
            self.is_finished = True
        elif self.stall_count >= 2:
            self.is_stalled = True
        elif self.current_step >= self.max_steps:
            self.is_budget_exhausted = True

        status = "finished" if self.is_finished else (
            "stalled" if self.is_stalled else (
                "budget_exhausted" if self.is_budget_exhausted else "active"
            )
        )

        self._write_state_md(f"Step {self.current_step}/{self.max_steps} executed. Status: {status}")

        return {
            "status": status,
            "step": self.current_step,
            "budget_remaining": max(0, self.max_steps - self.current_step),
            "state_signature": signature,
            "stalled": self.is_stalled,
            "finished": self.is_finished
        }

    def _write_state_md(self, note: str) -> None:
        """Writes current execution status to STATE.md for runtime transparency."""
        try:
            content = f"""# SEVA AI Kiosk Execution State

**Session ID:** `{self.active_session_id or 'NONE'}`  
**Language:** `{self.language}`  
**Step:** `{self.current_step}/{self.max_steps}`  
**Status Note:** {note}  

### Citizen Goal
> {self.citizen_goal or 'Idle / Awaiting Citizen'}

### Active State
- **Last State Signature $S(t)$:** `{self.last_signature or 'N/A'}`
- **Stall Counter:** `{self.stall_count}` (Breakout threshold = 2)
- **Finished:** `{self.is_finished}`
- **Budget Exhausted:** `{self.is_budget_exhausted}`

### Rolling Scratchpad History (Last {self.k_window} Steps)
"""
            compact = self.get_compacted_context()["recent_actions"]
            if not compact:
                content += "\n*No actions executed yet.*\n"
            else:
                for item in compact:
                    act = item.get("action", {})
                    content += f"- **Step {item.get('step')}:** `[{act.get('action')}]` {act.get('selector', '')} (Val: `{act.get('value', '')}`) -> *{act.get('thought', '')}*\n"

            STATE_MD_PATH.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.warning(f"[StateManager] Failed writing STATE.md: {e}")
