# A/B Testing Framework Guide

## Overview

The A/B Testing framework provides statistical significance testing for comparing agent variants. Use it to make data-driven decisions when evaluating different prompts, models, or agent configurations.

## Quick Start

### Python

```python
from agenkit.evaluation import ABTest, SignificanceLevel

# Create test
ab_test = ABTest(
    name="my_experiment",
    control_agent=baseline_agent,
    treatment_agent=new_agent,
    metrics=["accuracy"]
)

# Run experiment
test_cases = [
    {"input": "Question 1", "expected": "Answer 1"},
    {"input": "Question 2", "expected": "Answer 2"},
]

results = await ab_test.run(test_cases, sample_size=50)

# Check results
if results["accuracy"].is_significant:
    print(f"Winner: {results['accuracy'].winner}")
    print(f"Improvement: {results['accuracy'].improvement_percent:.1f}%")
```

### Go

```go
import "github.com/scttfrdmn/agenkit-go/evaluation"

// Create test
abTest := evaluation.NewABTest(
    "my_experiment",
    controlAgent,
    treatmentAgent,
    []string{"accuracy"},
    evaluation.SignificanceLevelP005,
    evaluation.StatisticalTestTypeTTest,
)

// Run experiment
testCases := []map[string]interface{}{
    {"input": "Question 1", "expected": "Answer 1"},
    {"input": "Question 2", "expected": "Answer 2"},
}

results, err := abTest.Run(testCases, 50, true)

// Check results
if results["accuracy"].IsSignificant() {
    fmt.Printf("Winner: %s\n", results["accuracy"].Winner())
}
```

## Core Concepts

### Variants

- **Control**: Baseline agent (existing implementation)
- **Treatment**: New agent variant to test

### Metrics

Built-in metrics automatically tracked:
- `accuracy` - Correctness of responses
- `latency_ms` - Response time in milliseconds

Custom metrics can be added by implementing the measurement interface.

### Statistical Tests

#### T-Test (Parametric)
- **Use when**: Data is normally distributed, sample size >30
- **Assumptions**: Normal distribution, equal variances
- **Effect size**: Cohen's d

```python
ab_test = ABTest(
    ...,
    test_type=StatisticalTestType.T_TEST
)
```

#### Mann-Whitney U (Non-Parametric)
- **Use when**: Non-normal distributions, small samples, ordinal data
- **Assumptions**: None (distribution-free)
- **Effect size**: Rank-biserial correlation

```python
ab_test = ABTest(
    ...,
    test_type=StatisticalTestType.MANN_WHITNEY
)
```

### Significance Levels

Choose confidence level based on risk tolerance:

| Level | P-Value | Confidence | Use Case |
|-------|---------|------------|----------|
| P_0_001 | 0.001 | 99.9% | Critical systems |
| P_0_01 | 0.01 | 99% | High-stakes decisions |
| P_0_05 | 0.05 | 95% | Standard (default) |
| P_0_10 | 0.10 | 90% | Exploratory research |

```python
ab_test = ABTest(
    ...,
    significance_level=SignificanceLevel.P_0_01
)
```

## Sample Size Calculation

Calculate required sample size before running experiments:

```python
from agenkit.evaluation import calculate_sample_size

n = calculate_sample_size(
    baseline_mean=0.80,           # Expected control accuracy
    minimum_detectable_effect=0.05,  # Want to detect 5% improvement
    alpha=0.05,                   # 95% confidence
    power=0.80,                   # 80% power
    std_dev=0.15                  # Estimated std deviation
)

print(f"Need {n} samples per variant")
```

**Key Parameters:**
- `baseline_mean`: Expected mean of control group
- `minimum_detectable_effect`: Smallest improvement to detect (absolute)
- `alpha`: Significance level (Type I error rate)
- `power`: Statistical power (1 - Type II error rate)
- `std_dev`: Estimated standard deviation (optional)

**Rules of Thumb:**
- Smaller effects require larger samples
- Higher power requires larger samples
- More variance requires larger samples

## Interpreting Results

### ABResult Object

```python
result = results["accuracy"]

# Statistical significance
print(result.is_significant)  # True/False
print(result.p_value)         # e.g., 0.0234

# Effect size
print(result.effect_size)     # Cohen's d or rank-biserial

# Confidence interval
print(result.confidence_interval)  # (lower, upper)

# Winner
print(result.winner)          # "control" or "treatment" (if significant)
print(result.improvement_percent)  # % improvement
```

### Effect Size Interpretation (Cohen's d)

| Cohen's d | Interpretation |
|-----------|---------------|
| 0.2 | Small effect |
| 0.5 | Medium effect |
| 0.8 | Large effect |
| >1.0 | Very large effect |

### Decision Framework

```python
if result.is_significant:
    if result.winner == "treatment":
        if result.effect_size >= 0.5:
            print("✅ Strong evidence to adopt treatment")
        else:
            print("⚠️ Significant but small effect - consider practical impact")
    else:
        print("❌ Control performs better - don't adopt treatment")
else:
    print("❓ No significant difference - need more data or accept equality")
```

## Multi-Metric Comparison

Compare multiple metrics simultaneously:

```python
ab_test = ABTest(
    ...,
    metrics=["accuracy", "latency_ms"]
)

results = await ab_test.run(test_cases, sample_size=50)

# Analyze trade-offs
acc_result = results["accuracy"]
lat_result = results["latency_ms"]

if acc_result.is_significant and acc_result.winner == "treatment":
    improvement = acc_result.improvement_percent
    if lat_result.is_significant and lat_result.winner == "control":
        slowdown = lat_result.improvement_percent
        print(f"Treatment is {improvement:.1f}% more accurate")
        print(f"But {abs(slowdown):.1f}% slower")
        print("Consider use case requirements for final decision")
```

