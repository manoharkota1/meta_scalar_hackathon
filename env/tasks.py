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
            "Coordinate a 4-way suburban intersection during rush hour while "
            "ensuring ambulance priority through the westbound corridor."
        ),
        max_steps=8,
        review_budget=10,
        submission_requirements=[
            "Triaging every alert is mandatory.",
            "At least one note should mention emergency response impact.",
            "Final summary must mention intersection safety readiness.",
        ],
        alerts=[
            AlertSpec(
                alert_id="E-A1",
                title="Emergency vehicle preemption ignored in westbound phase selector",
                file_path="traffic/intersection_controller.py",
                tool_priority=5,
                tool_signal="Safety analyzer: ev-preemption-missed",
                alert_context=(
                    "if westbound_queue > threshold: grant_green('westbound')"
                ),
                file_context=(
                    "Branch grants normal queue optimization but does not check "
                    "ambulance beacon state before setting phase."
                ),
                test_context=(
                    "No regression test covers simultaneous heavy queue and "
                    "active emergency beacon."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.HIGH,
                sla_deadline_step=4,
                remediation_hint=(
                    "Check emergency beacon before normal queue logic and enforce "
                    "preemption hold window for westbound ambulance passage."
                ),
            ),
            AlertSpec(
                alert_id="E-A2",
                title="Pedestrian wait starvation warning appears under simulation jitter",
                file_path="tests/test_pedestrian_cycle.py",
                tool_priority=2,
                tool_signal="Telemetry lint: starvation-threshold",
                alert_context="assert ped_wait_s < 45",
                file_context=(
                    "Warning originates from replay mode where virtual clock step "
                    "drift inflates measured wait time."
                ),
                test_context=(
                    "Simulation harness applies deterministic jitter; production "
                    "controller caps pedestrian wait correctly."
                ),
                required_views=[ViewType.ALERT, ViewType.TESTS],
                expected_decision=DecisionType.FALSE_POSITIVE,
                expected_severity=None,
                sla_deadline_step=None,
                remediation_hint=(
                    "Keep as false positive and document simulation jitter behavior "
                    "near the assertion."
                ),
            ),
        ],
    )


