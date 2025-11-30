# C++ Benchmarks

Performance benchmarks for all agenkit-cpp components.

## Running Benchmarks

```bash
# Build benchmarks
cmake -B build -S . -DAGENKIT_BUILD_BENCHMARKS=ON
cmake --build build

# Run all benchmarks
cmake --build build --target run_benchmarks

# Or run individually
./build/benchmarks/bench_core
./build/benchmarks/bench_http
./build/benchmarks/bench_patterns
./build/benchmarks/bench_evaluation
```

## Benchmark Suites

### bench_core
Core component benchmarks:
- Message creation and serialization
- Agent initialization and processing
- Result<T,E> operations

### bench_http
HTTP transport benchmarks:
- HTTP server creation and cleanup
- Request/response handling
- Connection management

### bench_patterns
Pattern benchmarks (all 11 patterns):
- Reflection, ReAct, Agents-as-Tools
- Orchestration, Reasoning with Tools
- Conversational, Task, Multiagent
- Planning, Autonomous, Memory

### bench_evaluation
Evaluation framework benchmarks:
- **Metrics Collection:** MetricMeasurement, SessionResult, MetricsCollector
- **Session Recording:** InteractionRecord, SessionRecorder
- **Evaluation Results:** EvaluationResult creation and serialization
- **Quality Metrics:** AccuracyMetric, QualityMetrics, PrecisionRecallMetric

## Baseline Performance (v0.37.0)

### Evaluation Framework Benchmarks

**Metrics Collection:**
- MetricMeasurement creation: <1 μs
- MetricMeasurement to_json: ~1 μs
- SessionResult creation: <1 μs
- SessionResult add 10 metrics: <1 μs
- SessionResult to_json (10 metrics): ~17 μs
- MetricsCollector (100 sessions): ~18 μs

**Session Recording:**
- InteractionRecord creation: ~2 μs
- InteractionRecord to_dict: ~1 μs
- SessionRecorder (10 interactions): ~44 μs

**Evaluation Results:**
- EvaluationResult creation: <1 μs
- EvaluationResult to_json: ~1 μs

**Quality Metrics:**
- AccuracyMetric measure: <1 μs
- QualityMetrics measure: ~1 μs
- PrecisionRecallMetric measure: <1 μs
- Metric aggregate (100 measurements): <1 μs

## Interpreting Results

- **Mean:** Average execution time
- **Median:** Middle value (more robust to outliers)
- **Min/Max:** Range of execution times

All times in microseconds (μs).

## Contributing

When adding new features:
1. Add corresponding benchmarks
2. Document baseline performance
3. Update this README with new benchmark categories
