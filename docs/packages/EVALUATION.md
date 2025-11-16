# Evaluation

Comprehensive evaluation framework for autonomous agents operating at scale, from simple quality checks to extreme-scale benchmarking at 1M-25M+ tokens.

## Overview

The Evaluation package provides sophisticated metrics, benchmarking, and regression detection for agents that need rigorous quality assurance. Essential for production deployments, A/B testing, and continuous integration workflows.

**Key Statistics:**
- **Python**: 2,738 lines
- **Go**: 3,173 lines (116% parity)
- **Metrics**: 15+ quality and performance metrics
- **Benchmarks**: 3 benchmark suites (SimpleQA, NeedleInHaystack, ExtremeScale)
- **Scale**: Tested up to 25M+ tokens

## Features

✅ **Quality Metrics** - Accuracy, precision/recall, F1 score, quality scoring
✅ **Context Metrics** - Compression ratio, retrieval accuracy at extreme scale
✅ **Latency Metrics** - Response time, throughput, percentile analysis
✅ **Regression Detection** - Automatic quality degradation alerts
✅ **Benchmark Suites** - Industry-standard test sets
✅ **Session Recording** - Capture and replay conversations
✅ **A/B Testing** - Compare agent configurations
✅ **Cross-language** - Full Python/Go parity

## Installation

Evaluation is included in the core Agenkit package:

```bash
# Python
pip install agenkit

# Go
go get github.com/agenkit/agenkit-go/evaluation
```

## Quick Start

### Python

```python
from agenkit.evaluation import Evaluator, QualityMetrics
from agenkit import Agent, Message

# Create evaluator
evaluator = Evaluator()

# Evaluate agent response
agent = Agent(...)
response = agent.process(Message(role="user", content="What is 2+2?"))

metrics = evaluator.evaluate_response(
    expected="4",
    actual=response.content,
    context={"question": "What is 2+2?"}
)

print(f"Accuracy: {metrics.accuracy:.2%}")
print(f"Quality: {metrics.quality_score:.2f}/10")
```

### Go

```go
package main

import (
    "fmt"
    "github.com/agenkit/agenkit-go/agenkit"
    "github.com/agenkit/agenkit-go/evaluation"
)

func main() {
    // Create evaluator
    evaluator := evaluation.NewEvaluator()

    // Evaluate agent response
    agent := agenkit.NewAgent(...)
    response, _ := agent.Process(&agenkit.Message{
        Role:    "user",
        Content: "What is 2+2?",
    })

    metrics := evaluator.EvaluateResponse(
        "4",                    // expected
        response.Content,       // actual
        map[string]interface{}{ // context
            "question": "What is 2+2?",
        },
    )

    fmt.Printf("Accuracy: %.2f%%\n", metrics.Accuracy*100)
    fmt.Printf("Quality: %.2f/10\n", metrics.QualityScore)
}
```

## Quality Metrics

### 1. Accuracy Metrics

Measure correctness of agent responses:

**Python:**
```python
from agenkit.evaluation import AccuracyMetrics

accuracy_metrics = AccuracyMetrics()

# Exact match
is_correct = accuracy_metrics.exact_match(
    expected="Paris",
    actual="Paris"
)

# Fuzzy match (handles typos, case, whitespace)
is_correct = accuracy_metrics.fuzzy_match(
    expected="Paris, France",
    actual="paris france",
    threshold=0.8  # 80% similarity
)

# Semantic match (using embeddings)
is_correct = accuracy_metrics.semantic_match(
    expected="The capital of France",
    actual="Paris is France's capital city",
    threshold=0.85
)
```

**Go:**
```go
accuracyMetrics := evaluation.NewAccuracyMetrics()

// Exact match
isCorrect := accuracyMetrics.ExactMatch("Paris", "Paris")

// Fuzzy match
isCorrect = accuracyMetrics.FuzzyMatch(
    "Paris, France",
    "paris france",
    0.8,
)

// Semantic match
isCorrect = accuracyMetrics.SemanticMatch(
    "The capital of France",
    "Paris is France's capital city",
    0.85,
)
```

**Use cases:**
- Factual Q&A validation
- Knowledge base accuracy
- Multi-choice testing

### 2. Precision & Recall

Measure information retrieval quality:

