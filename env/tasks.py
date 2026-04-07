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
        task_id="easy-pr-login-hotfix",
        difficulty=DifficultyLevel.EASY,
        objective=(
            "Review a small authentication hotfix PR and triage two scanner alerts "
            "before merge."
        ),
        max_steps=8,
        review_budget=10,
        submission_requirements=[
            "Triaging every alert is mandatory.",
            "At least one note should mention user impact.",
            "Final summary must mention merge readiness.",
        ],
        alerts=[
            AlertSpec(
                alert_id="E-A1",
                title="String-formatted SQL query in credential check",
                file_path="auth/login_repository.py",
                tool_priority=5,
                tool_signal="Bandit B608",
                alert_context=(
                    "SELECT id FROM users WHERE email = '%s' AND password_hash = '%s'"
                ),
                file_context=(
                    "The query is assembled with f-strings and executed directly "
                    "through cursor.execute(query)."
                ),
                test_context=(
                    "No parameterization tests exist for malicious email input."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.HIGH,
                sla_deadline_step=4,
                remediation_hint=(
                    "Switch to parameterized placeholders and add SQL injection "
                    "tests around email input."
                ),
            ),
            AlertSpec(
                alert_id="E-A2",
                title="Flaky timeout assertion in unit test",
                file_path="tests/test_login_rate_limit.py",
                tool_priority=2,
                tool_signal="Custom lint: timeout-threshold",
                alert_context="assert elapsed_ms < 2200",
                file_context=(
                    "The assertion checks an upper bound in a deterministic fake "
                    "clock test."
                ),
                test_context=(
                    "The suite monkeypatches time.monotonic(), so runtime jitter "
                    "does not apply in CI."
                ),
                required_views=[ViewType.ALERT, ViewType.TESTS],
                expected_decision=DecisionType.FALSE_POSITIVE,
                expected_severity=None,
                sla_deadline_step=None,
                remediation_hint=(
                    "Keep as false positive but add a one-line comment to explain "
                    "the fake clock usage."
                ),
            ),
        ],
    )


