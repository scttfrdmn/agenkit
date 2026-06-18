# Error Metrics (p_a, P_error)

Agenkit can export the two core agent-failure-rate quantities via OpenTelemetry
so you can chart and alert on them (e.g. in Prometheus + Grafana):

| Metric | Meaning |
|--------|---------|
| `agenkit.agent.per_step_error_rate` | **p_a** — per-step error rate, `failed_steps / total_steps` |
| `agenkit.agent.cumulative_failure_probability` | **P_error** — probability of ≥1 failure across `n` steps, `1 - (1 - p_a)^n` |

Both are recorded as **histograms**. The OTel→Prometheus exporter renames the
metric (dots → underscores) and adds `_sum` / `_count` / `_bucket` series, so in
PromQL they appear as `agenkit_agent_per_step_error_rate_*` and
`agenkit_agent_cumulative_failure_probability_*`.

## Recording the metrics

The values come from an [`ErrorTracker`](../agenkit/evaluation/error_tracker.py);
[`ErrorMetrics`](../agenkit/observability/error_metrics.py) records them to OTel.

```python
from agenkit.evaluation import ErrorTracker
from agenkit.observability import ErrorMetrics, init_metrics

init_metrics()  # sets up the meter provider / Prometheus exporter

tracker = ErrorTracker(enabled=True)
# ... record each step as the agent runs ...
tracker.record_step(True)
tracker.record_step(False, error="timeout")

metrics = ErrorMetrics()
# Emit once per run (typically after the run completes). Project the
# compounding over a planned horizon with steps=N; attach attributes for
# per-agent breakdowns.
metrics.record(tracker, steps=100, attributes={"agent": "researcher"})
```

> Once `enable_error_tracking` is wired into agent execution
> ([#653](https://github.com/scttfrdmn/agenkit/issues/653)), this recording
> happens automatically at the end of a tracked run.

## Prometheus queries

```promql
# Average per-step error rate over the last 24h
  avg_over_time(agenkit_agent_per_step_error_rate_sum[24h])
/ avg_over_time(agenkit_agent_per_step_error_rate_count[24h])

# 95th-percentile cumulative failure probability over 24h
histogram_quantile(
  0.95,
  rate(agenkit_agent_cumulative_failure_probability_bucket[24h])
)

# Per-agent average per-step error rate (uses the `agent` attribute)
  sum by (agent) (rate(agenkit_agent_per_step_error_rate_sum[1h]))
/ sum by (agent) (rate(agenkit_agent_per_step_error_rate_count[1h]))
```

## Grafana

- **Per-step error rate (p_a)** — time series of the average query above; a
  small p_a compounds, so trend matters more than the absolute value.
- **Cumulative failure probability (P_error)** — the p95 `histogram_quantile`
  query; a stat panel with thresholds (e.g. green < 0.3, amber < 0.6, red ≥ 0.6)
  surfaces runs likely to fail.
- **Per-agent breakdown** — table panel grouped by the `agent` attribute.

Alerting rule example (fire when projected failure probability is high):

```yaml
- alert: HighCumulativeFailureProbability
  expr: histogram_quantile(0.95, rate(agenkit_agent_cumulative_failure_probability_bucket[1h])) > 0.6
  for: 15m
  labels: { severity: warning }
  annotations:
    summary: "Agent runs have a >60% projected failure probability (p95)"
```
