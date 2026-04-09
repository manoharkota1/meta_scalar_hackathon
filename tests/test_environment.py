from env.environment import AutonomousTrafficControlEnvironment
from env.models import ActionType, ReviewAction
from env.tasks import load_tasks


def _play_deterministic_episode(task_id: str) -> float:
    env = AutonomousTrafficControlEnvironment()
    task = load_tasks()[task_id]
    truth = {
        alert.alert_id: (alert.expected_decision, alert.expected_severity)
        for alert in task.alerts
    }

    obs = env.reset(task_id=task_id)

    for _ in range(task.max_steps):
        for item in obs.queue:
            if not item.inspected_alert:
                obs, _, done, _ = env.step(
                    ReviewAction(action_type=ActionType.INSPECT_ALERT, alert_id=item.alert_id)
                )
                break
            if item.required_views and (not item.inspected_file) and any(
                view.value == "file" for view in item.required_views
            ):
                obs, _, done, _ = env.step(
                    ReviewAction(action_type=ActionType.INSPECT_FILE, alert_id=item.alert_id)
                )
                break
            if item.required_views and (not item.inspected_tests) and any(
                view.value == "tests" for view in item.required_views
            ):
                obs, _, done, _ = env.step(
                    ReviewAction(action_type=ActionType.INSPECT_TESTS, alert_id=item.alert_id)
                )
                break
            if item.triaged_decision is None:
                decision, severity = truth[item.alert_id]
                obs, _, done, _ = env.step(
                    ReviewAction(
                        action_type=ActionType.TRIAGE_ALERT,
                        alert_id=item.alert_id,
                        decision=decision,
                        severity=severity,
                    )
                )
                break
        else:
            obs, _, done, _ = env.step(
                ReviewAction(
                    action_type=ActionType.SUBMIT_REVIEW,
                    summary=(
                        "Go/no-go: no-go until emergency preemption latency and phase conflict "
                        "hazards are fixed. Owner handoff required."
                    ),
                )
            )

        if done:
            break

    final_state = env.state()
    env.close()
    return final_state.final_score


def test_easy_task_completes_with_high_score() -> None:
    score = _play_deterministic_episode("easy-four-way-rush-hour")
    assert score >= 0.95


def test_medium_task_completes_with_high_score() -> None:
    score = _play_deterministic_episode("medium-downtown-commuter-wave")
    assert score >= 0.90


def test_invalid_triage_action_sets_error() -> None:
    env = AutonomousTrafficControlEnvironment()
    obs = env.reset(task_id="easy-four-way-rush-hour")
    obs, _, _, _ = env.step(
        ReviewAction(
            action_type=ActionType.TRIAGE_ALERT,
            alert_id=obs.queue[0].alert_id,
        )
    )

    assert obs.last_action_error is not None
    assert "decision is required" in obs.last_action_error
    env.close()
