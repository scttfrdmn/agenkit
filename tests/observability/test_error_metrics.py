"""Tests for ErrorMetrics — OTel export of ErrorTracker p_a / P_error (#322).

OpenTelemetry's meter provider is process-global and only the first
``set_meter_provider`` wins, so (like tests/observability/test_metrics.py) we
use a single module-scoped reader. To keep tests independent despite the shared
histograms, each test tags its recording with a unique ``case`` attribute and
asserts on the data point carrying that attribute.
"""

import pytest
from opentelemetry import metrics as otel_metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from agenkit.evaluation import ErrorTracker
from agenkit.observability.error_metrics import (
    CUMULATIVE_FAILURE_PROBABILITY_METRIC,
    PER_STEP_ERROR_RATE_METRIC,
    ErrorMetrics,
)


@pytest.fixture(scope="module")
def metric_reader():
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    otel_metrics.set_meter_provider(provider)
    return reader


def _data_point(reader, metric_name, case):
    """Return the data point for ``metric_name`` tagged with ``case=<case>``."""
    for resource_metric in reader.get_metrics_data().resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name != metric_name:
                    continue
                for dp in metric.data.data_points:
                    if dp.attributes.get("case") == case:
                        return dp
    return None


def _tracker_half():
    """1 fail of 2 -> p_a = 0.5."""
    t = ErrorTracker(enabled=True)
    t.record_step(True)
    t.record_step(False, error="timeout")
    return t


def test_records_both_histograms(metric_reader):
    ErrorMetrics().record(_tracker_half(), attributes={"case": "both"})
    assert _data_point(metric_reader, PER_STEP_ERROR_RATE_METRIC, "both") is not None
    assert _data_point(metric_reader, CUMULATIVE_FAILURE_PROBABILITY_METRIC, "both") is not None


def test_records_per_step_error_rate_value(metric_reader):
    ErrorMetrics().record(_tracker_half(), attributes={"case": "p_a"})
    dp = _data_point(metric_reader, PER_STEP_ERROR_RATE_METRIC, "p_a")
    assert dp is not None
    assert dp.count == 1
    assert dp.sum == pytest.approx(0.5)


def test_records_cumulative_observed(metric_reader):
    # observed n=2 -> 1 - 0.5^2 = 0.75
    ErrorMetrics().record(_tracker_half(), attributes={"case": "observed"})
    dp = _data_point(metric_reader, CUMULATIVE_FAILURE_PROBABILITY_METRIC, "observed")
    assert dp is not None
    assert dp.sum == pytest.approx(0.75)


def test_records_cumulative_projected_steps(metric_reader):
    ErrorMetrics().record(_tracker_half(), steps=10, attributes={"case": "projected"})
    dp = _data_point(metric_reader, CUMULATIVE_FAILURE_PROBABILITY_METRIC, "projected")
    assert dp is not None
    assert dp.sum == pytest.approx(1 - 0.5**10)


def test_zero_error_rate_records_zero(metric_reader):
    t = ErrorTracker(enabled=True)
    for _ in range(5):
        t.record_step(True)
    ErrorMetrics().record(t, attributes={"case": "zero"})
    p_a_dp = _data_point(metric_reader, PER_STEP_ERROR_RATE_METRIC, "zero")
    p_err_dp = _data_point(metric_reader, CUMULATIVE_FAILURE_PROBABILITY_METRIC, "zero")
    assert p_a_dp.sum == pytest.approx(0.0)
    assert p_err_dp.sum == pytest.approx(0.0)


def test_attributes_applied(metric_reader):
    ErrorMetrics().record(_tracker_half(), attributes={"case": "attrs", "agent": "agent-1"})
    dp = _data_point(metric_reader, PER_STEP_ERROR_RATE_METRIC, "attrs")
    assert dp is not None
    assert dp.attributes.get("agent") == "agent-1"


def test_metric_names_are_canonical():
    assert PER_STEP_ERROR_RATE_METRIC == "agenkit.agent.per_step_error_rate"
    assert CUMULATIVE_FAILURE_PROBABILITY_METRIC == "agenkit.agent.cumulative_failure_probability"
