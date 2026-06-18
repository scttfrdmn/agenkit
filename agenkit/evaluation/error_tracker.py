"""
Error tracking infrastructure — per-step error rate and failure compounding.

Long-running agents execute many steps; even a small per-step error rate
compounds into a high probability of at least one failure over a long run.
``ErrorTracker`` records the outcome of each step and exposes the two core
quantities from the agent-failure-rate analysis:

- ``p_a`` (:meth:`ErrorTracker.per_step_error_rate`) — the per-step error rate,
  ``failed_steps / total_steps``.
- ``P_error`` (:meth:`ErrorTracker.cumulative_failure_probability`) — the
  probability of at least one failure across ``n`` independent steps,
  ``1 - (1 - p_a) ** n``. With no argument, ``n`` is the number of recorded
  steps (observed cumulative failure probability); pass ``steps=N`` to project
  the compounding over a planned run of ``N`` steps.

Tracking is opt-in: construct an ``ErrorTracker(enabled=True)`` (or pass
``enable_error_tracking=True`` to a component that owns one) and call
:meth:`record_step` as steps complete. When disabled, ``record_step`` is a
no-op and the metrics report zero, so the tracker is cheap to leave wired in.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StepResult:
    """Outcome of a single agent step.

    Attributes:
        success: Whether the step completed without error.
        name: Optional step label (useful for per-step breakdowns later).
        error: Optional error description when ``success`` is ``False``.
    """

    success: bool
    name: str | None = None
    error: str | None = None


@dataclass
class ErrorTracker:
    """Records step outcomes and computes error-rate / compounding metrics.

    Args:
        enabled: When ``False`` (the default), :meth:`record_step` is a no-op
            and all metrics report ``0.0``/``0`` — tracking is strictly opt-in.

    Example:
        >>> tracker = ErrorTracker(enabled=True)
        >>> tracker.record_step(True)
        >>> tracker.record_step(False, error="timeout")
        >>> tracker.per_step_error_rate()
        0.5
        >>> round(tracker.cumulative_failure_probability(steps=10), 4)
        0.999
    """

    enabled: bool = False
    step_results: list[StepResult] = field(default_factory=list)

    def record_step(
        self, success: bool, *, name: str | None = None, error: str | None = None
    ) -> None:
        """Record the outcome of one step (no-op when disabled).

        Args:
            success: Whether the step succeeded.
            name: Optional step label.
            error: Optional error description for a failed step.
        """
        if not self.enabled:
            return
        self.step_results.append(StepResult(success=success, name=name, error=error))

    @property
    def total_steps(self) -> int:
        """Number of recorded steps."""
        return len(self.step_results)

    @property
    def failed_steps(self) -> int:
        """Number of recorded steps that failed."""
        return sum(1 for r in self.step_results if not r.success)

    def per_step_error_rate(self) -> float:
        """Per-step error rate ``p_a`` = failed_steps / total_steps.

        Returns ``0.0`` when no steps have been recorded.
        """
        if self.total_steps == 0:
            return 0.0
        return self.failed_steps / self.total_steps

    def cumulative_failure_probability(self, steps: int | None = None) -> float:
        """Probability of at least one failure over ``steps`` steps.

        ``P_error = 1 - (1 - p_a) ** n`` where ``n`` is ``steps`` if given,
        otherwise the number of recorded steps. Models error compounding:
        independent steps each succeed with probability ``1 - p_a``, so the run
        succeeds only if all ``n`` succeed.

        Args:
            steps: Project the compounding over this many steps. Defaults to the
                number of recorded steps (observed cumulative probability).

        Returns:
            A probability in ``[0.0, 1.0]``. Returns ``0.0`` if ``p_a`` is 0 or
            ``n <= 0``.
        """
        n = self.total_steps if steps is None else steps
        if n <= 0:
            return 0.0
        p_a = self.per_step_error_rate()
        return 1.0 - (1.0 - p_a) ** n

    def reset(self) -> None:
        """Clear all recorded step results."""
        self.step_results.clear()