**Python:**
```python
from agenkit.evaluation import PrecisionRecall

pr_metrics = PrecisionRecall()

# Calculate precision and recall
expected_facts = ["Paris", "France", "capital"]
actual_facts = ["Paris", "France", "city", "capital"]

precision = pr_metrics.precision(expected_facts, actual_facts)
recall = pr_metrics.recall(expected_facts, actual_facts)
f1_score = pr_metrics.f1_score(expected_facts, actual_facts)

print(f"Precision: {precision:.2%}")  # 75% (3/4 correct)
print(f"Recall: {recall:.2%}")        # 100% (all expected found)
print(f"F1 Score: {f1_score:.2%}")    # 85.7%
```

**Go:**
```go
prMetrics := evaluation.NewPrecisionRecall()

expectedFacts := []string{"Paris", "France", "capital"}
actualFacts := []string{"Paris", "France", "city", "capital"}

precision := prMetrics.Precision(expectedFacts, actualFacts)
recall := prMetrics.Recall(expectedFacts, actualFacts)
f1Score := prMetrics.F1Score(expectedFacts, actualFacts)

fmt.Printf("Precision: %.2f%%\n", precision*100)
fmt.Printf("Recall: %.2f%%\n", recall*100)
fmt.Printf("F1 Score: %.2f%%\n", f1Score*100)
```

**Use cases:**
- Multi-fact extraction
- Document summarization
- Information retrieval

### 3. Quality Scoring

Holistic quality assessment (0-10 scale):

**Python:**
```python
from agenkit.evaluation import QualityScorer

scorer = QualityScorer()

score = scorer.score_response(
    response=agent_response,
    criteria={
        "accuracy": 0.3,      # 30% weight
        "completeness": 0.25, # 25% weight
        "clarity": 0.25,      # 25% weight
        "relevance": 0.2      # 20% weight
    }
)

print(f"Overall Quality: {score.overall:.1f}/10")
print(f"Breakdown:")
print(f"  Accuracy: {score.accuracy:.1f}/10")
print(f"  Completeness: {score.completeness:.1f}/10")
print(f"  Clarity: {score.clarity:.1f}/10")
print(f"  Relevance: {score.relevance:.1f}/10")
```

**Go:**
```go
scorer := evaluation.NewQualityScorer()

score := scorer.ScoreResponse(
    agentResponse,
    map[string]float64{
        "accuracy":     0.3,
        "completeness": 0.25,
        "clarity":      0.25,
        "relevance":    0.2,
    },
)

fmt.Printf("Overall Quality: %.1f/10\n", score.Overall)
fmt.Printf("Breakdown:\n")
fmt.Printf("  Accuracy: %.1f/10\n", score.Accuracy)
fmt.Printf("  Completeness: %.1f/10\n", score.Completeness)
fmt.Printf("  Clarity: %.1f/10\n", score.Clarity)
fmt.Printf("  Relevance: %.1f/10\n", score.Relevance)
```

**Use cases:**
- Subjective quality assessment
- Multi-dimensional evaluation
- Human-aligned scoring

## Context Metrics

### Compression Quality

Evaluate memory compression at extreme scale:

**Python:**
```python
from agenkit.evaluation import CompressionMetrics

compression_metrics = CompressionMetrics(
    test_lengths=[100_000, 1_000_000, 10_000_000],
    needle_count=10
)

# Test at different context lengths
needles = ["Paris is the capital of France"] * 10
results = compression_metrics.evaluate_at_lengths(
    agent=agent,
    session_id="test-session",
    needles=needles
)

for length, stats in results.items():
    print(f"\n{length:,} tokens:")
    print(f"  Compression: {stats.compression_ratio:.1f}x")
    print(f"  Retrieval: {stats.retrieval_accuracy:.1%}")
    print(f"  Latency: {stats.avg_latency_ms:.0f}ms")
```

**Go:**
```go
compressionMetrics := evaluation.NewCompressionMetrics(
    []int{100_000, 1_000_000, 10_000_000},
    10,
)

needles := []string{"Paris is the capital of France"}
results := compressionMetrics.EvaluateAtLengths(
    agent,
    "test-session",
    needles,
)

for length, stats := range results {
    fmt.Printf("\n%d tokens:\n", length)
    fmt.Printf("  Compression: %.1fx\n", stats.CompressionRatio)
    fmt.Printf("  Retrieval: %.1f%%\n", stats.RetrievalAccuracy*100)
    fmt.Printf("  Latency: %.0fms\n", stats.AvgLatencyMs)
}
```

