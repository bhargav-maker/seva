"""
vdak-host/state_machine.py
Hierarchical Finite State Machine for V-DAK kiosk session lifecycle.
States: IDLE → INTENT_DISCOVERY → DOCUMENT_SCANNING →
        PORTAL_AUTOMATION → HUMAN_CHECKPOINT → SUBMISSION → PURGE
"""

import logging
from transitions import Machine

logger = logging.getLogger("vdak.statemachine")


STATES = [
    "IDLE",
    "INTENT_DISCOVERY",
    "DOCUMENT_SCANNING",
    "PORTAL_AUTOMATION",
    "HUMAN_CHECKPOINT",
    "SUBMISSION",
    "PURGE",
    "ERROR",
]

TRANSITIONS = [
    # Citizen walks up → greeting
    {"trigger": "citizen_detected",   "source": "IDLE",              "dest": "INTENT_DISCOVERY"},
    # Intent understood → scan documents
    {"trigger": "intent_confirmed",   "source": "INTENT_DISCOVERY",  "dest": "DOCUMENT_SCANNING"},
    # OCR done and verified → launch browser agent on VM
    {"trigger": "docs_verified",      "source": "DOCUMENT_SCANNING", "dest": "PORTAL_AUTOMATION"},
    # OTP field detected by VM agent
    {"trigger": "checkpoint_hit",     "source": "PORTAL_AUTOMATION", "dest": "HUMAN_CHECKPOINT"},
    # Citizen typed OTP → agent resumes
    {"trigger": "otp_submitted",      "source": "HUMAN_CHECKPOINT",  "dest": "PORTAL_AUTOMATION"},
    # Form successfully submitted
    {"trigger": "submission_done",    "source": "PORTAL_AUTOMATION", "dest": "SUBMISSION"},
    # Print receipt → wipe session
    {"trigger": "receipt_printed",    "source": "SUBMISSION",        "dest": "PURGE"},
    # After purge → back to idle
    {"trigger": "session_purged",     "source": "PURGE",             "dest": "IDLE"},
    # Any error → ERROR state
    {"trigger": "error_occurred",     "source": "*",                 "dest": "ERROR"},
    # Recover from error
    {"trigger": "reset",              "source": "ERROR",             "dest": "IDLE"},
    # User cancels / timeout
    {"trigger": "user_cancelled",     "source": "*",                 "dest": "PURGE"},
]


class KioskStateMachine:
    """V-DAK session state machine with logging on every transition."""

    def __init__(self, on_state_change=None):
        """
        on_state_change: optional async callback(new_state: str)
        called after every transition — used to update the React UI.
        """
        self._on_state_change = on_state_change

        self.machine = Machine(
            model=self,
            states=STATES,
            transitions=TRANSITIONS,
            initial="IDLE",
            after_state_change="_after_transition",
        )

    def _after_transition(self):
        logger.info(f"[STATE] → {self.state}")
        if self._on_state_change:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._on_state_change(self.state))
            except RuntimeError:
                pass

    @property
    def current(self) -> str:
        return self.state

    def is_idle(self) -> bool:
        return self.state == "IDLE"

    def is_waiting_for_otp(self) -> bool:
        return self.state == "HUMAN_CHECKPOINT"
