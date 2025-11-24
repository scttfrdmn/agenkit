# Prometheus Monitoring for Agenkit

This directory contains Prometheus alert rules and SLO definitions for monitoring Agenkit in production.

## Table of Contents

- [Overview](#overview)
- [SLO Definitions](#slo-definitions)
- [Alert Rules](#alert-rules)
- [Configuration](#configuration)
- [Error Budget Management](#error-budget-management)
- [Runbooks](#runbooks)

## Overview

Agenkit uses Prometheus for metrics collection and alerting. This monitoring configuration implements:

1. **Service Level Objectives (SLOs)** - Targets for availability, latency, and error rates
2. **Alert Rules** - Notifications when SLOs are at risk or violated
3. **Recording Rules** - Pre-computed metrics for efficient querying and alerting
4. **Error Budget Tracking** - Monitoring of error budget consumption

## SLO Definitions

### Availability SLO

**Target**: 99.9% (3 nines)
- **Error Budget**: 0.1% (43.2 minutes downtime per month)
- **Measurement**: Ratio of successful requests to total requests
- **Window**: Rolling 30-day window

```
Success Rate = successful_requests / total_requests ≥ 99.9%
```

### Latency SLO

**Target**: P95 latency < 1000ms
- **Measurement**: 95th percentile request latency
- **Window**: Rolling 5-minute window

```
P95(request_latency) < 1000ms
```

### Error Rate SLO

**Target**: < 0.1% error rate
- **Measurement**: Ratio of failed requests to total requests
- **Window**: Rolling 5-minute window

```
Error Rate = error_requests / total_requests < 0.1%
```

## Alert Rules

### Service Health Alerts

#### HighErrorRate
- **Severity**: Warning
- **Threshold**: >1% error rate over 5 minutes
- **For**: 5 minutes
- **Description**: Indicates elevated error rates that may impact SLO compliance

#### CriticalErrorRate
- **Severity**: Critical
- **Threshold**: >5% error rate over 5 minutes
- **For**: 2 minutes
- **Description**: Severe error rate that requires immediate attention

#### HighLatency
- **Severity**: Warning
- **Threshold**: P95 > 1000ms over 5 minutes
- **For**: 5 minutes
- **Description**: Latency approaching or exceeding SLO target

#### CriticalLatency
- **Severity**: Critical
- **Threshold**: P95 > 5000ms over 5 minutes
- **For**: 2 minutes
- **Description**: Extremely high latency affecting user experience

#### LowSuccessRate
- **Severity**: Warning
- **Threshold**: <99% success rate over 5 minutes
- **For**: 5 minutes
- **Description**: Success rate below target, error budget at risk

#### CriticalSuccessRate
- **Severity**: Critical
- **Threshold**: <95% success rate over 5 minutes
- **For**: 2 minutes
- **Description**: Critical service degradation

### Resource Exhaustion Alerts

#### HighMemoryUsage
- **Severity**: Warning
- **Threshold**: >90% memory utilization
- **For**: 5 minutes
- **Description**: Memory pressure may lead to OOM errors

#### CriticalMemoryUsage
- **Severity**: Critical
- **Threshold**: >95% memory utilization
- **For**: 2 minutes
- **Description**: Imminent OOM risk, immediate action required

#### HighGoroutineCount
- **Severity**: Warning
- **Threshold**: >10,000 goroutines
- **For**: 10 minutes
- **Description**: Potential goroutine leak

#### RapidGoroutineGrowth
- **Severity**: Warning
- **Threshold**: >100 goroutines/second growth
- **For**: 5 minutes
- **Description**: Abnormal goroutine creation rate

### SLO Burn Rate Alerts

Based on [Google SRE Workbook](https://sre.google/workbook/alerting-on-slos/) multi-window, multi-burn-rate methodology.

#### ErrorBudgetFastBurn
- **Severity**: Critical
- **Threshold**: 14.4x normal burn rate (consuming 2% of monthly budget per hour)
- **For**: 2 minutes
- **Description**: Rapid error budget consumption - will exhaust 99.9% SLO in ~2 days at current rate

#### ErrorBudgetSlowBurn
- **Severity**: Warning
- **Threshold**: 3x normal burn rate (consuming 5% of monthly budget per day)
- **For**: 15 minutes
- **Description**: Sustained error budget consumption - will exhaust 99.9% SLO in ~20 days at current rate

## Configuration

### Prometheus Configuration

Add these files to your Prometheus configuration:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - 'alerts.yml'
  - 'recording_rules.yml'

scrape_configs:
  - job_name: 'agenkit'
    static_configs:
      - targets: ['localhost:8000']  # Adjust to your metrics endpoint
```

### Loading Rules

1. Copy `alerts.yml` and `recording_rules.yml` to your Prometheus rules directory
2. Reload Prometheus configuration:
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```
3. Verify rules loaded successfully:
   ```bash
   curl http://localhost:9090/api/v1/rules
   ```

### Alertmanager Configuration

Configure Alertmanager to route alerts based on severity:

```yaml
# alertmanager.yml
route:
  receiver: 'default'
  group_by: ['alertname', 'agent_name']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      repeat_interval: 5m
    - match:
        severity: warning
      receiver: 'slack'
      repeat_interval: 4h

receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<your-pagerduty-key>'
  - name: 'slack'
    slack_configs:
      - api_url: '<your-slack-webhook>'
        channel: '#agenkit-alerts'
  - name: 'default'
    slack_configs:
      - api_url: '<your-slack-webhook>'
        channel: '#agenkit-monitoring'
```

## Error Budget Management

### Viewing Error Budget

Query current error budget status:

```promql
# Remaining error budget (%)
agenkit:error_budget:availability:remaining_ratio * 100

# Current burn rate (1h window)
agenkit:error_budget:availability:burn_rate:1h

# Current burn rate (6h window)
agenkit:error_budget:availability:burn_rate:6h
```

### Interpreting Burn Rates

- **Burn Rate = 1.0**: Normal consumption (will last exactly 30 days)
- **Burn Rate > 1.0**: Burning faster than expected
- **Burn Rate < 1.0**: Burning slower than expected (good!)

**Example**: A burn rate of 14.4 means you're consuming error budget 14.4x faster than normal:
- At this rate, 30-day error budget will be exhausted in ~2 days
- This triggers the `ErrorBudgetFastBurn` critical alert

### Error Budget Policy

When error budget is exhausted or at risk:

1. **Stop feature releases** - Focus on reliability improvements
2. **Root cause analysis** - Investigate incidents consuming budget
3. **Reliability sprint** - Dedicate engineering time to stability
4. **Resume features** - Only after budget recovers above threshold (e.g., 10%)

## Runbooks

Alert annotations include runbook URLs for troubleshooting guidance:

- **High Error Rate**: https://github.com/scttfrdmn/agenkit/wiki/runbooks/high-error-rate
- **High Latency**: https://github.com/scttfrdmn/agenkit/wiki/runbooks/high-latency
- **Low Success Rate**: https://github.com/scttfrdmn/agenkit/wiki/runbooks/low-success-rate
- **High Memory Usage**: https://github.com/scttfrdmn/agenkit/wiki/runbooks/high-memory-usage
- **Goroutine Leak**: https://github.com/scttfrdmn/agenkit/wiki/runbooks/goroutine-leak
- **Error Budget Burn**: https://github.com/scttfrdmn/agenkit/wiki/runbooks/error-budget-burn

### Creating Runbooks

Each runbook should include:

1. **Alert Description** - What the alert means
2. **Impact** - How it affects users and SLOs
3. **Diagnosis** - How to investigate the issue
4. **Remediation** - Steps to resolve the problem
5. **Prevention** - How to prevent recurrence

## Dashboards

Recommended Grafana dashboards:

1. **SLO Dashboard** - Track SLO compliance and error budget
2. **Service Health** - Request rates, latency, errors
3. **Resource Utilization** - Memory, goroutines, GC metrics
4. **Agent Performance** - Per-agent metrics and comparisons

Example queries for dashboards:

```promql
# Availability over time
agenkit:slo:availability:ratio

# P95 latency by agent
agenkit:latency:p95:by_agent

# Error budget remaining
agenkit:error_budget:availability:remaining_ratio * 100

# Request rate by status
sum by (status) (agenkit:requests:rate5m)
```

## Testing Alerts

Verify alert rules are working:

```bash
# Check rule syntax
promtool check rules alerts.yml
promtool check rules recording_rules.yml

# Test alert evaluation
promtool test rules test_rules.yml
```

## References

- [Google SRE Book - SLIs, SLOs, and SLAs](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Workbook - Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)

## Support

For questions or issues with monitoring:

- GitHub Issues: https://github.com/scttfrdmn/agenkit/issues
- Documentation: https://github.com/scttfrdmn/agenkit/wiki