**Use cases:**
- Extreme-scale systems (1M-25M+ tokens)
- Memory optimization
- Compression strategy validation

### Retrieval Accuracy

Test information retrieval at scale:

**Python:**
```python
from agenkit.evaluation import RetrievalMetrics

retrieval_metrics = RetrievalMetrics()

# Test "needle in haystack"
accuracy = retrieval_metrics.needle_in_haystack(
    agent=agent,
    session_id="test-session",
    haystack_size=1_000_000,  # 1M tokens
    needle="The secret code is: ABC123",
    question="What is the secret code?"
)

print(f"Retrieval accuracy: {accuracy:.1%}")
```

**Go:**
```go
retrievalMetrics := evaluation.NewRetrievalMetrics()

accuracy := retrievalMetrics.NeedleInHaystack(
    agent,
    "test-session",
    1_000_000, // 1M tokens
    "The secret code is: ABC123",
    "What is the secret code?",
)

fmt.Printf("Retrieval accuracy: %.1f%%\n", accuracy*100)
```

**Use cases:**
- Long-context systems
- RAG validation
- Memory effectiveness

## Latency Metrics

### Response Time Analysis

**Python:**
```python
from agenkit.evaluation import LatencyMetrics
import time

latency_metrics = LatencyMetrics()

# Measure single request
start = time.time()
response = agent.process(message)
latency_ms = (time.time() - start) * 1000

latency_metrics.record_latency(latency_ms)

# Get statistics
stats = latency_metrics.get_stats()
print(f"Avg: {stats.avg_ms:.0f}ms")
print(f"P50: {stats.p50_ms:.0f}ms")
print(f"P95: {stats.p95_ms:.0f}ms")
print(f"P99: {stats.p99_ms:.0f}ms")
```

**Go:**
```go
latencyMetrics := evaluation.NewLatencyMetrics()

// Measure single request
start := time.Now()
response, _ := agent.Process(message)
latencyMs := float64(time.Since(start).Milliseconds())

latencyMetrics.RecordLatency(latencyMs)

// Get statistics
stats := latencyMetrics.GetStats()
fmt.Printf("Avg: %.0fms\n", stats.AvgMs)
fmt.Printf("P50: %.0fms\n", stats.P50Ms)
fmt.Printf("P95: %.0fms\n", stats.P95Ms)
fmt.Printf("P99: %.0fms\n", stats.P99Ms)
```

### Throughput Testing

**Python:**
```python
from agenkit.evaluation import ThroughputMetrics
import asyncio

throughput_metrics = ThroughputMetrics()

# Test concurrent requests
async def load_test():
    tasks = []
    for i in range(100):
        task = agent.process_async(Message(
            role="user",
            content=f"Request {i}"
        ))
        tasks.append(task)

    await asyncio.gather(*tasks)

# Measure throughput
start = time.time()
asyncio.run(load_test())
duration = time.time() - start

throughput = 100 / duration
print(f"Throughput: {throughput:.1f} req/s")
```

**Go:**
```go
throughputMetrics := evaluation.NewThroughputMetrics()

// Test concurrent requests
var wg sync.WaitGroup
start := time.Now()

for i := 0; i < 100; i++ {
    wg.Add(1)
    go func(id int) {
        defer wg.Done()
        agent.Process(&agenkit.Message{
            Role:    "user",
            Content: fmt.Sprintf("Request %d", id),
        })
    }(i)
}

wg.Wait()
duration := time.Since(start).Seconds()

throughput := 100.0 / duration
fmt.Printf("Throughput: %.1f req/s\n", throughput)
```

## Regression Detection

Automatically detect quality degradation:

**Python:**
```python
from agenkit.evaluation import RegressionDetector

detector = RegressionDetector(
    baseline_accuracy=0.95,
    baseline_latency_ms=500,
    accuracy_threshold=0.05,  # Alert if accuracy drops >5%
    latency_threshold=2.0     # Alert if latency increases >2x
)

# Evaluate new version
current_metrics = evaluator.evaluate_agent(agent)

# Check for regressions
regressions = detector.detect_regressions(current_metrics)

if regressions:
    for regression in regressions:
        print(f"⚠️  Regression detected: {regression.metric}")
        print(f"   Baseline: {regression.baseline}")
        print(f"   Current: {regression.current}")
        print(f"   Change: {regression.change_percent:.1f}%")
        print(f"   Severity: {regression.severity}")
```

