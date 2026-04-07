from __future__ import annotations

from typing import Optional

from .models import RewardBreakdown


def compute_step_reward(
    *,
    step_count: int,
    max_steps: int,
    action_valid: bool,
    is_loop: bool,
    is_noop: bool,
    progress_before: float,
    progress_after: float,
    triage_signal: float,
    submitted: bool,
    final_score: Optional[float],
) -> RewardBreakdown:
    """Deterministic dense reward with penalties for poor behavior."""

    step_tax = -0.01
    validity = 0.02 if action_valid else -0.20
    novelty = 0.03 if action_valid and (not is_loop) and (not is_noop) else 0.0

    delta = max(-1.0, min(1.0, progress_after - progress_before))
    progress = 0.60 * delta

    triage = max(-0.25, min(0.25, triage_signal))

    completion = 0.0
    if submitted:
        completion = 0.45 * float(final_score or 0.0)

    loop_penalty = -0.08 if is_loop else 0.0
    noop_penalty = -0.05 if is_noop else 0.0

    # Extra soft pressure to finish near max steps without over-penalizing exploration.
    tempo_penalty = 0.0
    if max_steps > 0 and step_count > int(0.9 * max_steps):
        tempo_penalty = -0.03

    total = (
        step_tax
        + validity
        + novelty
        + progress
        + triage
        + completion
        + loop_penalty
        + noop_penalty
        + tempo_penalty
    )

    total = max(-1.0, min(1.0, total))

    return RewardBreakdown(
        step_tax=step_tax,
        validity=validity,
        novelty=novelty,
        triage=triage,
        progress=progress,
        completion=completion,
        loop_penalty=loop_penalty + tempo_penalty,
        noop_penalty=noop_penalty,
        total=total,
    )