def _medium_task() -> TaskDefinition:
    return TaskDefinition(
        task_id="medium-downtown-commuter-wave",
        difficulty=DifficultyLevel.MEDIUM,
        objective=(
            "Manage downtown commuter-wave timing with mixed safety and reliability "
            "alerts while preserving emergency corridor responsiveness."
        ),
        max_steps=14,
        review_budget=16,
        submission_requirements=[
            "All alerts must receive decision plus severity when applicable.",
            "Critical or high findings require concrete remediation notes.",
            "Summary must include fallback signal plan and monitoring strategy.",
        ],
        alerts=[
            AlertSpec(
                alert_id="M-A1",
                title="Conflicting green phases can be emitted on stale clock window",
                file_path="traffic/phase_scheduler.py",
                tool_priority=5,
                tool_signal="Safety rule: conflicting-green-window",
                alert_context="if now_ms - last_sync_ms > 2000: push_cached_phase_pair()",
                file_context=(
                    "Cached pair may contain north-south and east-west green phases "
                    "when sync lag exceeds threshold."
                ),
                test_context=(
                    "Current tests do not include stale clock injection combined with "
                    "phase reconciliation."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.CRITICAL,
                sla_deadline_step=6,
                remediation_hint=(
                    "Invalidate cached phase pair on stale sync and force all-red "
                    "barrier before selecting a single direction."
                ),
            ),
            AlertSpec(
                alert_id="M-A2",
                title="Possible null sensor access in lane demand estimator",
                file_path="traffic/demand_estimator.py",
                tool_priority=3,
                tool_signal="Pyright: Optional access",
                alert_context="sensor_snapshot['northbound'].queue_length",
                file_context=(
                    "Code path follows a guard that substitutes fallback queue values "
                    "when a sensor packet is missing."
                ),
                test_context=(
                    "Property tests include missing northbound packets and estimator "
                    "returns safe defaults."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.FALSE_POSITIVE,
                expected_severity=None,
                sla_deadline_step=None,
                remediation_hint=(
                    "Document guard behavior and add narrow inline suppression to avoid "
                    "future confusion."
                ),
            ),
            AlertSpec(
                alert_id="M-A3",
                title="No retry cap for upstream reroute advisory service",
                file_path="traffic/reroute_orchestrator.py",
                tool_priority=4,
                tool_signal="Reliability rule: unbounded-retry",
                alert_context="while True: advisory = route_hub.fetch_override(...)",
                file_context=(
                    "Retry loop can block preemption worker when route hub returns "
                    "transient 502 responses."
                ),
                test_context=(
                    "Fault-injection tests show emergency command lag spikes during "
                    "route hub outages."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.HIGH,
                sla_deadline_step=10,
                remediation_hint=(
                    "Add bounded retries with exponential backoff and fail over to "
                    "local timing plan after max attempts."
                ),
            ),
        ],
    )


def _hard_task() -> TaskDefinition:
    return TaskDefinition(
        task_id="hard-citywide-evacuation-incident",
        difficulty=DifficultyLevel.HARD,
        objective=(
            "Run incident-mode control for a city-center intersection during "
            "evacuation traffic with strict emergency-priority SLAs."
        ),
        max_steps=20,
        review_budget=18,
        submission_requirements=[
            "All alerts must be triaged.",
            "Critical alerts should be triaged before their SLA deadlines.",
            "Summary must include: go/no-go signal plan, top two risks, and owner handoff.",
        ],
        alerts=[
            AlertSpec(
                alert_id="H-A1",
                title="Emergency preemption command delayed by batch dispatcher",
                file_path="traffic/preemption_dispatch.py",
                tool_priority=5,
                tool_signal="Internal safety scanner: delayed-preemption",
                alert_context="flush_every_s = 15; dispatch_buffer.append(command)",
                file_context=(
                    "Batching adds up to 15 seconds before siren-triggered phase "
                    "change is sent to hardware."
                ),
                test_context=(
                    "No integration test validates sub-second dispatch latency for "
                    "ambulance preemption commands."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.CRITICAL,
                sla_deadline_step=6,
                remediation_hint=(
                    "Bypass batching for emergency commands and enforce immediate "
                    "dispatch path with latency alarms."
                ),
            ),
            AlertSpec(
                alert_id="H-A2",
                title="Vehicle identifiers exposed in incident telemetry logs",
                file_path="traffic/incident_logging.py",
                tool_priority=4,
                tool_signal="Privacy detector: plate+phone exposure",
                alert_context="logger.info({'plate': vehicle.plate, 'phone': owner.phone})",
                file_context=(
                    "Telemetry middleware emits direct vehicle and owner identifiers "
                    "before redaction."
                ),
                test_context=(
                    "Snapshot tests assert key presence but do not verify redaction."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.HIGH,
                sla_deadline_step=12,
                remediation_hint=(
                    "Hash or drop direct identifiers and add regression checks for "
                    "sanitized telemetry payloads."
                ),
            ),
            AlertSpec(
                alert_id="H-A3",
                title="Potential path traversal in timing-plan import endpoint",
                file_path="traffic/plan_import_service.py",
                tool_priority=5,
                tool_signal="Semgrep: path-traversal",
                alert_context="open(f'/plans/{request.filename}', 'wb')",
                file_context=(
                    "Filename is accepted from operator input without normalization or "
                    "allow-listing."
                ),
                test_context=(
                    "No tests attempt '../../' payloads in timing-plan filename."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.CRITICAL,
                sla_deadline_step=9,
                remediation_hint=(
                    "Validate filename against strict regex and resolve paths under a "
                    "safe plan directory root."
                ),
            ),
            AlertSpec(
                alert_id="H-A4",
                title="Static analyzer flags deadlock risk in signal worker locks",
                file_path="traffic/signal_worker_pool.py",
                tool_priority=3,
                tool_signal="Concurrency lint: lock-order",
                alert_context="with pool_lock: ... with stats_lock:",
                file_context=(
                    "Code acquires locks in a consistent global order across controller "
                    "call sites."
                ),
                test_context=(
                    "Stress tests run 10k iterations with no deadlock and lock-order "
                    "assertions enabled."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.FALSE_POSITIVE,
                expected_severity=None,
                sla_deadline_step=None,
                remediation_hint=(
                    "Retain existing lock-order contract and document it near pool_lock "
                    "for future maintainers."
                ),
            ),
            AlertSpec(
                alert_id="H-A5",
                title="Quadratic loop in adaptive phase merge",
                file_path="traffic/phase_plan_merge.py",
                tool_priority=4,
                tool_signal="Perf rule: O(n^2)-merge",
                alert_context="for lhs in plans: for rhs in plans:",
                file_context=(
                    "Large incident plans can contain 3k+ phase segments during "
                    "evacuation-mode sync."
                ),
                test_context=(
                    "Benchmark CI indicates p95 merge latency exceeds control SLO for "
                    "large evacuation plans."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.MEDIUM,
                sla_deadline_step=15,
                remediation_hint=(
                    "Replace nested scan with hash-join style merge keyed by phase id."
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