**Go:**
```go
detector := evaluation.NewRegressionDetector(
    0.95,  // baseline accuracy
    500.0, // baseline latency ms
    0.05,  // accuracy threshold
    2.0,   // latency threshold
)

// Evaluate new version
currentMetrics := evaluator.EvaluateAgent(agent)

// Check for regressions
regressions := detector.DetectRegressions(currentMetrics)

if len(regressions) > 0 {
    for _, regression := range regressions {
        fmt.Printf("⚠️  Regression detected: %s\n", regression.Metric)
        fmt.Printf("   Baseline: %v\n", regression.Baseline)
        fmt.Printf("   Current: %v\n", regression.Current)
        fmt.Printf("   Change: %.1f%%\n", regression.ChangePercent)
        fmt.Printf("   Severity: %s\n", regression.Severity)
    }
}
```

**Severity levels:**
- `Low` - Minor degradation within tolerance
- `Medium` - Noticeable quality drop
- `High` - Significant regression, investigate immediately
- `Critical` - Severe degradation, block release

## Benchmark Suites

### 1. SimpleQA Benchmark

Standard Q&A evaluation:

**Python:**
```python
from agenkit.evaluation import SimpleQABenchmark

benchmark = SimpleQABenchmark()

# Run benchmark
results = benchmark.run(agent)

print(f"Overall Score: {results.overall_score:.1%}")
print(f"Categories:")
print(f"  Factual: {results.factual_accuracy:.1%}")
print(f"  Math: {results.math_accuracy:.1%}")
print(f"  Reasoning: {results.reasoning_accuracy:.1%}")
print(f"  Common Sense: {results.common_sense_accuracy:.1%}")
```

**Go:**
```go
benchmark := evaluation.NewSimpleQABenchmark()

results := benchmark.Run(agent)

fmt.Printf("Overall Score: %.1f%%\n", results.OverallScore*100)
fmt.Printf("Categories:\n")
fmt.Printf("  Factual: %.1f%%\n", results.FactualAccuracy*100)
fmt.Printf("  Math: %.1f%%\n", results.MathAccuracy*100)
fmt.Printf("  Reasoning: %.1f%%\n", results.ReasoningAccuracy*100)
fmt.Printf("  Common Sense: %.1f%%\n", results.CommonSenseAccuracy*100)
```

### 2. Needle In Haystack Benchmark

Long-context retrieval testing:

**Python:**
```python
from agenkit.evaluation import NeedleInHaystackBenchmark

benchmark = NeedleInHaystackBenchmark(
    lengths=[10_000, 100_000, 1_000_000, 10_000_000],
    depths=[0.1, 0.5, 0.9]  # Beginning, middle, end
)

# Run benchmark
results = benchmark.run(agent)

print(f"Overall Accuracy: {results.overall_accuracy:.1%}")
print(f"\nBy Length:")
for length, accuracy in results.by_length.items():
    print(f"  {length:,} tokens: {accuracy:.1%}")

print(f"\nBy Depth:")
for depth, accuracy in results.by_depth.items():
    print(f"  {depth:.0%} position: {accuracy:.1%}")
```

**Go:**
```go
benchmark := evaluation.NewNeedleInHaystackBenchmark(
    []int{10_000, 100_000, 1_000_000, 10_000_000},
    []float64{0.1, 0.5, 0.9},
)

results := benchmark.Run(agent)

fmt.Printf("Overall Accuracy: %.1f%%\n", results.OverallAccuracy*100)
fmt.Printf("\nBy Length:\n")
for length, accuracy := range results.ByLength {
    fmt.Printf("  %d tokens: %.1f%%\n", length, accuracy*100)
}

fmt.Printf("\nBy Depth:\n")
for depth, accuracy := range results.ByDepth {
    fmt.Printf("  %.0f%% position: %.1f%%\n", depth*100, accuracy*100)
}
```

### 3. Extreme Scale Benchmark

Test systems at 1M-25M+ tokens:

**Python:**
```python
from agenkit.evaluation import ExtremeScaleBenchmark

benchmark = ExtremeScaleBenchmark(
    max_length=25_000_000,  # 25M tokens
    compression_ratios=[100, 1000, 10000]
)

# Run benchmark (may take hours)
results = benchmark.run(agent)

print(f"Max Context: {results.max_context:,} tokens")
print(f"Compression: {results.compression_ratio:.0f}:1")
print(f"Retrieval: {results.retrieval_accuracy:.1%}")
print(f"Quality: {results.quality_score:.1f}/10")
print(f"Avg Latency: {results.avg_latency_ms:.0f}ms")
```