def _medium_task() -> TaskDefinition:
    return TaskDefinition(
        task_id="medium-pr-billing-worker",
        difficulty=DifficultyLevel.MEDIUM,
        objective=(
            "Triage a billing worker refactor with mixed reliability and security "
            "alerts while preserving on-call stability."
        ),
        max_steps=14,
        review_budget=16,
        submission_requirements=[
            "All alerts must receive decision plus severity when applicable.",
            "Critical or high findings require concrete remediation notes.",
            "Summary must include rollback risk and monitoring plan.",
        ],
        alerts=[
            AlertSpec(
                alert_id="M-A1",
                title="Unsafe YAML deserialization in worker config loader",
                file_path="billing/config_loader.py",
                tool_priority=5,
                tool_signal="Semgrep: pyyaml-unsafe-load",
                alert_context="yaml.load(raw_config, Loader=yaml.Loader)",
                file_context=(
                    "The worker reads tenant-provided YAML templates from object "
                    "storage and executes post-load hooks."
                ),
                test_context=(
                    "Existing tests cover valid YAML only and do not include crafted "
                    "payloads."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.CRITICAL,
                sla_deadline_step=6,
                remediation_hint=(
                    "Use yaml.safe_load and block executable tags. Add a malicious "
                    "fixture regression test."
                ),
            ),
            AlertSpec(
                alert_id="M-A2",
                title="Possible null dereference in customer plan parser",
                file_path="billing/plan_parser.py",
                tool_priority=3,
                tool_signal="Pyright: Optional access",
                alert_context="plan['tiers'][0]['limit']",
                file_context=(
                    "Code path follows a guard that returns early when tiers is empty."
                ),
                test_context=(
                    "Property tests include empty tiers and parser returns a default "
                    "plan safely."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.FALSE_POSITIVE,
                expected_severity=None,
                sla_deadline_step=None,
                remediation_hint=(
                    "Document why the guard is sufficient and suppress the analyzer "
                    "with a narrow inline comment."
                ),
            ),
            AlertSpec(
                alert_id="M-A3",
                title="No retry cap for payment provider idempotency check",
                file_path="billing/reconciliation.py",
                tool_priority=4,
                tool_signal="Reliability rule: unbounded-retry",
                alert_context="while True: resp = provider.get_status(...)",
                file_context=(
                    "The loop retries forever when provider returns transient 502, "
                    "which blocks queue workers."
                ),
                test_context=(
                    "Chaos tests show queue lag spikes under provider outage due to "
                    "stuck worker slots."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.HIGH,
                sla_deadline_step=10,
                remediation_hint=(
                    "Add bounded retries with exponential backoff and dead-letter "
                    "handoff after max attempts."
                ),
            ),
        ],
    )


def _hard_task() -> TaskDefinition:
    return TaskDefinition(
        task_id="hard-release-platform-gateway",
        difficulty=DifficultyLevel.HARD,
        objective=(
            "Run a release-candidate triage for platform gateway changes with "
            "security, reliability, and privacy findings under strict SLA pressure."
        ),
        max_steps=20,
        review_budget=18,
        submission_requirements=[
            "All alerts must be triaged.",
            "Critical alerts should be triaged before their SLA deadlines.",
            "Summary must include: ship/no-ship decision, top two risks, and owner handoff.",
        ],
        alerts=[
            AlertSpec(
                alert_id="H-A1",
                title="Authorization cache allows stale role reuse",
                file_path="gateway/authz_cache.py",
                tool_priority=5,
                tool_signal="Internal security scanner: stale-acl",
                alert_context="cache_ttl = 900; return cached_role",
                file_context=(
                    "Role revocations can take up to 15 minutes to propagate in the "
                    "new cache path."
                ),
                test_context=(
                    "No integration test covers immediate access revocation on role "
                    "downgrade."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.CRITICAL,
                sla_deadline_step=6,
                remediation_hint=(
                    "Invalidate cache on authz write events and reduce fallback TTL "
                    "to seconds, not minutes."
                ),
            ),
            AlertSpec(
                alert_id="H-A2",
                title="PII appears in structured request logs",
                file_path="gateway/request_logging.py",
                tool_priority=4,
                tool_signal="PII detector: email+phone exposure",
                alert_context="logger.info({'email': user.email, 'phone': user.phone})",
                file_context=(
                    "Logging middleware emits full user contact fields before redaction."
                ),
                test_context=(
                    "Snapshot tests assert key presence but do not assert redaction."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.HIGH,
                sla_deadline_step=12,
                remediation_hint=(
                    "Hash or drop direct identifiers and add regression tests for "
                    "sanitized logs."
                ),
            ),
            AlertSpec(
                alert_id="H-A3",
                title="Potential path traversal in export endpoint",
                file_path="gateway/export_service.py",
                tool_priority=5,
                tool_signal="Semgrep: path-traversal",
                alert_context="open(f'/exports/{request.filename}', 'wb')",
                file_context=(
                    "Filename is accepted from user input without normalization or "
                    "allow-listing."
                ),
                test_context=(
                    "No tests attempt '../../' payloads in filename."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.CRITICAL,
                sla_deadline_step=9,
                remediation_hint=(
                    "Validate filename against strict regex and resolve paths under a "
                    "safe base directory."
                ),
            ),
            AlertSpec(
                alert_id="H-A4",
                title="Static analyzer flags deadlock risk in lock ordering",
                file_path="gateway/worker_pool.py",
                tool_priority=3,
                tool_signal="Concurrency lint: lock-order",
                alert_context="with pool_lock: ... with stats_lock:",
                file_context=(
                    "Code acquires locks in a consistent global order across call sites."
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
                    "Retain existing lock-order contract and document it near pool_lock."
                ),
            ),
            AlertSpec(
                alert_id="H-A5",
                title="Quadratic loop in tenant policy merge",
                file_path="gateway/policy_merge.py",
                tool_priority=4,
                tool_signal="Perf rule: O(n^2)-merge",
                alert_context="for lhs in policies: for rhs in policies:",
                file_context=(
                    "Large enterprise tenants can have 3k+ policy entries in nightly sync."
                ),
                test_context=(
                    "Benchmark CI indicates p95 merge latency exceeds SLO for large tenants."
                ),
                required_views=[ViewType.ALERT, ViewType.FILE, ViewType.TESTS],
                expected_decision=DecisionType.BUG,
                expected_severity=SeverityLevel.MEDIUM,
                sla_deadline_step=15,
                remediation_hint=(
                    "Replace nested scan with hash-join style merge keyed by policy id."
                ),
            ),
        ],
    )


def load_tasks() -> Dict[str, TaskDefinition]:
    tasks: List[TaskDefinition] = [_easy_task(), _medium_task(), _hard_task()]
    return {task.task_id: task for task in tasks}


def ordered_task_ids() -> List[str]:
    return [
        "easy-pr-login-hotfix",
        "medium-pr-billing-worker",
        "hard-release-platform-gateway",
    ]
