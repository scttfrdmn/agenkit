# Agent Evaluation Framework

> **Status**: Production Ready
> **Python**: ✅ | **Go**: 🚧 Planned Q1 2026

## Overview

The Agenkit Evaluation Framework provides comprehensive testing and quality measurement for autonomous agents, with **special focus on extreme-scale context evaluation (1M-25M+ tokens)** for systems like **endless**.

### Why Evaluation?

**Problem**: How do you measure if your agent is performing well over time, especially at massive context lengths?

**Answer**: This framework provides:
- **Quality Metrics**: Accuracy, precision, recall, response quality
- **Context Tracking**: Monitor context length growth and compression
- **Extreme-Scale Testing**: Validate performance at 1M-25M tokens
- **Regression Detection**: Catch quality degradation before production
- **Session Replay**: A/B test agent versions with real interactions

## Quick Start

```python
from agenkit.evaluation import Evaluator, AccuracyMetric, BenchmarkSuite

# 1. Create evaluator with metrics
evaluator = Evaluator(agent=my_agent, metrics=[AccuracyMetric()])

# 2. Define test cases
test_cases = [
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "Capital of France?", "expected": "Paris"},
]

# 3. Run evaluation
results = await evaluator.evaluate(test_cases)
print(f"Accuracy: {results.accuracy:.2%}")
```

## Components

### 1. Core Evaluation

#### Evaluator

Orchestrates evaluation runs, collects metrics, and aggregates results.

```python
from agenkit.evaluation import Evaluator, AccuracyMetric, QualityMetrics

evaluator = Evaluator(agent=my_agent, metrics=[AccuracyMetric(), QualityMetrics()])

results = await evaluator.evaluate(test_cases)

# Access results
print(f"Accuracy: {results.accuracy:.2%}")
print(f"Passed: {results.passed_tests}/{results.total_tests}")
print(f"Latency: {results.avg_latency_ms:.2f}ms")
```

#### Metrics

Base class for all evaluation metrics:

```python
from agenkit.evaluation import Metric


class CustomMetric(Metric):
    @property
    def name(self) -> str:
        return "custom_metric"

    async def measure(self, agent, input_msg, output_msg, context) -> float:
        # Your measurement logic
        return score  # 0.0 to 1.0

    def aggregate(self, measurements: List[float]) -> Dict[str, float]:
        return {
            "mean": sum(measurements) / len(measurements),
            "min": min(measurements),
            "max": max(measurements),
        }
```

### 2. Quality Metrics

#### AccuracyMetric

Measures task correctness:

```python
from agenkit.evaluation import AccuracyMetric

metric = AccuracyMetric()

# String matching (case-insensitive by default)
score = await metric.measure(agent, input_msg, output_msg, context={"expected": "Paris"})
# Returns 1.0 if correct, 0.0 if incorrect


# Custom validator
def custom_validator(expected, actual):
    return len(actual) > 10


metric = AccuracyMetric(validator=custom_validator)
```

#### QualityMetrics

Comprehensive quality scoring across multiple dimensions:

```python
from agenkit.evaluation import QualityMetrics

metric = QualityMetrics(
    use_llm_judge=False,  # Rule-based by default
    weights={"relevance": 0.3, "completeness": 0.3, "coherence": 0.2, "accuracy": 0.2},
)

score = await metric.measure(agent, input_msg, output_msg)
# Returns 0.0 to 1.0 composite quality score
```

#### PrecisionRecallMetric

For classification tasks:

```python
from agenkit.evaluation import PrecisionRecallMetric

metric = PrecisionRecallMetric()

# For each classification
await metric.measure(
    agent, input_msg, output_msg, context={"true_label": True, "predicted_label": True}
)

# Get statistics
stats = metric.aggregate([])
print(f"Precision: {stats['precision']:.2f}")
print(f"Recall: {stats['recall']:.2f}")
print(f"F1 Score: {stats['f1_score']:.2f}")
```

### 3. Context Metrics (For Extreme Scale)

#### ContextMetrics

Track context length growth:

```python
from agenkit.evaluation.context_metrics import ContextMetrics

metric = ContextMetrics()

length = await metric.measure(agent, input_msg, output_msg)
# Returns current context length in tokens

# Aggregate over time
stats = metric.aggregate(measurements)
print(f"Growth rate: {stats['growth_rate']:.2f} tokens/interaction")
print(f"Max length: {stats['max']:.0f} tokens")
```

#### CompressionMetrics

**Critical for endless**: Measure compression quality at 1M-25M+ tokens:

```python
from agenkit.evaluation.context_metrics import CompressionMetrics

metric = CompressionMetrics(test_lengths=[1_000_000, 10_000_000, 25_000_000], needle_count=10)

# Test compression at multiple scales
stats = await metric.evaluate_at_lengths(
    agent, session_id="test", needle_content=["Fact 1", "Fact 2", ...]
)

for length, stat in stats.items():
    print(f"{length / 1e6}M tokens:")
    print(f"  Compression ratio: {stat.compression_ratio}x")
    print(f"  Retrieval accuracy: {stat.retrieval_accuracy:.2%}")
```

**Key metrics**:
- Compression ratio (e.g., 100x, 1000x)
- Retrieval accuracy after compression
- Quality degradation as context grows

### 4. Benchmark Suites

#### Pre-defined Suites

```python
from agenkit.evaluation import BenchmarkSuite

# Standard: Basic Q&A and small-scale retrieval
suite = BenchmarkSuite.standard()

# Extreme-scale: 1M, 10M, 25M tokens (for endless)
suite = BenchmarkSuite.extreme_scale()

# Quick: Fast iteration during development
suite = BenchmarkSuite.quick()

# Generate test cases
test_cases = await suite.generate_all_test_cases()
```

#### Custom Benchmarks

```python
from agenkit.evaluation.benchmarks import Benchmark, TestCase


class CustomBenchmark(Benchmark):
    @property
    def name(self) -> str:
        return "custom_benchmark"

    @property
    def description(self) -> str:
        return "My custom test suite"

    async def generate_test_cases(self) -> List[TestCase]:
        return [
            TestCase(input="Question 1", expected="Answer 1", tags=["custom"]),
            # ... more test cases
        ]


# Use it
suite = BenchmarkSuite(benchmarks=[CustomBenchmark()])
```

#### Built-in Benchmarks

**SimpleQABenchmark**: Basic question-answering
```python
from agenkit.evaluation.benchmarks import SimpleQABenchmark

benchmark = SimpleQABenchmark()
test_cases = await benchmark.generate_test_cases()
# Returns 5 basic Q&A tests
```

**NeedleInHaystackBenchmark**: Retrieval from large contexts
```python
from agenkit.evaluation.benchmarks import NeedleInHaystackBenchmark

benchmark = NeedleInHaystackBenchmark(context_length=10_000, needle_count=5)
test_cases = await benchmark.generate_test_cases()
# Tests finding 5 facts in 10K token context
```

**ExtremeScaleBenchmark**: For endless (1M-25M tokens)
```python
from agenkit.evaluation.benchmarks import ExtremeScaleBenchmark

benchmark = ExtremeScaleBenchmark(
    test_lengths=[1_000_000, 10_000_000, 25_000_000], needles_per_length=10
)
test_cases = await benchmark.generate_test_cases()
# Tests retrieval at 1M, 10M, 25M tokens
```

**InformationRetentionBenchmark**: Long conversation recall
```python
from agenkit.evaluation.benchmarks import InformationRetentionBenchmark

benchmark = InformationRetentionBenchmark(
    conversation_length=1000, recall_points=[250, 500, 750, 1000]
)
# Tests if agent remembers facts across long conversations
```

### 5. Regression Detection

Catch quality degradation before production:

```python
from agenkit.evaluation import RegressionDetector

# Run baseline evaluation
baseline_result = await evaluator.evaluate(test_cases)

# Create detector
detector = RegressionDetector(
    baseline=baseline_result,
    thresholds={
        "accuracy": 0.10,  # 10% degradation threshold
        "latency": 0.20,  # 20% slower threshold
    },
)

# Later: detect regressions
current_result = await evaluator.evaluate(test_cases)
regressions = detector.detect(current_result)

if regressions:
    for reg in regressions:
        print(f"⚠️ {reg.metric_name} degraded:")
        print(f"   Baseline: {reg.baseline_value:.2f}")
        print(f"   Current: {reg.current_value:.2f}")
        print(f"   Degradation: {reg.degradation_percent:.1f}%")
        print(f"   Severity: {reg.severity.value}")
```

