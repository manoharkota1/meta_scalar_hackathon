from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from .graders import grade_submission, progress_score
from .models import (
    ActionType,
    AlertQueueItem,
    AlertRuntimeStatus,
    DecisionType,
    ReviewAction,
    ReviewObservation,
    ReviewState,
    TaskDefinition,
)
from .reward import compute_step_reward
from .tasks import load_tasks, ordered_task_ids


class CodeReviewTriageEnvironment:
    """Real-world code review and bug triage simulator for OpenEnv."""

    ACTION_COST = {
        ActionType.INSPECT_ALERT: 1,
        ActionType.INSPECT_FILE: 2,
        ActionType.INSPECT_TESTS: 2,
        ActionType.TRIAGE_ALERT: 1,
        ActionType.ADD_NOTE: 1,
        ActionType.SUBMIT_REVIEW: 0,
    }

    def __init__(self) -> None:
        self._tasks = load_tasks()
        self._task_order = ordered_task_ids()
        self._task: Optional[TaskDefinition] = None
        self._state: Optional[ReviewState] = None
        self._last_context: str = ""

    def reset(self, task_id: Optional[str] = None) -> ReviewObservation:
        selected_task = task_id or self._task_order[0]
        if selected_task not in self._tasks:
            selected_task = self._task_order[0]

        self._task = self._tasks[selected_task]

        status_map = {
            alert.alert_id: AlertRuntimeStatus() for alert in self._task.alerts
        }

        self._state = ReviewState(
            episode_id=str(uuid4()),
            step_count=0,
            task_id=self._task.task_id,
            difficulty=self._task.difficulty,
            objective=self._task.objective,
            max_steps=self._task.max_steps,
            budget_limit=self._task.review_budget,
            alert_status=status_map,
        )

        self._last_context = (
            "Review queue initialized. Prioritize high-risk alerts and keep triage "
            "notes concise for handoff."
        )
        return self._build_observation(reward=0.0, done=False, last_error=None)

    def step(self, action: ReviewAction) -> Tuple[ReviewObservation, float, bool, Dict[str, Any]]:
        if self._state is None or self._task is None:
            obs = self.reset()
            return obs, 0.0, False, {"warning": "Environment was auto-reset."}

        if self._state.done:
            self._state.invalid_actions += 1
            self._state.last_action_error = "Episode already finished. Call reset()."
            breakdown = compute_step_reward(
                step_count=self._state.step_count,
                max_steps=self._state.max_steps,
                action_valid=False,
                is_loop=True,
                is_noop=True,
                progress_before=progress_score(self._task, self._state),
                progress_after=progress_score(self._task, self._state),
                triage_signal=-0.1,
                submitted=False,
                final_score=self._state.final_score,
            )
            obs = self._build_observation(
                reward=breakdown.total,
                done=True,
                last_error=self._state.last_action_error,
            )
            return obs, breakdown.total, True, {"reward_breakdown": breakdown.model_dump()}

        self._state.step_count += 1
        self._state.budget_used += self.ACTION_COST.get(action.action_type, 1)
        self._state.last_action_error = None

        progress_before = progress_score(self._task, self._state)

        action_valid = True
        is_loop = False
        is_noop = False
        triage_signal = 0.0
        final_grade = None

        signature = self._action_signature(action)
        if signature in self._state.action_history[-2:]:
            is_loop = True
            self._state.loop_actions += 1

        try:
            if action.action_type == ActionType.INSPECT_ALERT:
                is_noop = self._inspect_alert(action)
            elif action.action_type == ActionType.INSPECT_FILE:
                is_noop = self._inspect_file(action)
            elif action.action_type == ActionType.INSPECT_TESTS:
                is_noop = self._inspect_tests(action)
            elif action.action_type == ActionType.TRIAGE_ALERT:
                triage_signal, is_noop = self._triage_alert(action)
            elif action.action_type == ActionType.ADD_NOTE:
                is_noop = self._add_note(action)
            elif action.action_type == ActionType.SUBMIT_REVIEW:
                final_grade = self._submit_review(action)
            else:
                action_valid = False
                self._state.invalid_actions += 1
                self._state.last_action_error = "Unsupported action_type."
                self._last_context = "Unsupported action."
        except ValueError as exc:
            action_valid = False
            self._state.invalid_actions += 1
            self._state.last_action_error = str(exc)
            self._last_context = str(exc)

        self._state.action_history.append(signature)

        if self._state.step_count >= self._task.max_steps and not self._state.done:
            final_grade = grade_submission(self._task, self._state)
            self._state.final_score = final_grade.score
            self._state.done = True
            self._last_context = "Step limit reached. Episode auto-submitted for grading."

        progress_after = progress_score(self._task, self._state)

        breakdown = compute_step_reward(
            step_count=self._state.step_count,
            max_steps=self._state.max_steps,
            action_valid=action_valid,
            is_loop=is_loop,
            is_noop=is_noop,
            progress_before=progress_before,
            progress_after=progress_after,
            triage_signal=triage_signal,
            submitted=self._state.submitted,
            final_score=self._state.final_score if self._state.done else None,
        )

        obs = self._build_observation(
            reward=breakdown.total,
            done=self._state.done,
            last_error=self._state.last_action_error,
        )

        info: Dict[str, Any] = {
            "reward_breakdown": breakdown.model_dump(),
            "progress_before": progress_before,
            "progress_after": progress_after,
            "budget_used": self._state.budget_used,
            "budget_limit": self._state.budget_limit,
        }
        if final_grade is not None:
            info["grade"] = final_grade.model_dump()

        return obs, breakdown.total, self._state.done, info

    def state(self) -> ReviewState:
        if self._state is None:
            raise RuntimeError("Environment has not been reset yet.")
        return self._state

    def close(self) -> None:
        self._task = None
        self._state = None
        self._last_context = ""

    def _alert_or_raise(self, alert_id: Optional[str]):
        if self._task is None or self._state is None:
            raise ValueError("Environment not initialized.")
        if not alert_id:
            raise ValueError("alert_id is required for this action.")

        for alert in self._task.alerts:
            if alert.alert_id == alert_id:
                return alert, self._state.alert_status[alert_id]

        raise ValueError("Unknown alert_id.")

    def _inspect_alert(self, action: ReviewAction) -> bool:
        alert, status = self._alert_or_raise(action.alert_id)
        already = status.inspected_alert
        status.inspected_alert = True
        self._state.inspection_log.append(f"alert:{alert.alert_id}")
        self._last_context = (
            f"[{alert.alert_id}] {alert.title}\n"
            f"Signal: {alert.tool_signal}\n"
            f"Context: {alert.alert_context}"
        )
        return already

    def _inspect_file(self, action: ReviewAction) -> bool:
        alert, status = self._alert_or_raise(action.alert_id)
        already = status.inspected_file
        status.inspected_file = True
        self._state.inspection_log.append(f"file:{alert.alert_id}")
        self._last_context = (
            f"[{alert.alert_id}] File {alert.file_path}\n"
            f"Implementation details: {alert.file_context}"
        )
        return already

    def _inspect_tests(self, action: ReviewAction) -> bool:
        alert, status = self._alert_or_raise(action.alert_id)
        already = status.inspected_tests
        status.inspected_tests = True
        self._state.inspection_log.append(f"tests:{alert.alert_id}")
        self._last_context = (
            f"[{alert.alert_id}] Test signal\n"
            f"Test evidence: {alert.test_context}"
        )
        return already

    def _triage_alert(self, action: ReviewAction) -> Tuple[float, bool]:
        alert, status = self._alert_or_raise(action.alert_id)

        if action.decision is None:
            raise ValueError("decision is required for triage_alert.")
        if action.decision == DecisionType.BUG and action.severity is None:
            raise ValueError("severity is required when decision=bug.")

        prior_decision = status.triaged_decision
        prior_severity = status.triaged_severity

        status.triaged_decision = action.decision
        status.triaged_severity = action.severity if action.decision == DecisionType.BUG else None
        if status.first_triage_step is None:
            status.first_triage_step = self._state.step_count

        correct_decision = action.decision == alert.expected_decision
        triage_signal = 0.14 if correct_decision else -0.12

        if action.decision == DecisionType.BUG:
            if action.severity == alert.expected_severity:
                triage_signal += 0.08
            else:
                triage_signal -= 0.05

        self._last_context = (
            f"[{alert.alert_id}] triaged as {status.triaged_decision.value}"
        )

        is_noop = (
            prior_decision == status.triaged_decision
            and prior_severity == status.triaged_severity
        )

        return triage_signal, is_noop

    def _add_note(self, action: ReviewAction) -> bool:
        alert, status = self._alert_or_raise(action.alert_id)
        note = action.note.strip()
        if len(note) < 8:
            raise ValueError("note must contain at least 8 characters.")

        duplicate = note in status.notes
        if not duplicate:
            status.notes.append(note)
        self._last_context = f"[{alert.alert_id}] note recorded."
        return duplicate

    def _submit_review(self, action: ReviewAction):
        summary = action.summary.strip()
        if len(summary) < 24:
            raise ValueError("summary must contain at least 24 characters.")

        self._state.summary = summary
        self._state.submitted = True
        self._state.done = True

        grade = grade_submission(self._task, self._state)
        self._state.final_score = grade.score
        self._last_context = "Review submitted for deterministic grading."
        return grade

    def _action_signature(self, action: ReviewAction) -> str:
        parts = [
            action.action_type.value,
            action.alert_id or "-",
            action.decision.value if action.decision else "-",
            action.severity.value if action.severity else "-",
            action.note.strip(),
            action.summary.strip(),
        ]
        return "|".join(parts)

    def _build_observation(
        self,
        *,
        reward: float,
        done: bool,
        last_error: Optional[str],
    ) -> ReviewObservation:
        if self._task is None or self._state is None:
            raise RuntimeError("Environment is not initialized.")

        queue = []
        for alert in self._task.alerts:
            status = self._state.alert_status[alert.alert_id]
            queue.append(
                AlertQueueItem(
                    alert_id=alert.alert_id,
                    title=alert.title,
                    file_path=alert.file_path,
                    tool_priority=alert.tool_priority,
                    tool_signal=alert.tool_signal,
                    required_views=alert.required_views,
                    inspected_alert=status.inspected_alert,
                    inspected_file=status.inspected_file,
                    inspected_tests=status.inspected_tests,
                    triaged_decision=status.triaged_decision,
                    triaged_severity=status.triaged_severity,
                )
            )

        return ReviewObservation(
            task_id=self._task.task_id,
            difficulty=self._task.difficulty,
            objective=self._task.objective,
            step_count=self._state.step_count,
            max_steps=self._task.max_steps,
            budget_used=self._state.budget_used,
            budget_limit=self._state.budget_limit,
            progress_score=progress_score(self._task, self._state),
            queue=queue,
            focused_context=self._last_context,
            last_action_error=last_error,
            done=done,
            reward=reward,
            metadata={
                "submission_requirements": self._task.submission_requirements,
                "invalid_actions": self._state.invalid_actions,
                "loop_actions": self._state.loop_actions,
                "final_score": self._state.final_score,
            },
        )
