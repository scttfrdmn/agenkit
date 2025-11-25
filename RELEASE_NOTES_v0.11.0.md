# Release Notes - v0.11.0

**Release Date:** TBD
**Previous Version:** v0.10.1

## Overview

Version 0.11.0 completes the **Evaluation Framework** with the addition of a comprehensive **A/B Testing framework** for statistical comparison of agent variants. This release enables data-driven decision-making when comparing different agent implementations, prompts, models, or configurations.

## What's New

### 🧪 A/B Testing Framework

A complete statistical A/B testing system for comparing agent performance with proper significance testing and confidence intervals.

**Key Features:**

- **Statistical Tests:**
  - Independent samples t-test (parametric)
  - Mann-Whitney U test (non-parametric)
  - Chi-square test (categorical data)
  - Bootstrap methods (distribution-free)

- **Effect Size Calculations:**
  - Cohen's d for t-tests
  - Rank-biserial correlation for Mann-Whitney
  - Confidence intervals for all tests

- **Sample Size Calculation:**
  - Power analysis to determine required sample sizes
  - Configurable significance levels (0.001, 0.01, 0.05, 0.10)
  - Adjustable statistical power (default 80%)

- **Experiment Orchestration:**
  - Automated test case distribution
  - Parallel variant evaluation
  - Comprehensive result reporting
  - JSON-serializable results

**Python API:**

```python
from agenkit.evaluation import ABTest, SignificanceLevel, StatisticalTestType

# Create A/B test
ab_test = ABTest(
    name="prompt_optimization",
    control_agent=baseline_agent,
    treatment_agent=optimized_agent,
    metrics=["accuracy", "latency_ms"],
    significance_level=SignificanceLevel.P_0_05,
    test_type=StatisticalTestType.T_TEST
)

# Run experiment
results = await ab_test.run(test_cases, sample_size=100)

# Check significance
if results["accuracy"].is_significant:
    print(f"Winner: {results['accuracy'].winner}")
    print(f"Improvement: {results['accuracy'].improvement_percent:.1f}%")
```

**Go API:**

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/evaluation"

// Create A/B test
abTest := evaluation.NewABTest(
    "prompt_optimization",
    controlAgent,
    treatmentAgent,
    []string{"accuracy", "latency_ms"},
    evaluation.SignificanceLevelP005,
    evaluation.StatisticalTestTypeTTest,
)

// Run experiment
results, err := abTest.Run(testCases, 100, true)

// Check significance
if results["accuracy"].IsSignificant() {
    fmt.Printf("Winner: %s\n", results["accuracy"].Winner())
}
```

### 📊 New Classes and Functions

**Python:**
- `ABTest` - Main A/B testing orchestrator
- `ABVariant` - Represents a test variant (control/treatment)
- `ABResult` - Experiment results with statistical analysis
- `SignificanceLevel` - Enum for significance thresholds
- `StatisticalTestType` - Enum for test type selection
- `calculate_sample_size()` - Power analysis for sample sizing

**Go:**
- `ABTest` - Main A/B testing orchestrator
- `ABVariant` - Test variant representation
- `ABResult` - Statistical results
- `SignificanceLevel` - Significance threshold enum
- `StatisticalTestType` - Test type enum
- `CalculateSampleSize()` - Sample size calculator

### 📚 Examples and Documentation

**New Examples:**
- `examples/evaluation/ab_testing_demo.py` - 5 interactive demonstrations:
  1. Basic A/B testing with statistical significance
  2. Multi-metric comparison (accuracy vs latency trade-offs)
  3. Sample size calculation with power analysis
  4. Non-parametric testing with Mann-Whitney U
  5. Complete experiment workflow with summary

**Test Coverage:**
- 24 comprehensive tests in Python (`tests/evaluation/test_ab_testing.py`)
- 11 example tests in Go (`agenkit-go/evaluation/example_test.go`)

## Dependencies

### Python
- **Added:** `scipy>=1.11.0` for statistical functions

### Go
- **Added:** `gonum.org/v1/gonum v0.16.0` for statistical functions

## Breaking Changes

None. This is a backwards-compatible feature addition.

## Bug Fixes

- Fixed pytest hanging issue in `tests/conftest.py` by adding proper timeouts to async cleanup
- Fixed deprecated `datetime.utcnow()` usage in evaluation modules
- Resolved Go duplicate function declarations in evaluation package

## Evaluation Framework Status

The Evaluation Framework is now **95% complete** with the following components:

✅ **Implemented:**
- Core evaluation infrastructure (`Evaluator`, `Metric`, `EvaluationResult`)
- Session recording and replay (`SessionRecorder`, `SessionReplay`)
- Regression detection (`RegressionDetector`)
- Context tracking (`ContextMetrics`, `CompressionMetrics`)
- Quality metrics (`AccuracyMetric`, `PrecisionRecallMetric`, `QualityMetrics`)
- Latency tracking (`LatencyMetric`)
- Benchmark suites (`Benchmark`, `BenchmarkSuite`)
- **A/B testing framework** ← New in v0.11.0

📋 **Remaining (Phase 10 - Future):**
- Automated optimization (Bayesian optimization, AutoML integration)

## Migration Guide

No migration required. The A/B testing framework is a new addition that doesn't affect existing code.

To start using A/B testing:

1. Install/update dependencies:
   ```bash
   # Python
   pip install agenkit>=0.11.0

   # Go
   go get github.com/scttfrdmn/agenkit/agenkit-go@v0.11.0
   ```

2. Import the new classes:
   ```python
   from agenkit.evaluation import ABTest, calculate_sample_size
   ```

3. Run the demo:
   ```bash
   python examples/evaluation/ab_testing_demo.py
   ```

## Performance

- A/B tests run efficiently with parallel variant evaluation
- Statistical calculations are optimized using scipy (Python) and gonum (Go)
- Typical experiment with 100 samples per variant completes in <5 seconds

## Testing

All tests pass successfully:
- Python: 88 evaluation tests (including 24 A/B testing tests)
- Go: 11 example tests + comprehensive unit tests

## Known Issues

None.

## Contributors

- Scott Friedman (@scttfrdmn)

## Next Steps

**Phase 10 - Automated Optimization (Future):**
- Bayesian optimization for hyperparameter tuning
- AutoML integration for model selection
- Automated prompt optimization
- Multi-objective optimization

---

For detailed API documentation, see the inline documentation in:
- `agenkit/evaluation/ab_testing.py`
- `agenkit-go/evaluation/ab_testing.go`

For usage examples, run:
```bash
python examples/evaluation/ab_testing_demo.py
```