**Severity Levels**:
- `MINOR`: 10-20% degradation
- `MODERATE`: 20-50% degradation
- `CRITICAL`: >50% degradation

### 6. Session Recording & Replay

Record sessions for replay and A/B testing:

```python
from agenkit.evaluation import SessionRecorder, SessionReplay

# Record session
recorder = SessionRecorder()
wrapped_agent = recorder.wrap(agent)

# Use normally (automatically recorded)
await wrapped_agent.process(message, session_id="session-1")
await wrapped_agent.process(message2, session_id="session-1")

# Finalize
recording = await recorder.finalize_session("session-1")

# Later: Replay with different agent
replay = SessionReplay()
results_v1 = await replay.replay(recording, agent_v1)
results_v2 = await replay.replay(recording, agent_v2)

# Compare
comparison = await replay.compare(results_v1, results_v2)
print(f"Latency diff: {comparison['latency_diff_ms']:.2f}ms")
print(f"Output differences: {len(comparison['output_differences'])}")
```

## Extreme-Scale Evaluation (For Endless)

### Problem

endless operates at **25M+ tokens** with 100x-1000x compression. Standard benchmarks can't validate:
- Compression quality at massive scale
- Retrieval accuracy from 25M token contexts
- Information retention after compression
- Quality degradation as context grows

### Solution

```python
from agenkit.evaluation import Evaluator, BenchmarkSuite
from agenkit.evaluation.context_metrics import CompressionMetrics

# 1. Set up extreme-scale metrics
compression_metric = CompressionMetrics(
    test_lengths=[1_000_000, 10_000_000, 25_000_000], needle_count=10
)

evaluator = Evaluator(agent=endless_agent, metrics=[compression_metric])

# 2. Generate extreme-scale test suite
suite = BenchmarkSuite.extreme_scale()
test_cases = await suite.generate_all_test_cases()

# 3. Run evaluation
results = await evaluator.evaluate(test_cases)

# 4. Analyze compression quality
for length, stats in results.metadata["compression_stats"].items():
    print(f"\n{length / 1e6}M tokens:")
    print(f"  Compression: {stats.compression_ratio}x")
    print(f"  Retrieval: {stats.retrieval_accuracy:.2%}")
```

### Quality Degradation Curves

Test if quality degrades at extreme scale:

```python
# Test at multiple scales
test_lengths = [1_000_000, 5_000_000, 10_000_000, 25_000_000]

results = {}
for length in test_lengths:
    # Create context of target length
    # ... (populate context)

    # Measure retrieval accuracy
    accuracy = await measure_retrieval(agent, session_id, length)
    results[length] = accuracy

# Plot degradation curve
for length, accuracy in results.items():
    print(f"{length / 1e6}M tokens: {accuracy:.2%}")
```

## Real-World Scenarios

### Scenario 1: Continuous Quality Monitoring

```python
from agenkit.evaluation import Evaluator, RegressionDetector, AccuracyMetric

# Set up baseline
evaluator = Evaluator(agent, metrics=[AccuracyMetric()])
baseline = await evaluator.evaluate(standard_tests)

detector = RegressionDetector(baseline=baseline)

# Monitor in production
while True:
    # Run daily evaluation
    current = await evaluator.evaluate(standard_tests)

    # Check for regressions
    regressions = detector.detect(current, store_history=True)

    if regressions:
        # Alert team
        send_alert(f"Quality degradation detected: {regressions}")

    await asyncio.sleep(86400)  # Daily
```

### Scenario 2: A/B Testing Agent Versions

```python
from agenkit.evaluation import SessionRecorder, SessionReplay

# Record production sessions
recorder = SessionRecorder()
wrapped = recorder.wrap(agent_v1)

# Collect 100 sessions
for i in range(100):
    # ... process real user interactions
    await recorder.finalize_session(f"session-{i}")

# Test new version against recorded sessions
replay = SessionReplay()
for i in range(100):
    recording = await recorder.load_recording(f"session-{i}")

    results_v1 = await replay.replay(recording, agent_v1)
    results_v2 = await replay.replay(recording, agent_v2)

    comparison = await replay.compare(results_v1, results_v2)
    # Analyze differences
```