**Go:**
```go
benchmark := evaluation.NewExtremeScaleBenchmark(
    25_000_000, // 25M tokens
    []int{100, 1000, 10000},
)

results := benchmark.Run(agent)

fmt.Printf("Max Context: %d tokens\n", results.MaxContext)
fmt.Printf("Compression: %d:1\n", results.CompressionRatio)
fmt.Printf("Retrieval: %.1f%%\n", results.RetrievalAccuracy*100)
fmt.Printf("Quality: %.1f/10\n", results.QualityScore)
fmt.Printf("Avg Latency: %.0fms\n", results.AvgLatencyMs)
```

## Session Recording

Capture and replay conversations:

**Python:**
```python
from agenkit.evaluation import SessionRecorder

recorder = SessionRecorder(output_dir="./recordings")

# Record session
session_id = recorder.start_recording(agent)

# Agent processes messages (automatically recorded)
agent.process(Message(role="user", content="Hello"))
agent.process(Message(role="user", content="What is 2+2?"))

# Stop recording
recorder.stop_recording(session_id)

# Replay session
replayed_agent = Agent(...)
replay_results = recorder.replay_session(
    session_id=session_id,
    agent=replayed_agent
)

# Compare recordings
comparison = recorder.compare_sessions(
    original_session_id=session_id,
    replay_session_id=replay_results.session_id
)

print(f"Match rate: {comparison.match_rate:.1%}")
print(f"Avg response difference: {comparison.avg_difference:.2f}")
```

**Go:**
```go
recorder := evaluation.NewSessionRecorder("./recordings")

// Record session
sessionID := recorder.StartRecording(agent)

// Agent processes messages
agent.Process(&agenkit.Message{Role: "user", Content: "Hello"})
agent.Process(&agenkit.Message{Role: "user", Content: "What is 2+2?"})

// Stop recording
recorder.StopRecording(sessionID)

// Replay session
replayedAgent := agenkit.NewAgent(...)
replayResults := recorder.ReplaySession(sessionID, replayedAgent)

// Compare recordings
comparison := recorder.CompareSessions(sessionID, replayResults.SessionID)

fmt.Printf("Match rate: %.1f%%\n", comparison.MatchRate*100)
fmt.Printf("Avg response difference: %.2f\n", comparison.AvgDifference)
```

## A/B Testing

Compare different agent configurations:

**Python:**
```python
from agenkit.evaluation import ABTest

# Create two agent variants
agent_a = Agent(model="claude-sonnet-4", temperature=0.7)
agent_b = Agent(model="claude-opus-4", temperature=0.9)

# Run A/B test
ab_test = ABTest(
    agent_a=agent_a,
    agent_b=agent_b,
    test_cases=test_dataset,
    metrics=["accuracy", "quality", "latency"]
)

results = ab_test.run()

print(f"Winner: Agent {results.winner}")
print(f"\nAgent A:")
print(f"  Accuracy: {results.agent_a.accuracy:.1%}")
print(f"  Quality: {results.agent_a.quality:.1f}/10")
print(f"  Latency: {results.agent_a.latency_ms:.0f}ms")

print(f"\nAgent B:")
print(f"  Accuracy: {results.agent_b.accuracy:.1%}")
print(f"  Quality: {results.agent_b.quality:.1f}/10")
print(f"  Latency: {results.agent_b.latency_ms:.0f}ms")

# Statistical significance
print(f"\nStatistical Significance: p={results.p_value:.3f}")
print(f"Confidence: {results.confidence:.1%}")
```

**Go:**
```go
// Create two agent variants
agentA := agenkit.NewAgent("claude-sonnet-4", 0.7)
agentB := agenkit.NewAgent("claude-opus-4", 0.9)

// Run A/B test
abTest := evaluation.NewABTest(
    agentA,
    agentB,
    testDataset,
    []string{"accuracy", "quality", "latency"},
)

results := abTest.Run()

fmt.Printf("Winner: Agent %s\n", results.Winner)
fmt.Printf("\nAgent A:\n")
fmt.Printf("  Accuracy: %.1f%%\n", results.AgentA.Accuracy*100)
fmt.Printf("  Quality: %.1f/10\n", results.AgentA.Quality)
fmt.Printf("  Latency: %.0fms\n", results.AgentA.LatencyMs)

fmt.Printf("\nAgent B:\n")
fmt.Printf("  Accuracy: %.1f%%\n", results.AgentB.Accuracy*100)
fmt.Printf("  Quality: %.1f/10\n", results.AgentB.Quality)
fmt.Printf("  Latency: %.0fms\n", results.AgentB.LatencyMs)

fmt.Printf("\nStatistical Significance: p=%.3f\n", results.PValue)
fmt.Printf("Confidence: %.1f%%\n", results.Confidence*100)
```

