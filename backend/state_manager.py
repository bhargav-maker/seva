"""
backend/state_manager.py
Session State Manager for SEVA AI Kiosk Platform.

Manages:
- Active citizen task & vernacular language session state.
- Step counter with hard 8-step budget guard (MAX_STEPS = 8).
- Step execution history & rolling scratchpad context pruning (last 3 step deltas).
- State signature history S(t) and two-step stall detection.
- Completion gate & tracking receipt generation (SEVA-YYYYMMDD-XXXXX).
- Ephemeral memory purge compliant with Digital Personal Data Protection (DPDP) Act 2023.
"""

import datetime
import logging
import secrets
import threading
import uuid
from typing import Dict, Any, List, Optional

try:
    from backend.config import (
        MAX_STEPS,
        CONTEXT_HISTORY_LIMIT,
        DEFAULT_LANGUAGE,
        RECEIPT_PREFIX,
        STALL_THRESHOLD
    )
    from backend.models import (
        SessionState,
        StepDelta,
        PrunedContext
    )
except ImportError:
    try:
        from config import (
            MAX_STEPS,
            CONTEXT_HISTORY_LIMIT,
            DEFAULT_LANGUAGE,
            RECEIPT_PREFIX,
            STALL_THRESHOLD
        )
        from models import (
            SessionState,
            StepDelta,
            PrunedContext
        )
    except ImportError:
        MAX_STEPS = 8
        CONTEXT_HISTORY_LIMIT = 3
        DEFAULT_LANGUAGE = "mr-IN"
        RECEIPT_PREFIX = "SEVA"
        STALL_THRESHOLD = 2
        SessionState = None
        StepDelta = None
        PrunedContext = None

logger = logging.getLogger("seva.state_manager")


