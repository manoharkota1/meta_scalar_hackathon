from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# Fallback models keep this repository runnable even when openenv is not
# installed in the local development interpreter.
try:
    from openenv.core.env_server.types import Action as OpenEnvAction
    from openenv.core.env_server.types import Observation as OpenEnvObservation
    from openenv.core.env_server.types import State as OpenEnvState
except Exception:  # pragma: no cover
    class OpenEnvAction(BaseModel):
        model_config = ConfigDict(extra="forbid")
        metadata: Dict[str, Any] = Field(default_factory=dict)

    class OpenEnvObservation(BaseModel):
        model_config = ConfigDict(extra="forbid")
        done: bool = False
        reward: Optional[float] = None
        metadata: Dict[str, Any] = Field(default_factory=dict)

    class OpenEnvState(BaseModel):
        model_config = ConfigDict(extra="allow")
        episode_id: Optional[str] = None
        step_count: int = 0


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ActionType(str, Enum):
    INSPECT_ALERT = "inspect_alert"
    INSPECT_FILE = "inspect_file"
    INSPECT_TESTS = "inspect_tests"
    TRIAGE_ALERT = "triage_alert"
    ADD_NOTE = "add_note"
    SUBMIT_REVIEW = "submit_review"


class DecisionType(str, Enum):
    BUG = "bug"
    FALSE_POSITIVE = "false_positive"
    NEEDS_INFO = "needs_info"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViewType(str, Enum):
    ALERT = "alert"
    FILE = "file"
    TESTS = "tests"


class AlertSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    title: str
    file_path: str
    tool_priority: int = Field(ge=1, le=5)
    tool_signal: str
    alert_context: str
    file_context: str
    test_context: str
    required_views: List[ViewType]
    expected_decision: DecisionType
    expected_severity: Optional[SeverityLevel] = None
    sla_deadline_step: Optional[int] = Field(default=None, ge=1)
    remediation_hint: str


class TaskDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    difficulty: DifficultyLevel
    objective: str
    max_steps: int = Field(ge=4)
    review_budget: int = Field(ge=6)
    submission_requirements: List[str]
    alerts: List[AlertSpec]


class AlertRuntimeStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inspected_alert: bool = False
    inspected_file: bool = False
    inspected_tests: bool = False
    triaged_decision: Optional[DecisionType] = None
    triaged_severity: Optional[SeverityLevel] = None
    notes: List[str] = Field(default_factory=list)
    first_triage_step: Optional[int] = None


class AlertQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    title: str
    file_path: str
    tool_priority: int
    tool_signal: str
    required_views: List[ViewType]
    inspected_alert: bool
    inspected_file: bool
    inspected_tests: bool
    triaged_decision: Optional[DecisionType] = None
    triaged_severity: Optional[SeverityLevel] = None


class ReviewAction(OpenEnvAction):
    action_type: ActionType
    alert_id: Optional[str] = None
    decision: Optional[DecisionType] = None
    severity: Optional[SeverityLevel] = None
    note: str = ""
    summary: str = ""


class ReviewObservation(OpenEnvObservation):
    task_id: str
    difficulty: DifficultyLevel
    objective: str
    step_count: int
    max_steps: int
    budget_used: int
    budget_limit: int
    progress_score: float = Field(ge=0.0, le=1.0)
    queue: List[AlertQueueItem]
    focused_context: str = ""
    last_action_error: Optional[str] = None
    available_actions: List[ActionType] = Field(
        default_factory=lambda: [
            ActionType.INSPECT_ALERT,
            ActionType.INSPECT_FILE,
            ActionType.INSPECT_TESTS,
            ActionType.TRIAGE_ALERT,
            ActionType.ADD_NOTE,
            ActionType.SUBMIT_REVIEW,
        ]
    )


class ReviewState(OpenEnvState):
    task_id: str
    difficulty: DifficultyLevel
    objective: str
    max_steps: int
    budget_limit: int
    budget_used: int = 0
    invalid_actions: int = 0
    loop_actions: int = 0
    submitted: bool = False
    done: bool = False
    final_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_action_error: Optional[str] = None
    summary: str = ""
    alert_status: Dict[str, AlertRuntimeStatus]
    action_history: List[str] = Field(default_factory=list)
    inspection_log: List[str] = Field(default_factory=list)


class RewardBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_tax: float = 0.0
    validity: float = 0.0
    novelty: float = 0.0
    triage: float = 0.0
    progress: float = 0.0
    completion: float = 0.0
    loop_penalty: float = 0.0
    noop_penalty: float = 0.0
    total: float = 0.0


class GradeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    decision_accuracy: float = Field(ge=0.0, le=1.0)
    severity_accuracy: float = Field(ge=0.0, le=1.0)
    coverage: float = Field(ge=0.0, le=1.0)
    evidence_ratio: float = Field(ge=0.0, le=1.0)
    sla_ratio: float = Field(ge=0.0, le=1.0)
    summary_ratio: float = Field(ge=0.0, le=1.0)
    efficiency: float = Field(ge=0.0, le=1.0)
    penalties: float = 0.0
