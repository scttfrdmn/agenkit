"""
OpenTelemetry metrics for error tracking — per-step error rate and compounding.

Bridges :class:`agenkit.evaluation.ErrorTracker` to OpenTelemetry so the two
core failure-rate quantities can be exported (e.g. to Prometheus) and alerted
on:

- ``agenkit.agent.per_step_error_rate`` — histogram of ``p_a``
  (``failed_steps / total_steps``).
- ``agenkit.agent.cumulative_failure_probability`` — histogram of ``P_error``
  (``1 - (1 - p_a) ** n``).

Both are recorded by :meth:`ErrorMetrics.record`, which reads the values
straight off an ``ErrorTracker``. Recording is decoupled from the agent step
loop on purpose: callers (or, once wired, the agent's
``enable_error_tracking`` path) decide when to emit — typically once per run
after the tracker has observed all steps.

Example Prometheus queries (also in docs/ERROR_METRICS.md)::

    # Average per-step error rate over the last day
    avg_over_time(agenkit_agent_per_step_error_rate_sum[24h])
      / avg_over_time(agenkit_agent_per_step_error_rate_count[24h])

    # 95th-percentile cumulative failure probability
    histogram_quantile(
        0.95,
        rate(agenkit_agent_cumulative_failure_probability_bucket[24h]),
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .metrics import get_meter

if TYPE_CHECKING:
    from agenkit.evaluation import ErrorTracker

PER_STEP_ERROR_RATE_METRIC = "agenkit.agent.per_step_error_rate"
CUMULATIVE_FAILURE_PROBABILITY_METRIC = "agenkit.agent.cumulative_failure_probability"


class ErrorMetrics:
    """Records ErrorTracker quantities (``p_a``, ``P_error``) to OpenTelemetry.

    Creates the two histograms once on construction (from the current meter
    provider) and records to them on demand.

    Example:
        >>> from agenkit.evaluation import ErrorTracker
        >>> tracker = ErrorTracker(enabled=True)
        >>> tracker.record_step(True)
        >>> tracker.record_step(False, error="timeout")
        >>> metrics = ErrorMetrics()           # doctest: +SKIP
        >>> metrics.record(tracker)             # doctest: +SKIP
    """

    def __init__(self) -> None:
        meter = get_meter()
        self._per_step_error_rate = meter.create_histogram(
            name=PER_STEP_ERROR_RATE_METRIC,
            description="Per-step error rate (p_a) = failed_steps / total_steps",
            unit="1",
        )
        self._cumulative_failure_probability = meter.create_histogram(
            name=CUMULATIVE_FAILURE_PROBABILITY_METRIC,
            description="Cumulative failure probability (P_error) = 1 - (1 - p_a)^n",
            unit="1",
        )

    def record(
        self,
        tracker: ErrorTracker,
        *,
        steps: int | None = None,
        attributes: dict[str, str] | None = None,
    ) -> None:
        """Record ``tracker``'s current ``p_a`` and ``P_error`` to the histograms.

        Args:
            tracker: The :class:`ErrorTracker` to read values from.
            steps: Passed through to
                :meth:`ErrorTracker.cumulative_failure_probability` — project
                the compounding over this many steps (defaults to the recorded
                step count).
            attributes: Optional metric attributes (e.g. ``{"agent": name}``)
                applied to both recordings.
        """
        attrs = attributes or {}
        self._per_step_error_rate.record(tracker.per_step_error_rate(), attributes=attrs)
        self._cumulative_failure_probability.record(
            tracker.cumulative_failure_probability(steps=steps), attributes=attrs
        )