## Best Practices

### 1. Pre-Register Your Experiment

Define before running:
- Metrics to track
- Minimum sample size
- Significance level
- Stopping criteria

### 2. Use Appropriate Sample Sizes

```python
# Calculate needed sample size first
n = calculate_sample_size(
    baseline_mean=current_accuracy,
    minimum_detectable_effect=0.03,  # 3% improvement
    power=0.80
)

# Then run experiment with sufficient samples
results = await ab_test.run(test_cases, sample_size=n)
```

### 3. Choose Test Type Appropriately

```python
# Use t-test for normal distributions
if large_sample_size and normal_distribution:
    test_type = StatisticalTestType.T_TEST

# Use Mann-Whitney for non-normal or small samples
else:
    test_type = StatisticalTestType.MANN_WHITNEY
```

### 4. Avoid P-Hacking

❌ **Don't:**
- Test multiple times and stop when significant
- Change significance level after seeing results
- Add more samples only when result is not significant

✅ **Do:**
- Set sample size before experiment
- Use single significance level throughout
- Report all metrics tested

### 5. Consider Practical Significance

```python
if result.is_significant:
    # Also check if improvement is meaningful
    if abs(result.improvement_percent) >= 5.0:  # At least 5% improvement
        print("Both statistically and practically significant")
    else:
        print("Statistically significant but small practical impact")
```

## Advanced Usage

### Custom Evaluation Logic

Override the default evaluation to use custom scoring:

```python
class CustomABTest(ABTest):
    async def _evaluate_variant(self, variant, test_cases):
        results = []
        for test_case in test_cases:
            # Custom evaluation logic
            response = await variant.agent.process(...)
            score = self.custom_scoring_function(response, test_case)
            results.append({"accuracy": score, "latency_ms": latency})
        return results
```

### Bootstrap Confidence Intervals

For non-parametric tests, bootstrap confidence intervals are automatically calculated:

```python
ab_test = ABTest(
    ...,
    test_type=StatisticalTestType.MANN_WHITNEY
)

result = await ab_test.run(test_cases, sample_size=50)

# Bootstrap CI automatically computed
print(result.confidence_interval)  # Based on 1000 bootstrap samples
```

### Experiment Summary

Get complete experiment summary as JSON:

```python
summary = ab_test.get_summary()

# Contains:
# - Experiment name
# - Variant names
# - All metrics tested
# - Full results for each metric
# - Winners and improvement percentages

import json
print(json.dumps(summary, indent=2))
```

## Common Pitfalls

### 1. Insufficient Sample Size

**Problem:** Running experiment with too few samples leads to false negatives.

**Solution:** Always calculate required sample size first:
```python
n = calculate_sample_size(baseline_mean=0.8, minimum_detectable_effect=0.05)
```

### 2. Multiple Comparison Problem

**Problem:** Testing many metrics increases false positive rate.

**Solution:** Apply Bonferroni correction or focus on primary metric:
```python
# Adjust significance level for multiple tests
adjusted_alpha = 0.05 / num_metrics
```

### 3. Peeking at Results

**Problem:** Repeatedly checking results and stopping when significant inflates p-values.

**Solution:** Set sample size upfront and run to completion:
```python
# Pre-register sample size
n = calculate_sample_size(...)

# Run to completion
results = await ab_test.run(test_cases, sample_size=n)
```

### 4. Ignoring Assumptions

**Problem:** Using t-test on non-normal data gives invalid results.

**Solution:** Check distribution or use non-parametric test:
```python
# For non-normal distributions
ab_test = ABTest(..., test_type=StatisticalTestType.MANN_WHITNEY)
```

## Examples

See `examples/evaluation/ab_testing_demo.py` for complete working examples:

1. Basic A/B test with statistical significance
2. Multi-metric comparison (accuracy vs latency)
3. Sample size calculation
4. Non-parametric testing
5. Complete experiment workflow

Run the demo:
```bash
python examples/evaluation/ab_testing_demo.py
```

## API Reference

### Classes

- **ABTest**: Main experiment orchestrator
  - `__init__(name, control_agent, treatment_agent, metrics, significance_level, test_type)`
  - `run(test_cases, sample_size, shuffle)` → Dict[str, ABResult]
  - `get_summary()` → Dict[str, Any]

- **ABVariant**: Test variant representation
  - `name`: Variant name
  - `agent`: Agent instance
  - `samples`: List of measurements
  - `mean`: Mean of samples
  - `std`: Standard deviation
  - `sample_size`: Number of samples

- **ABResult**: Statistical results
  - `is_significant`: Whether result is significant
  - `winner`: Winning variant name (if significant)
  - `p_value`: Statistical p-value
  - `effect_size`: Effect size (Cohen's d or rank-biserial)
  - `confidence_interval`: (lower, upper) bounds
  - `improvement_percent`: % improvement of treatment over control

### Functions

- **calculate_sample_size(baseline_mean, minimum_detectable_effect, alpha, power, std_dev)**
  - Returns required sample size per variant

### Enums

- **SignificanceLevel**: P_0_001, P_0_01, P_0_05, P_0_10
- **StatisticalTestType**: T_TEST, MANN_WHITNEY, CHI_SQUARE, BOOTSTRAP

## Further Reading

- [Statistical Power Analysis](https://en.wikipedia.org/wiki/Power_of_a_test)
- [Cohen's d Effect Size](https://en.wikipedia.org/wiki/Effect_size#Cohen's_d)
- [Mann-Whitney U Test](https://en.wikipedia.org/wiki/Mann%E2%80%93Whitney_U_test)
- [Multiple Comparisons Problem](https://en.wikipedia.org/wiki/Multiple_comparisons_problem)
