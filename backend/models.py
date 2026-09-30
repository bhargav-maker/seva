"""
backend/models.py
Strict Pydantic models and schemas for SEVA AI Kiosk Platform.

Defines:
1. LLMDecision: Deterministic 5-key JSON schema:
   { "thought": str, "action": str, "selector": str, "value": str, "feedback": str }
   Restricts action to ["navigate", "click", "fill", "scroll", "wait", "finish"].
2. Context Pruning Data Structures: StepDelta, PrunedContext, DOMElement.
3. Session State Models: StartTaskRequest, StartTaskResponse, StepResponse, SessionState, ResetResponse.
"""

from typing import List, Dict, Any, Optional, Literal, Set
import hashlib
import json

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    _PYDANTIC_V2 = True
except ImportError:
    try:
        from pydantic import BaseModel, Field, validator as field_validator
        _PYDANTIC_V2 = False
    except ImportError:
        _PYDANTIC_V2 = False

        class _FieldInfo:
            def __init__(self, default=None, default_factory=None, description=""):
                self.default = default
                self.default_factory = default_factory
                self.description = description

        def Field(default=..., *, default_factory=None, description=""):  # type: ignore
            return _FieldInfo(default=default, default_factory=default_factory, description=description)

        class BaseModel:  # type: ignore
            def __init__(self, **kwargs):
                for k, v in self.__class__.__dict__.items():
                    if isinstance(v, _FieldInfo):
                        if v.default_factory is not None:
                            setattr(self, k, v.default_factory())
                        elif v.default is not ...:
                            setattr(self, k, v.default)
                for k, v in kwargs.items():
                    setattr(self, k, v)


VALID_ACTIONS: Set[str] = {"navigate", "click", "fill", "scroll", "wait", "finish"}
ActionType = Literal["navigate", "click", "fill", "scroll", "wait", "finish"]