### Scenario 3: Validating Endless at 25M Tokens

```python
from agenkit.evaluation.benchmarks import ExtremeScaleBenchmark
from agenkit.evaluation.context_metrics import CompressionMetrics

# Create extreme-scale benchmark
benchmark = ExtremeScaleBenchmark(
    test_lengths=[1_000_000, 10_000_000, 25_000_000], needles_per_length=20
)

compression_metric = CompressionMetrics(
    test_lengths=[1_000_000, 10_000_000, 25_000_000], needle_count=20
)

# Run evaluation
evaluator = Evaluator(endless_agent, metrics=[compression_metric])
test_cases = await benchmark.generate_test_cases()
results = await evaluator.evaluate(test_cases)

# Validate compression quality
for length, stats in results.metadata["compression_stats"].items():
    assert stats.compression_ratio >= 100, "Compression too low"
    assert stats.retrieval_accuracy >= 0.95, "Retrieval accuracy too low"
    print(f"✅ {length / 1e6}M tokens: {stats.compression_ratio}x @ {stats.retrieval_accuracy:.2%}")
```

## API Reference

### Evaluator

```python
evaluator = Evaluator(
    agent: Agent,
    metrics: List[Metric] = None,
    session_id: str = None
)

# Methods
result = await evaluator.evaluate(test_cases, evaluation_id=None)
metrics = await evaluator.evaluate_single(input_message, expected_output=None)
```

### EvaluationResult

```python
@dataclass
class EvaluationResult:
    evaluation_id: str
    agent_name: str
    timestamp: datetime

    # Metrics
    metrics: Dict[str, float]
    aggregated_metrics: Dict[str, Dict[str, float]]

    # Context (for endless)
    context_length: Optional[int]
    compressed_length: Optional[int]
    compression_ratio: Optional[float]

    # Quality
    accuracy: Optional[float]
    quality_score: Optional[float]

    # Performance
    avg_latency_ms: Optional[float]
    p95_latency_ms: Optional[float]

    # Tests
    total_tests: int
    passed_tests: int
    failed_tests: int

    @property
    def success_rate(self) -> float: ...
```

### RegressionDetector

```python
detector = RegressionDetector(
    thresholds: Dict[str, float] = None,
    baseline: EvaluationResult = None
)

# Methods
detector.set_baseline(result)
regressions = detector.detect(result, store_history=True)
trend = detector.get_trend(metric_name, window=10)
comparison = detector.compare_results(result_a, result_b)
```

### SessionRecorder

```python
recorder = SessionRecorder(storage=InMemoryRecordingStorage())

# Methods
wrapped_agent = recorder.wrap(agent)
await recorder.start_session(session_id, agent_name)
await recorder.record_interaction(session_id, input_msg, output_msg, latency_ms)
recording = await recorder.finalize_session(session_id)
recording = await recorder.load_recording(session_id)
```

## Testing

```bash
# Run evaluation framework tests (64 tests)
uv run pytest tests/evaluation/ -v

# Run example
python examples/evaluation/evaluation_demo.py
```

## Best Practices

1. **Always set baselines** before deploying to production
2. **Monitor trends** not just point-in-time metrics
3. **Test at scale** if your agent operates at scale (use extreme benchmarks)
4. **Record sessions** for reproducible testing
5. **Use custom metrics** for domain-specific quality measures
6. **Set appropriate thresholds** for regression detection

## Related

- [Memory Systems](../memory/) - Context management
- [Cost Tracking](../budget/) - Budget management
- [Checkpointing](../checkpointing/) - Durable execution

## Contributing

Want to add a metric or benchmark? Implement the base classes:

```python
from agenkit.evaluation import Metric, Benchmark

class MyMetric(Metric):
    @property
    def name(self) -> str: ...

    async def measure(self, ...): ...

    def aggregate(self, measurements): ...

class MyBenchmark(Benchmark):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    async def generate_test_cases(self): ...
```