## Advanced Usage

### Custom Evaluation Metrics

Create domain-specific metrics:

**Python:**
```python
from agenkit.evaluation import MetricBase

class CodeQualityMetric(MetricBase):
    def evaluate(self, response: str, context: dict) -> float:
        """Evaluate code quality (0-10)."""
        score = 0.0

        # Check for syntax errors
        try:
            compile(response, '<string>', 'exec')
            score += 3.0
        except:
            return 0.0

        # Check for good practices
        if 'def ' in response or 'class ' in response:
            score += 2.0
        if '"""' in response or "'''" in response:
            score += 2.0  # Has docstrings
        if 'type:' in response or '->' in response:
            score += 1.5  # Has type hints
        if len(response.split('\n')) < 100:
            score += 1.5  # Reasonable length

        return min(score, 10.0)

# Use custom metric
evaluator = Evaluator(metrics=[CodeQualityMetric()])
score = evaluator.evaluate_response(response=code_response)
```

**Go:**
```go
type CodeQualityMetric struct{}

func (m *CodeQualityMetric) Evaluate(response string, context map[string]interface{}) float64 {
    score := 0.0

    // Check for basic structure
    if strings.Contains(response, "func ") {
        score += 3.0
    }

    // Check for comments
    if strings.Contains(response, "//") {
        score += 2.0
    }

    // Check for error handling
    if strings.Contains(response, "error") {
        score += 2.0
    }

    // Check for tests
    if strings.Contains(response, "Test") {
        score += 1.5
    }

    // Check length
    if len(strings.Split(response, "\n")) < 100 {
        score += 1.5
    }

    if score > 10.0 {
        return 10.0
    }
    return score
}

// Use custom metric
evaluator := evaluation.NewEvaluator([]evaluation.Metric{&CodeQualityMetric{}})
score := evaluator.EvaluateResponse(codeResponse, context)
```

### Continuous Evaluation

Monitor agents in production:

**Python:**
```python
from agenkit.evaluation import ContinuousEvaluator
import asyncio

evaluator = ContinuousEvaluator(
    agent=agent,
    interval_seconds=60,  # Evaluate every minute
    metrics=["accuracy", "latency", "quality"]
)

# Start continuous evaluation
async def monitor():
    async for snapshot in evaluator.run():
        print(f"\n[{snapshot.timestamp}]")
        print(f"Requests: {snapshot.request_count}")
        print(f"Accuracy: {snapshot.accuracy:.1%}")
        print(f"Avg Latency: {snapshot.avg_latency_ms:.0f}ms")
        print(f"Quality: {snapshot.quality_score:.1f}/10")

        # Alert on issues
        if snapshot.accuracy < 0.9:
            alert("Low accuracy detected!")
        if snapshot.avg_latency_ms > 1000:
            alert("High latency detected!")

asyncio.run(monitor())
```

**Go:**
```go
evaluator := evaluation.NewContinuousEvaluator(
    agent,
    60, // interval seconds
    []string{"accuracy", "latency", "quality"},
)

// Start continuous evaluation
snapshots := evaluator.Run()

for snapshot := range snapshots {
    fmt.Printf("\n[%s]\n", snapshot.Timestamp)
    fmt.Printf("Requests: %d\n", snapshot.RequestCount)
    fmt.Printf("Accuracy: %.1f%%\n", snapshot.Accuracy*100)
    fmt.Printf("Avg Latency: %.0fms\n", snapshot.AvgLatencyMs)
    fmt.Printf("Quality: %.1f/10\n", snapshot.QualityScore)

    // Alert on issues
    if snapshot.Accuracy < 0.9 {
        alert("Low accuracy detected!")
    }
    if snapshot.AvgLatencyMs > 1000 {
        alert("High latency detected!")
    }
}
```

### Integration with CI/CD