class SessionStateManager:
    """
    Thread-safe state manager for citizen kiosk sessions.
    Strictly enforces:
      1. Maximum 8 iterations per session (hard step budget guard).
      2. Stall detector: flags stalled=True when 2 consecutive identical states are observed.
      3. Rolling scratchpad: retains citizen goal + last 3 step deltas.
      4. Ephemeral data purge: zero-persistence DPDP Act compliant wipe on reset.
      5. Application tracking receipt generation: SEVA-YYYYMMDD-XXXXX.
    """

    def __init__(self, max_steps: int = MAX_STEPS):
        self._lock = threading.Lock()
        self.max_steps: int = max_steps
        self.session_id: str = ""
        self.task: str = ""
        self.language: str = DEFAULT_LANGUAGE
        self.step: int = 0
        self.active: bool = False
        self.finished: bool = False
        self.stalled: bool = False
        self.status: str = "ready"  # ready, started, progressing, stalled, finished, budget_exceeded, error, reset
        self.current_url: str = ""
        self.current_signature: str = ""
        self.history: List[Dict[str, Any]] = []
        self.signature_history: List[str] = []
        self.last_action: Optional[Dict[str, Any]] = None
        self.receipt: Optional[str] = None
        self.error_message: Optional[str] = None

    def start_session(self, task: str, language: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
        """
        Initializes a fresh citizen session.
        Cleans any previous ephemeral data and starts a new session tracking scope.
        """
        with self._lock:
            # Ephemeral wipe of prior session data
            self._wipe_internal()

            self.session_id = uuid.uuid4().hex
            self.task = task.strip()
            self.language = language or DEFAULT_LANGUAGE
            self.step = 0
            self.active = True
            self.finished = False
            self.stalled = False
            self.status = "started"
            self.history = []
            self.signature_history = []
            self.last_action = None
            self.receipt = None
            self.error_message = None
            self.current_url = "about:blank"
            self.current_signature = "0000000000000000"

            logger.info(
                f"[STATE] Started session {self.session_id} | Task: '{self.task[:40]}...' | "
                f"Lang: {self.language} | Max Steps: {self.max_steps}"
            )

            return {
                "status": "started",
                "session_id": self.session_id,
                "step": self.step,
                "task": self.task,
                "language": self.language,
                "max_steps": self.max_steps
            }

    def check_stall(self, new_signature: str) -> bool:
        """
        Stall detection audit:
        Flags stalled=True if the new signature matches the immediately preceding state
        signature (i.e. 2 consecutive identical states).
        """
        with self._lock:
            if not new_signature or new_signature == "0000000000000000":
                return False

            if len(self.signature_history) >= 1:
                # Compare against the last recorded signature
                if self.signature_history[-1] == new_signature:
                    self.stalled = True
                    logger.warning(
                        f"[STATE] Stall detected: state signature '{new_signature}' "
                        f"repeated across 2 consecutive steps."
                    )
                    return True

            self.stalled = False
            return False

    def record_step(
        self,
        step_delta: Dict[str, Any],
        state_signature: str
    ) -> None:
        """
        Records an executed step delta and state signature into history.
        Enforces step counter increment up to max_steps.
        """
        with self._lock:
            self.history.append(step_delta)
            if state_signature:
                self.signature_history.append(state_signature)
                self.current_signature = state_signature

            self.last_action = step_delta.get("action_dict") or {
                "thought": step_delta.get("thought", ""),
                "action": step_delta.get("action", ""),
                "selector": step_delta.get("selector", ""),
                "value": step_delta.get("value", ""),
                "feedback": step_delta.get("feedback", "")
            }

            if "url" in step_delta and step_delta["url"]:
                self.current_url = step_delta["url"]

            logger.info(
                f"[STATE] Step {self.step}/{self.max_steps} recorded | "
                f"Action: {step_delta.get('action')} | Status: {step_delta.get('status')} | "
                f"Sig: {state_signature}"
            )

    def increment_step(self) -> int:
        """
        Increments step counter by 1, clamped to max_steps ceiling.
        Returns the new step index.
        """
        with self._lock:
            if self.step < self.max_steps:
                self.step += 1
            if self.step >= self.max_steps:
                logger.info(f"[STATE] Reached hard budget ceiling ({self.step}/{self.max_steps}).")
            return self.step

    def is_budget_exceeded(self) -> bool:
        """Checks if session has hit or exceeded the hard 8-step budget ceiling."""
        with self._lock:
            return self.step >= self.max_steps

    def mark_budget_exceeded(self) -> None:
        """Sets status to budget_exceeded and marks session inactive."""
        with self._lock:
            self.status = "budget_exceeded"
            self.active = False
            logger.warning(f"[STATE] Step budget exceeded ({self.step}/{self.max_steps}). Loop locked.")

    def finish_task(self) -> str:
        """
        Marks task completed, generates citizen tracking receipt,
        and sets status='finished'.
        Format: SEVA-YYYYMMDD-XXXXX
        """
        with self._lock:
            self.finished = True
            self.active = False
            self.status = "finished"
            today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
            rand_suffix = secrets.token_hex(3).upper()[:5]
            self.receipt = f"{RECEIPT_PREFIX}-{today_str}-{rand_suffix}"
            logger.info(f"[STATE] Task marked finished. Generated receipt: {self.receipt}")
            return self.receipt

    def get_pruned_context(self) -> Any:
        """
        Implements Context Pruning (Rolling Scratchpad pattern per R1 / R3):
        Retains original citizen goal + at most the last 3 step deltas.
        """
        with self._lock:
            recent_deltas: List[Any] = []
            raw_recent = self.history[-CONTEXT_HISTORY_LIMIT:] if self.history else []

            for d in raw_recent:
                if StepDelta is not None:
                    recent_deltas.append(
                        StepDelta(
                            step=d.get("step", 0),
                            action=str(d.get("action", "")),
                            selector=str(d.get("selector", "")),
                            value=str(d.get("value", "")),
                            status=str(d.get("status", "ok")),
                            url=str(d.get("url", "")),
                            state_signature=str(d.get("state_signature", ""))
                        )
                    )
                else:
                    recent_deltas.append(d)

            if PrunedContext is not None:
                return PrunedContext(
                    citizen_goal=self.task,
                    language=self.language,
                    recent_steps=recent_deltas,
                    active_url=self.current_url,
                    dom_elements_count=0
                )
            return {
                "citizen_goal": self.task,
                "language": self.language,
                "recent_steps": recent_deltas,
                "active_url": self.current_url
            }

    def purge_ephemeral_data(self) -> None:
        """
        Digital Personal Data Protection (DPDP) Act 2023 Compliance:
        Immediately wipes all citizen sensitive information, active task, PII values,
        step histories, DOM states, and receipts from volatile memory.
        """
        with self._lock:
            self._wipe_internal()
            logger.info("[STATE] Ephemeral data purged. Volatile memory zeroed (DPDP Act compliant).")

    def _wipe_internal(self) -> None:
        """Internal zeroing of session fields without external lock acquisition."""
        self.session_id = ""
        self.task = ""
        self.language = DEFAULT_LANGUAGE
        self.step = 0
        self.active = False
        self.finished = False
        self.stalled = False
        self.status = "reset"
        self.current_url = ""
        self.current_signature = ""
        self.history.clear()
        self.signature_history.clear()
        self.last_action = None
        self.receipt = None
        self.error_message = None

    def get_session_state(self) -> Dict[str, Any]:
        """Returns comprehensive session state dictionary."""
        with self._lock:
            return {
                "session_id": self.session_id,
                "active": self.active,
                "step": self.step,
                "max_steps": self.max_steps,
                "task": self.task,
                "language": self.language,
                "history": list(self.history),
                "last_action": self.last_action,
                "url": self.current_url,
                "stalled": self.stalled,
                "finished": self.finished,
                "state_signature": self.current_signature,
                "status": self.status,
                "receipt": self.receipt,
                "error": self.error_message
            }

    def to_model(self) -> Any:
        """Converts internal state to SessionState Pydantic model if available."""
        state_dict = self.get_session_state()
        if SessionState is not None:
            return SessionState(
                session_id=state_dict["session_id"],
                active=state_dict["active"],
                step=state_dict["step"],
                max_steps=state_dict["max_steps"],
                task=state_dict["task"],
                language=state_dict["language"],
                history=state_dict["history"],
                last_action=state_dict["last_action"],
                url=state_dict["url"],
                stalled=state_dict["stalled"],
                finished=state_dict["finished"],
                state_signature=state_dict["state_signature"]
            )
        return state_dict


# Global Singleton Instance
_global_state_manager: Optional[SessionStateManager] = None
_manager_lock = threading.Lock()


def get_default_state_manager(max_steps: int = MAX_STEPS) -> SessionStateManager:
    """Returns singleton instance of SessionStateManager."""
    global _global_state_manager
    with _manager_lock:
        if _global_state_manager is None:
            _global_state_manager = SessionStateManager(max_steps=max_steps)
        return _global_state_manager


def reset_default_state_manager() -> SessionStateManager:
    """Resets and purges the singleton state manager."""
    global _global_state_manager
    with _manager_lock:
        if _global_state_manager is not None:
            _global_state_manager.purge_ephemeral_data()
        _global_state_manager = SessionStateManager(max_steps=MAX_STEPS)
        return _global_state_manager
