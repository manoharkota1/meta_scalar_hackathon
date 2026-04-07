from __future__ import annotations

from typing import Dict

from .models import AlertRuntimeStatus, DecisionType, GradeResult, ReviewState, TaskDefinition


def _safe_ratio(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return max(0.0, min(1.0, num / den))


def progress_score(task: TaskDefinition, state: ReviewState) -> float:
    """Dense progress signal that can be computed at every step."""
    total_alerts = float(len(task.alerts))
    if total_alerts == 0:
        return 0.0

    triaged = 0.0
    inspected_coverage = 0.0
    correctly_triaged = 0.0

    for alert in task.alerts:
        status = state.alert_status[alert.alert_id]
        if status.triaged_decision is not None:
            triaged += 1.0

        required = set(alert.required_views)
        viewed = set()
        if status.inspected_alert:
            viewed.add("alert")
        if status.inspected_file:
            viewed.add("file")
        if status.inspected_tests:
            viewed.add("tests")
        inspected_coverage += _safe_ratio(
            len(required.intersection(viewed)),
            len(required),
        )

        if status.triaged_decision == alert.expected_decision:
            if alert.expected_decision == DecisionType.BUG:
                if status.triaged_severity == alert.expected_severity:
                    correctly_triaged += 1.0
                else:
                    correctly_triaged += 0.5
            else:
                correctly_triaged += 1.0

    triage_ratio = triaged / total_alerts
    inspect_ratio = inspected_coverage / total_alerts
    correctness_ratio = correctly_triaged / total_alerts

    score = (0.40 * triage_ratio) + (0.30 * inspect_ratio) + (0.30 * correctness_ratio)
    return max(0.0, min(1.0, score))


def _summary_ratio(summary: str) -> float:
    text = summary.strip().lower()
    if not text:
        return 0.0
    ratio = 0.2
    if len(text) >= 40:
        ratio += 0.4
    if "ship" in text or "merge" in text:
        ratio += 0.2
    if "risk" in text:
        ratio += 0.1
    if "owner" in text or "handoff" in text:
        ratio += 0.1
    return min(1.0, ratio)


def _efficiency(task: TaskDefinition, state: ReviewState) -> float:
    baseline = max(1.0, float(len(task.alerts) * 3))
    step_pressure = max(0.0, state.step_count - baseline) / max(1.0, task.max_steps)
    budget_pressure = max(0.0, state.budget_used - task.review_budget) / max(
        1.0, task.review_budget
    )

    raw = 1.0 - (0.45 * step_pressure) - (0.35 * budget_pressure)
    raw -= 0.08 * state.invalid_actions
    raw -= 0.04 * state.loop_actions
    return max(0.0, min(1.0, raw))


def grade_submission(task: TaskDefinition, state: ReviewState) -> GradeResult:
    total_alerts = float(len(task.alerts))

    decision_correct = 0.0
    severity_correct = 0.0
    coverage_count = 0.0
    evidence_count = 0.0

    sla_deadlines = [a for a in task.alerts if a.sla_deadline_step is not None]
    sla_met = 0.0

    bug_alerts = [a for a in task.alerts if a.expected_decision == DecisionType.BUG]

    for alert in task.alerts:
        status = state.alert_status[alert.alert_id]

        if status.triaged_decision is not None:
            coverage_count += 1.0

        if status.triaged_decision == alert.expected_decision:
            decision_correct += 1.0

        if alert.expected_decision == DecisionType.BUG:
            if (
                status.triaged_decision == DecisionType.BUG
                and status.triaged_severity == alert.expected_severity
            ):
                severity_correct += 1.0

        required_ok = _required_views_covered(alert.required_views, status)
        if status.triaged_decision is not None and required_ok:
            evidence_count += 1.0

        if alert.sla_deadline_step is not None and status.first_triage_step is not None:
            if status.first_triage_step <= alert.sla_deadline_step:
                sla_met += 1.0

    decision_accuracy = _safe_ratio(decision_correct, total_alerts)
    severity_accuracy = _safe_ratio(severity_correct, float(len(bug_alerts)))
    coverage = _safe_ratio(coverage_count, total_alerts)
    evidence_ratio = _safe_ratio(evidence_count, total_alerts)
    sla_ratio = _safe_ratio(sla_met, float(len(sla_deadlines))) if sla_deadlines else 1.0
    summary_ratio = _summary_ratio(state.summary)
    efficiency = _efficiency(task, state)

    penalties = (0.03 * state.invalid_actions) + (0.02 * state.loop_actions)

    weighted = (
        0.30 * decision_accuracy
        + 0.15 * severity_accuracy
        + 0.15 * coverage
        + 0.15 * evidence_ratio
        + 0.10 * sla_ratio
        + 0.05 * summary_ratio
        + 0.10 * efficiency
    )

    final = max(0.0, min(1.0, weighted - penalties))

    return GradeResult(
        score=final,
        decision_accuracy=decision_accuracy,
        severity_accuracy=severity_accuracy,
        coverage=coverage,
        evidence_ratio=evidence_ratio,
        sla_ratio=sla_ratio,
        summary_ratio=summary_ratio,
        efficiency=efficiency,
        penalties=penalties,
    )


def _required_views_covered(required_views, status: AlertRuntimeStatus) -> bool:
    mapping: Dict[str, bool] = {
        "alert": status.inspected_alert,
        "file": status.inspected_file,
        "tests": status.inspected_tests,
    }
    for view in required_views:
        if not mapping.get(view.value, False):
            return False
    return True