**Python (pytest integration):**
```python
# tests/test_agent_quality.py
import pytest
from agenkit.evaluation import Evaluator, SimpleQABenchmark

@pytest.fixture
def agent():
    return Agent(...)

def test_agent_accuracy(agent):
    """Ensure agent meets accuracy threshold."""
    evaluator = Evaluator()
    accuracy = evaluator.evaluate_accuracy(agent, test_cases)
    assert accuracy >= 0.95, f"Accuracy {accuracy:.1%} below threshold"

def test_agent_latency(agent):
    """Ensure agent meets latency requirements."""
    evaluator = Evaluator()
    avg_latency = evaluator.evaluate_latency(agent, test_cases)
    assert avg_latency <= 500, f"Latency {avg_latency:.0f}ms exceeds limit"

def test_agent_benchmark(agent):
    """Run standard benchmark suite."""
    benchmark = SimpleQABenchmark()
    results = benchmark.run(agent)
    assert results.overall_score >= 0.90
```

**Go (testing integration):**
```go
// evaluation_test.go
package evaluation_test

import (
    "testing"
    "github.com/agenkit/agenkit-go/evaluation"
)

func TestAgentAccuracy(t *testing.T) {
    agent := setupAgent()
    evaluator := evaluation.NewEvaluator()

    accuracy := evaluator.EvaluateAccuracy(agent, testCases)
    if accuracy < 0.95 {
        t.Errorf("Accuracy %.1f%% below threshold", accuracy*100)
    }
}

func TestAgentLatency(t *testing.T) {
    agent := setupAgent()
    evaluator := evaluation.NewEvaluator()

    avgLatency := evaluator.EvaluateLatency(agent, testCases)
    if avgLatency > 500 {
        t.Errorf("Latency %.0fms exceeds limit", avgLatency)
    }
}

func TestAgentBenchmark(t *testing.T) {
    agent := setupAgent()
    benchmark := evaluation.NewSimpleQABenchmark()

    results := benchmark.Run(agent)
    if results.OverallScore < 0.90 {
        t.Errorf("Benchmark score %.1f%% below threshold", results.OverallScore*100)
    }
}
```

## Best Practices

### 1. Define Quality Baselines

```python
# Establish baselines from production data
baseline_evaluator = Evaluator()
baseline_metrics = baseline_evaluator.evaluate_agent(
    agent=production_agent,
    test_cases=representative_sample
)

# Store baselines
baselines = {
    "accuracy": baseline_metrics.accuracy,
    "latency_p95": baseline_metrics.latency_p95,
    "quality_score": baseline_metrics.quality_score
}

# Use for regression detection
regression_detector = RegressionDetector(
    baseline_accuracy=baselines["accuracy"],
    baseline_latency_ms=baselines["latency_p95"]
)
```

### 2. Use Representative Test Cases

```python
# Create diverse test set
test_cases = [
    # Common queries (70%)
    *load_common_queries(),

    # Edge cases (20%)
    *load_edge_cases(),

    # Adversarial cases (10%)
    *load_adversarial_cases()
]

# Ensure coverage across categories
evaluator = Evaluator()
results = evaluator.evaluate_by_category(agent, test_cases)
```

### 3. Monitor Multiple Metrics

```python
# Don't optimize for single metric
evaluator = Evaluator(metrics=[
    "accuracy",      # Correctness
    "quality",       # Overall quality
    "latency",       # Speed
    "token_usage",   # Efficiency
    "safety"         # Security
])

# Balance trade-offs
results = evaluator.evaluate_agent(agent)
if results.accuracy > 0.95 and results.latency_p95 < 500:
    print("✅ Meets all requirements")
```

### 4. Test at Scale

```python
# Test extreme-scale scenarios
extreme_scale_test = ExtremeScaleBenchmark(
    max_length=10_000_000,  # 10M tokens
    compression_ratios=[100, 1000]
)

results = extreme_scale_test.run(agent)

# Ensure quality maintained at scale
assert results.retrieval_accuracy > 0.90
assert results.quality_score > 7.0
```

### 5. Automate Regression Detection

```python
# Run on every commit
regression_detector = RegressionDetector(...)

# In CI/CD pipeline
def test_no_regressions():
    current_metrics = evaluator.evaluate_agent(agent)
    regressions = regression_detector.detect_regressions(current_metrics)

    # Fail build on critical regressions
    critical = [r for r in regressions if r.severity == "Critical"]
    assert len(critical) == 0, f"Critical regressions detected: {critical}"
```

## Performance

### Evaluation Throughput

