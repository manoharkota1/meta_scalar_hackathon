from __future__ import annotations

from typing import Dict, List

from .models import (
    AlertSpec,
    DecisionType,
    DifficultyLevel,
    SeverityLevel,
    TaskDefinition,
    ViewType,
)


def _easy_task() -> TaskDefinition:
    return TaskDefinition(
        task_id="easy-four-way-rush-hour",
        difficulty=DifficultyLevel.EASY,
        objective=(
            "Keep a suburban 4-way junction stable during rush hour while "
            "clearing a westbound ambulance path."
        ),
        max_steps=8,
        review_budget=10,
        submission_requirements=[
            "Every alert must receive a decision.",
            "Include at least one note about emergency response delay impact.",
            "Final summary should state whether automatic control is safe to continue.",
        ],
        alerts=[
            AlertSpec(
                alert_id="E-A1",
                title="Westbound green logic skips ambulance preemption check",
                file_path="traffic/intersection_controller.py",
                tool_priority=5,
                tool_signal="Safety check: preemption_not_applied",
                alert_context=(
                    "if westbound_queue > threshold: grant_green('westbound')"
                ),
                file_context=(
                    "Queue optimization path sets westbound green first and only "
                    "later inspects emergency beacons."
                ),
                test_context=(
                    "No test covers the combined case of heavy queue pressure and "
                    "active ambulance beacon."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.HIGH,
                sla_deadline_step=4,
                remediation_hint=(
                    "Evaluate emergency state before queue heuristics and enforce a "
                    "minimum preemption hold interval."
                ),
            ),
            AlertSpec(
                alert_id="E-A2",
                title="Pedestrian starvation warning appears only in replay jitter mode",
                file_path="tests/test_pedestrian_cycle.py",
                tool_priority=2,
                tool_signal="Telemetry check: ped_wait_threshold",
                alert_context="assert ped_wait_s < 45",
                file_context=(
                    "Replay mode can stretch virtual clock ticks, inflating computed "
                    "wait time in the assertion path."
                ),
                test_context=(
                    "Production controller keeps pedestrian wait bounded; this warning "
                    "shows up under synthetic jitter only."
                ),
                required_views=[ViewType.ALERT, ViewType.TESTS],
                expected_decision=DecisionType.FALSE_POSITIVE,
                expected_severity=None,
                sla_deadline_step=None,
                remediation_hint=(
                    "Mark as false positive and document replay-mode timing drift near "
                    "the test assertion."
                ),
            ),
        ],
    )


def _medium_task() -> TaskDefinition:
    return TaskDefinition(
        task_id="medium-downtown-commuter-wave",
        difficulty=DifficultyLevel.MEDIUM,
        objective=(
            "Handle downtown commuter surge with mixed safety/reliability findings "
            "while keeping emergency corridors responsive."
        ),
        max_steps=14,
        review_budget=16,
        submission_requirements=[
            "Decide all alerts, including severity for true defects.",
            "High or critical defects need concrete remediation notes.",
            "Summary must include fallback timing mode and monitoring plan.",
        ],
        alerts=[
            AlertSpec(
                alert_id="M-A1",
                title="Stale sync window can emit conflicting green phases",
                file_path="traffic/phase_scheduler.py",
                tool_priority=5,
                tool_signal="Safety rule: conflicting_green_phase",
                alert_context="if now_ms - last_sync_ms > 2000: push_cached_phase_pair()",
                file_context=(
                    "When sync is stale, cached output may contain both north-south "
                    "and east-west green simultaneously."
                ),
                test_context=(
                    "Tests do not combine stale-clock injection with reconciliation "
                    "logic in the same case."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.CRITICAL,
                sla_deadline_step=6,
                remediation_hint=(
                    "Invalidate stale cached pairs and force all-red clearance before "
                    "activating one direction."
                ),
            ),
            AlertSpec(
                alert_id="M-A2",
                title="Possible null read in lane demand estimator",
                file_path="traffic/demand_estimator.py",
                tool_priority=3,
                tool_signal="Pyright: Optional access",
                alert_context="sensor_snapshot['northbound'].queue_length",
                file_context=(
                    "Estimator applies a guard and fallback queue value whenever the "
                    "northbound packet is absent."
                ),
                test_context=(
                    "Property tests include missing northbound payloads and confirm "
                    "safe defaults."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.FALSE_POSITIVE,
                expected_severity=None,
                sla_deadline_step=None,
                remediation_hint=(
                    "Document the fallback guard and add narrow inline suppression for "
                    "this line only."
                ),
            ),
            AlertSpec(
                alert_id="M-A3",
                title="Reroute advisory call has no retry cap",
                file_path="traffic/reroute_orchestrator.py",
                tool_priority=4,
                tool_signal="Reliability rule: infinite_retry",
                alert_context="while True: advisory = route_hub.fetch_override(...)",
                file_context=(
                    "Worker can stay stuck in retry loop if route hub keeps returning "
                    "transient 502 responses."
                ),
                test_context=(
                    "Fault-injection run shows emergency command lag spikes when the "
                    "route hub is unavailable."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.HIGH,
                sla_deadline_step=10,
                remediation_hint=(
                    "Set max retry count, keep exponential backoff, and fail over to "
                    "local timing plan when attempts are exhausted."
                ),
            ),
        ],
    )


def _hard_task() -> TaskDefinition:
    return TaskDefinition(
        task_id="hard-citywide-evacuation-incident",
        difficulty=DifficultyLevel.HARD,
        objective=(
            "Operate a city-center junction in evacuation mode under strict "
            "emergency-priority deadlines."
        ),
        max_steps=20,
        review_budget=18,
        submission_requirements=[
            "Resolve every alert.",
            "Resolve critical alerts before deadline where possible.",
            "Summary must include go/no-go, top two risks, and owner handoff.",
        ],
        alerts=[
            AlertSpec(
                alert_id="H-A1",
                title="Batch dispatcher delays emergency preemption command",
                file_path="traffic/preemption_dispatch.py",
                tool_priority=5,
                tool_signal="Safety scanner: preemption_dispatch_delay",
                alert_context="flush_every_s = 15; dispatch_buffer.append(command)",
                file_context=(
                    "Batch path can delay siren-triggered phase changes by up to "
                    "15 seconds before hardware dispatch."
                ),
                test_context=(
                    "There is no integration test asserting sub-second dispatch for "
                    "ambulance preemption commands."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.CRITICAL,
                sla_deadline_step=6,
                remediation_hint=(
                    "Bypass batching for emergency commands and attach latency alarms "
                    "to immediate dispatch path."
                ),
            ),
            AlertSpec(
                alert_id="H-A2",
                title="Incident telemetry logs expose direct vehicle identifiers",
                file_path="traffic/incident_logging.py",
                tool_priority=4,
                tool_signal="Privacy detector: direct_identifier_leak",
                alert_context="logger.info({'plate': vehicle.plate, 'phone': owner.phone})",
                file_context=(
                    "Logging middleware writes plate and owner contact fields before "
                    "redaction rules run."
                ),
                test_context=(
                    "Snapshot tests only check key existence and miss redaction checks."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.HIGH,
                sla_deadline_step=12,
                remediation_hint=(
                    "Drop or hash direct identifiers and add regression assertions for "
                    "sanitized telemetry payloads."
                ),
            ),
            AlertSpec(
                alert_id="H-A3",
                title="Timing-plan import endpoint accepts path traversal payloads",
                file_path="traffic/plan_import_service.py",
                tool_priority=5,
                tool_signal="Semgrep: path-traversal",
                alert_context="open(f'/plans/{request.filename}', 'wb')",
                file_context=(
                    "Operator-supplied filename is written directly without normalization "
                    "or allow-list checks."
                ),
                test_context=(
                    "No tests attempt ../../ traversal in timing-plan filenames."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.CRITICAL,
                sla_deadline_step=9,
                remediation_hint=(
                    "Validate filename with strict allow-list and resolve writes under "
                    "a fixed plan root directory."
                ),
            ),
            AlertSpec(
                alert_id="H-A4",
                title="Static analyzer flags deadlock risk in worker lock order",
                file_path="traffic/signal_worker_pool.py",
                tool_priority=3,
                tool_signal="Concurrency lint: lock-order",
                alert_context="with pool_lock: ... with stats_lock:",
                file_context=(
                    "Lock acquisition order is consistent across call sites in current "
                    "implementation."
                ),
                test_context=(
                    "Stress suite runs 10k iterations with lock-order assertions and no "
                    "deadlock observed."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.FALSE_POSITIVE,
                expected_severity=None,
                sla_deadline_step=None,
                remediation_hint=(
                    "Keep the lock-order contract and document it near pool_lock for "
                    "future edits."
                ),
            ),
            AlertSpec(
                alert_id="H-A5",
                title="Adaptive phase merge uses quadratic loop",
                file_path="traffic/phase_plan_merge.py",
                tool_priority=4,
                tool_signal="Perf rule: O(n^2)-merge",
                alert_context="for lhs in plans: for rhs in plans:",
                file_context=(
                    "Large evacuation plans can exceed 3k phase segments during sync "
                    "windows."
                ),
                test_context=(
                    "Benchmark pipeline shows p95 merge time exceeding SLO on large "
                    "evacuation plans."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.MEDIUM,
                sla_deadline_step=15,
                remediation_hint=(
                    "Replace nested iteration with hash-indexed merge keyed by phase id."
                ),
            ),
        ],
    )


def load_tasks() -> Dict[str, TaskDefinition]:
    tasks: List[TaskDefinition] = [_easy_task(), _medium_task(), _hard_task()]
    return {task.task_id: task for task in tasks}


def ordered_task_ids() -> List[str]:
    return [
        "easy-four-way-rush-hour",
        "medium-downtown-commuter-wave",
        "hard-citywide-evacuation-incident",
    ]
