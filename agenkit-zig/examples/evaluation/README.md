# Zig Evaluation Framework Examples

This directory contains practical examples demonstrating the Zig evaluation framework.

## Examples

### 1. Basic Evaluation (`basic_evaluation_example.zig`)

Demonstrates fundamental evaluation concepts:
- Creating test cases (exact match and functional validators)
- Adding metadata to test cases
- Running evaluations
- Collecting metrics and results
- Error tracking

**Run:** `zig build run-evaluation-basic`

**Key Concepts:**
- `TestCase.initExact()` - Exact string matching
- `TestCase.initFunctional()` - Custom validation functions
- `EvaluationResult` - Collecting pass/fail and metrics
- `ErrorRecord` - Tracking failures

### 2. Session Recording (`session_recording_example.zig`)

Shows how to record and replay agent sessions:
- Recording interactions with metadata
- Multiple concurrent sessions
- Session replay functionality
- Statistics collection
- JSON export

**Run:** `zig build run-evaluation-recording`

**Key Concepts:**
- `SessionRecorder` - Thread-safe recording
- `Interaction` - Single request/response pair
- `SessionTrace` - Complete session history
- `SessionReplay` - Replay for debugging/testing

**Use Cases:**
- Debugging agent behavior
- Creating test fixtures from production
- Performance analysis
- Compliance audit trails

### 3. Regression Detection (`regression_detection_example.zig`)

Demonstrates performance monitoring across deployments:
- Establishing performance baselines
- Detecting regressions with statistical tests
- Severity classification
- Custom thresholds per metric
- CI/CD integration patterns

**Run:** `zig build run-evaluation-regression`

**Key Concepts:**
- `RegressionDetector` - Compare current vs baseline
- `BaselineMeasurement` - Statistical baseline (mean, std dev)
- `Severity` - none → minor → moderate → severe → critical
- Statistical significance testing (t-test approximation)

**Severity Levels:**
| Severity | Change | Action |
|----------|--------|--------|
| None | < 5% | Continue monitoring |
| Minor | 5-10% | Schedule review |
| Moderate | 10-25% | Investigate immediately |
| Severe | 25-50% | Roll back deployment |
| Critical | > 50% | Emergency rollback |

## Architecture

### Phase 1 Modules (Implemented)

```
src/evaluation/
├── core.zig              # TestCase, Evaluator, Metric interface
├── metrics.zig           # MetricsCollector, SessionResult
├── quality_metrics.zig   # Accuracy, Quality, PrecisionRecall
├── recorder.zig          # SessionRecorder, SessionReplay
├── regression.zig        # RegressionDetector, Severity
└── mod.zig               # Module exports
```

### Integration Tests

See `tests/evaluation/integration_test.zig` for:
- Multi-metric evaluation
- Recording during evaluation
- Metrics aggregation
- End-to-end pipelines

## Usage Patterns

### Basic Evaluation

```zig
const evaluation = @import("evaluation/mod.zig");

// Create test case
const tc = try evaluation.TestCase.initExact(
    allocator,
    "What is 2+2?",
    "4"
);
defer tc.deinit();

// Evaluate (with real agent)
const result = try evaluator.evaluate(&[_]*TestCase{tc}, "session-1");
defer result.deinit();

std.debug.print("Success Rate: {d:.1}%\n", .{result.successRate() * 100.0});
```

### Session Recording

```zig
const recorder = try evaluation.SessionRecorder.init(allocator);
defer recorder.deinit();

try recorder.startRecording("session-1");

const interaction = try evaluation.Interaction.init(
    allocator,
    "input",
    "output",
    duration_ms
);
try recorder.recordInteraction("session-1", interaction);
interaction.deinit();

try recorder.stopRecording("session-1");

// Replay
const trace = recorder.getTrace("session-1").?;
const replay = try evaluation.SessionReplay.init(allocator, trace);
defer replay.deinit();

while (replay.next()) |interaction| {
    // Process interaction
}
```

### Regression Detection

```zig
const config = evaluation.RegressionConfig{
    .min_change_percent = 5.0,
    .significance_level = 0.05,
    .min_samples = 5,
};

const detector = try evaluation.RegressionDetector.init(allocator, config);
defer detector.deinit();

// Establish baseline
try detector.setBaseline("accuracy", 0.92);
try detector.setBaseline("accuracy", 0.91);
// ... more samples

// Check current metrics
var current = std.StringHashMap(f64).init(allocator);
defer current.deinit();

try current.put("accuracy", 0.85); // 7.6% drop

var regressions = try detector.detect(current, allocator);
defer {
    for (regressions.items) |reg| reg.deinit();
    regressions.deinit();
}

for (regressions.items) |reg| {
    std.debug.print("{s}\n", .{reg.message});
    std.debug.print("Severity: {s}\n", .{reg.severity.toString()});
}
```

## Memory Management

All evaluation types follow Zig's explicit memory management:

```zig
// Always pass allocator
const tc = try TestCase.initExact(allocator, input, expected);

// Always call deinit()
defer tc.deinit();

// Or manually manage lifetime
tc.deinit(); // Frees all internal allocations
```

## Thread Safety

Some types are thread-safe:
- ✅ `MetricsCollector` - Uses mutex for concurrent recording
- ✅ `SessionRecorder` - Thread-safe session management
- ✅ `RegressionDetector` - Thread-safe baseline updates

## Next Steps

### Phase 2-3 (Coming Soon)

- **context_metrics.zig** - Extreme-scale evaluation (1M-25M tokens)
- **benchmarks.zig** - Standardized test suites
- **optimizer.zig** - Hyperparameter optimization
- **ab_testing.zig** - Statistical A/B testing
- **bayesian_optimizer.zig** - GP-based optimization
- **prompt_optimizer.zig** - Automated prompt engineering

### Contributing

When adding new evaluation frameworks:
1. Follow existing patterns (allocator passing, VTable interfaces)
2. Add comprehensive unit tests
3. Create usage examples
4. Update this README
5. Export types in `mod.zig`

## Resources

- **Zig Documentation:** https://ziglang.org/documentation/master/
- **Issue #310:** Full implementation plan
- **Integration Tests:** `tests/evaluation/integration_test.zig`

## Performance

Phase 1 frameworks are designed for efficiency:
- Minimal allocations (explicit control)
- No hidden costs (no GC)
- Thread-safe where needed (mutex-protected)
- Zero-cost abstractions (comptime + inlining)

Typical overhead:
- Test case creation: < 1μs
- Metric recording: < 100ns
- Regression check: < 10μs

## License

Same as parent project.