| Operation | Throughput | Latency |
|-----------|------------|---------|
| Accuracy check | 10,000/s | <1ms |
| Quality scoring | 1,000/s | 10ms |
| Semantic match | 100/s | 100ms |
| Full benchmark | 10/s | 1s |

### Benchmark Duration

| Benchmark | Test Cases | Duration | Scale |
|-----------|------------|----------|-------|
| SimpleQA | 100 | 2 min | Standard |
| NeedleInHaystack | 40 | 10 min | 1M-10M tokens |
| ExtremeScale | 20 | 2 hours | 10M-25M tokens |

## Examples

See the `examples/evaluation/` directory for complete examples:

- `basic_evaluation.py` - Simple accuracy testing
- `quality_metrics.py` - Comprehensive quality assessment
- `regression_detection.py` - Automated regression detection
- `benchmarking.py` - Running benchmark suites
- `ab_testing.py` - Comparing agent configurations
- `continuous_evaluation.py` - Production monitoring
- `ci_integration.py` - CI/CD pipeline integration

## API Reference

### Python API

**Evaluator**
- `__init__(metrics: list[str] = None)`
- `evaluate_response(expected: str, actual: str, context: dict) -> Metrics`
- `evaluate_agent(agent: Agent, test_cases: list) -> AgentMetrics`
- `evaluate_accuracy(agent: Agent, test_cases: list) -> float`
- `evaluate_latency(agent: Agent, test_cases: list) -> float`
- `evaluate_quality(agent: Agent, test_cases: list) -> float`

**RegressionDetector**
- `__init__(baseline_accuracy: float, baseline_latency_ms: float, ...)`
- `detect_regressions(current_metrics: Metrics) -> list[Regression]`

**Benchmarks**
- `SimpleQABenchmark.run(agent: Agent) -> BenchmarkResults`
- `NeedleInHaystackBenchmark.run(agent: Agent) -> BenchmarkResults`
- `ExtremeScaleBenchmark.run(agent: Agent) -> BenchmarkResults`

**A/B Testing**
- `ABTest(agent_a: Agent, agent_b: Agent, test_cases: list, metrics: list)`
- `run() -> ABTestResults`

### Go API

**Evaluator**
- `NewEvaluator(metrics []string) *Evaluator`
- `EvaluateResponse(expected, actual string, context map[string]interface{}) *Metrics`
- `EvaluateAgent(agent Agent, testCases []TestCase) *AgentMetrics`
- `EvaluateAccuracy(agent Agent, testCases []TestCase) float64`
- `EvaluateLatency(agent Agent, testCases []TestCase) float64`
- `EvaluateQuality(agent Agent, testCases []TestCase) float64`

**RegressionDetector**
- `NewRegressionDetector(baselineAccuracy, baselineLatencyMs float64, ...) *RegressionDetector`
- `DetectRegressions(currentMetrics *Metrics) []*Regression`

**Benchmarks**
- `NewSimpleQABenchmark() *SimpleQABenchmark`
- `NewNeedleInHaystackBenchmark(lengths []int, depths []float64) *NeedleInHaystackBenchmark`
- `NewExtremeScaleBenchmark(maxLength int, ratios []int) *ExtremeScaleBenchmark`

**A/B Testing**
- `NewABTest(agentA, agentB Agent, testCases []TestCase, metrics []string) *ABTest`
- `Run() *ABTestResults`

## Troubleshooting

**Issue**: Evaluation taking too long
**Solution**: Reduce test case count, use sampling, or parallelize evaluation

**Issue**: Inconsistent accuracy scores
**Solution**: Increase test case diversity, use fuzzy/semantic matching instead of exact match

**Issue**: High false positive rate in regression detection
**Solution**: Adjust thresholds, use rolling averages, increase baseline sample size

**Issue**: Extreme-scale benchmarks failing
**Solution**: Ensure adequate memory compression, increase timeout, test incrementally at lower scales first

## Related Packages

- **[Memory Management](MEMORY.md)** - Test compression quality
- **[Budget Tracking](BUDGET.md)** - Monitor evaluation costs
- **[Safety & Security](SAFETY.md)** - Validate safety metrics

## Learn More

- [Evaluation Examples](../../examples/evaluation/)
- [Getting Started Guide](../../GETTING_STARTED.md)
- [Architecture Overview](../../ARCHITECTURE.md)

---

**Ready to measure your agent's quality?** Start with `SimpleQABenchmark` and scale up! 📊