class LLMDecision(BaseModel):
    """
    Deterministic 5-key JSON decision schema returned by LLM Decision Engine.
    Strictly enforced across Gemini 2.5 Flash, Qwen 2.5 7B, and local fallback.
    """
    thought: str = Field(..., description="Reasoning for the selected action in English")
    action: ActionType = Field(..., description="Single immediate browser primitive action")
    selector: str = Field(default="", description="CSS selector or target anchor (empty if not applicable)")
    value: str = Field(default="", description="Input text or destination URL (empty if not applicable)")
    feedback: str = Field(..., description="Spoken feedback for citizen in their vernacular language")

    if _PYDANTIC_V2:
        @field_validator("action", mode="before")
        @classmethod
        def validate_action(cls, v: Any) -> str:
            if not isinstance(v, str):
                raise ValueError(f"action must be a string, got {type(v).__name__}")
            norm = v.strip().lower()
            if norm not in VALID_ACTIONS:
                raise ValueError(f"Invalid action '{v}'. Allowed actions: {sorted(list(VALID_ACTIONS))}")
            return norm

        @field_validator("selector", "value", mode="before")
        @classmethod
        def sanitize_strings(cls, v: Any) -> str:
            if v is None:
                return ""
            return str(v)

        @field_validator("thought", "feedback", mode="before")
        @classmethod
        def ensure_str(cls, v: Any) -> str:
            if v is None:
                return ""
            return str(v)
    else:
        def __init__(self, **data):
            super().__init__(**data)
            action_val = str(getattr(self, "action", "")).strip().lower()
            if action_val not in VALID_ACTIONS:
                raise ValueError(f"Invalid action '{action_val}'. Allowed actions: {sorted(list(VALID_ACTIONS))}")
            self.action = action_val
            self.selector = str(getattr(self, "selector", "") or "")
            self.value = str(getattr(self, "value", "") or "")
            self.thought = str(getattr(self, "thought", "") or "")
            self.feedback = str(getattr(self, "feedback", "") or "")


    def to_dict(self) -> Dict[str, str]:
        """Returns the canonical 5-key dictionary."""
        return {
            "thought": str(self.thought),
            "action": str(self.action),
            "selector": str(self.selector),
            "value": str(self.value),
            "feedback": str(self.feedback)
        }

    def to_json(self) -> str:
        """Returns raw JSON string without markdown or backticks."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class DOMElement(BaseModel):
    """Extracted interactive DOM element from Playwright browser sandbox."""
    tag: str = Field(default="", description="HTML tag: button, a, input, select, textarea")
    id: str = Field(default="", description="Element ID attribute")
    name: str = Field(default="", description="Element name attribute")
    text: str = Field(default="", description="Inner visible text or label")
    type: str = Field(default="", description="Input type if applicable")
    placeholder: str = Field(default="", description="Input placeholder")
    selector: str = Field(default="", description="Unique CSS selector or path")
    href: str = Field(default="", description="Link destination if anchor")
    role: str = Field(default="", description="ARIA accessibility role")


class StepDelta(BaseModel):
    """Single step execution delta recorded in history for context pruning."""
    step: int = Field(default=0, description="1-based step counter")
    action: str = Field(..., description="Action primitive executed")
    selector: str = Field(default="", description="Target CSS selector")
    value: str = Field(default="", description="Value passed to action")
    status: str = Field(default="ok", description="Execution status: ok, error, stalled")
    url: str = Field(default="", description="Page URL after step execution")
    state_signature: str = Field(default="", description="16-character SHA-256 state signature")


class PrunedContext(BaseModel):
    """
    Context Pruning data structure implementing the Rolling Scratchpad pattern:
    Retains citizen goal + last 3 step deltas.
    """
    citizen_goal: str = Field(..., description="Original citizen request")
    language: str = Field(default="mr-IN", description="Vernacular language code")
    recent_steps: List[StepDelta] = Field(default_factory=list, description="At most 3 recent step deltas")
    active_url: str = Field(default="", description="Current browser viewport URL")
    dom_elements_count: int = Field(default=0, description="Total interactive elements extracted")

    def format_prompt_summary(self) -> str:
        """Formats concise context string for LLM inference (< 250 tokens)."""
        summary = f"Citizen Goal: {self.citizen_goal}\n"
        if self.recent_steps:
            summary += "Recent Steps (last 3):\n"
            for s in self.recent_steps[-3:]:
                summary += f"  Step {s.step}: action={s.action}, selector={s.selector}, status={s.status}\n"
        return summary


class StartTaskRequest(BaseModel):
    """Payload for POST /api/start-task."""
    task: str = Field(..., description="Citizen natural language goal")
    language: str = Field(default="mr-IN", description="Target vernacular language (mr-IN, hi-IN, en-IN)")


class StartTaskResponse(BaseModel):
    """Response from POST /api/start-task."""
    status: str = Field(default="started")
    session_id: str = Field(..., description="Unique UUID session identifier")
    step: int = Field(default=0)


class StepRequest(BaseModel):
    """Payload for POST /api/step."""
    force_action: Optional[Dict[str, Any]] = Field(default=None, description="Optional manual override action")


class StepResponse(BaseModel):
    """Response from POST /api/step."""
    step: int = Field(..., description="Current step index (1-8)")
    state_signature: str = Field(..., description="SHA-256 state signature hash")
    action: Dict[str, str] = Field(..., description="Executed LLMDecision dict")
    stalled: bool = Field(default=False, description="True if 2 consecutive identical states observed")
    status: str = Field(default="progressing", description="progressing, finished, stalled, budget_exceeded, error")
    feedback: str = Field(default="", description="Spoken feedback for citizen")


class SessionState(BaseModel):
    """Complete session state model returned by GET /api/session-state."""
    session_id: str = Field(default="")
    active: bool = Field(default=False)
    step: int = Field(default=0)
    max_steps: int = Field(default=8)
    task: str = Field(default="")
    language: str = Field(default="mr-IN")
    history: List[Dict[str, Any]] = Field(default_factory=list)
    last_action: Optional[Dict[str, Any]] = None
    url: str = Field(default="")
    stalled: bool = Field(default=False)
    finished: bool = Field(default=False)
    state_signature: str = Field(default="")


class ResetResponse(BaseModel):
    """Response from POST /api/reset."""
    status: str = Field(default="reset")
    purged: bool = Field(default=True, description="Ephemeral memory purge confirmed")


def compute_state_signature(url: str, elements: List[Dict[str, Any]]) -> str:
    """
    Computes deterministic 16-character SHA-256 state signature:
    S(t) = SHA256(url + DOM)[:16].
    Token format: tag:selector:value:text:id for up to 25 elements.
    """
    url = url or "about:blank"
    elements = elements or []
    tokens = [
        f"{e.get('tag', '')}:{e.get('selector', '')}:{e.get('value', '')}:{e.get('text', '')}:{e.get('id', '')}"
        for e in elements[:25]
    ]
    payload = f"{url}|" + "|".join(tokens)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

