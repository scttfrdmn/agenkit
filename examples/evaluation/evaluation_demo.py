"""
Evaluation Framework Demo

Demonstrates:
1. Basic agent evaluation
2. Custom metrics
3. Benchmark suites
4. Regression detection
5. Session recording and replay
"""

import asyncio
from agenkit.evaluation import (
    Evaluator,
    AccuracyMetric,
    QualityMetrics,
    BenchmarkSuite,
    RegressionDetector,
    SessionRecorder,
    SessionReplay
)
from agenkit.evaluation.context_metrics import ContextMetrics, LatencyMetric
from agenkit.interfaces import Message


class SimpleQAAgent:
    """Simple Q&A agent for demonstration."""

    def __init__(self, knowledge_base=None):
        self.knowledge_base = knowledge_base or {
            "capital of france": "Paris",
            "2+2": "4",
            "largest planet": "Jupiter",
        }
        self.name = "simple_qa_agent"

    async def process(self, message: Message, session_id=None):
        """Process message and return response."""
        query = message.content.lower()

        # Simple matching
        for key, value in self.knowledge_base.items():
            if key in query:
                return Message(
                    role="assistant",
                    content=f"The answer is {value}."
                )

        return Message(
            role="assistant",
            content="I don't know the answer to that."
        )


async def demo_basic_evaluation():
    """Demo 1: Basic agent evaluation with metrics."""
    print("=" * 60)
    print("Demo 1: Basic Agent Evaluation")
    print("=" * 60)

    # Create agent
    agent = SimpleQAAgent()

    # Create evaluator with metrics
    evaluator = Evaluator(
        agent,
        metrics=[
            AccuracyMetric(),
            QualityMetrics(),
            LatencyMetric()
        ]
    )

    # Define test cases
    test_cases = [
        {"input": "What is the capital of France?", "expected": "Paris"},
        {"input": "What is 2+2?", "expected": "4"},
        {"input": "What is the largest planet?", "expected": "Jupiter"},
        {"input": "Who invented the telephone?", "expected": "Unknown"}  # Should fail
    ]

    # Run evaluation
    result = await evaluator.evaluate(test_cases, evaluation_id="demo-basic")

    # Print results
    print(f"\n📊 Evaluation Results:")
    print(f"  Tests: {result.total_tests}")
    print(f"  Passed: {result.passed_tests}")
    print(f"  Failed: {result.failed_tests}")
    print(f"  Accuracy: {result.accuracy:.2%}")
    print(f"  Avg Latency: {result.avg_latency_ms:.2f}ms")

    print(f"\n📈 Metric Details:")
    for metric_name, stats in result.aggregated_metrics.items():
        print(f"  {metric_name}:")
        for stat, value in stats.items():
            print(f"    {stat}: {value:.2f}")

    return result


async def demo_benchmark_suite():
    """Demo 2: Using benchmark suites."""
    print("\n" + "=" * 60)
    print("Demo 2: Benchmark Suites")
    print("=" * 60)

    agent = SimpleQAAgent()
    evaluator = Evaluator(agent, metrics=[AccuracyMetric()])

    # Use quick benchmark suite
    suite = BenchmarkSuite.quick()

    print(f"\n📦 Running '{suite.suite_name}' benchmark suite")
    print(f"  Benchmarks: {len(suite.benchmarks)}")

    test_cases = await suite.generate_all_test_cases()
    print(f"  Test cases: {len(test_cases)}")

    # Run evaluation (limiting to first 10 for demo)
    result = await evaluator.evaluate(test_cases[:10])

    print(f"\n📊 Results:")
    print(f"  Accuracy: {result.accuracy:.2%}")
    print(f"  Success Rate: {result.success_rate:.2%}")

    return result


async def demo_regression_detection():
    """Demo 3: Detecting performance regressions."""
    print("\n" + "=" * 60)
    print("Demo 3: Regression Detection")
    print("=" * 60)

    agent = SimpleQAAgent()
    evaluator = Evaluator(agent, metrics=[AccuracyMetric(), QualityMetrics()])

    test_cases = [
        {"input": "What is the capital of France?", "expected": "Paris"},
        {"input": "What is 2+2?", "expected": "4"},
    ]

    # Baseline evaluation
    print("\n📊 Running baseline evaluation...")
    baseline = await evaluator.evaluate(test_cases, evaluation_id="baseline")
    print(f"  Baseline Accuracy: {baseline.accuracy:.2%}")

    # Create regression detector
    detector = RegressionDetector(baseline=baseline)

    # Simulate degraded agent (wrong answers)
    degraded_agent = SimpleQAAgent(knowledge_base={
        "capital of france": "London",  # Wrong!
        "2+2": "5",  # Wrong!
    })

    # Evaluate degraded version
    print("\n📊 Running evaluation on degraded agent...")
    degraded_evaluator = Evaluator(degraded_agent, metrics=[AccuracyMetric(), QualityMetrics()])
    current = await degraded_evaluator.evaluate(test_cases, evaluation_id="current")
    print(f"  Current Accuracy: {current.accuracy:.2%}")

    # Detect regressions
    regressions = detector.detect(current)

    if regressions:
        print(f"\n🚨 Detected {len(regressions)} regression(s):")
        for reg in regressions:
            print(f"  - {reg.metric_name}:")
            print(f"      Baseline: {reg.baseline_value:.2f}")
            print(f"      Current: {reg.current_value:.2f}")
            print(f"      Degradation: {reg.degradation_percent:.1f}%")
            print(f"      Severity: {reg.severity.value}")
    else:
        print("\n✅ No regressions detected!")

    return detector


async def demo_session_recording():
    """Demo 4: Recording and replaying sessions."""
    print("\n" + "=" * 60)
    print("Demo 4: Session Recording & Replay")
    print("=" * 60)

    # Create recorder
    recorder = SessionRecorder()

    # Wrap agent for automatic recording
    agent_v1 = SimpleQAAgent()
    wrapped = recorder.wrap(agent_v1)

    print("\n📝 Recording session...")
    # Use wrapped agent (automatically recorded)
    await wrapped.process(
        Message(role="user", content="What is the capital of France?"),
        session_id="demo-session"
    )
    await wrapped.process(
        Message(role="user", content="What is 2+2?"),
        session_id="demo-session"
    )

    # Finalize recording
    recording = await recorder.finalize_session("demo-session")
    print(f"  Recorded {recording.interaction_count} interactions")
    print(f"  Total latency: {recording.total_latency_ms:.2f}ms")

    # Replay with different agent (A/B testing)
    print("\n🔄 Replaying session with different agent...")
    agent_v2 = SimpleQAAgent(knowledge_base={
        "capital of france": "Paris is the capital",  # Different response
        "2+2": "Four (4)",  # Different format
    })

    replay = SessionReplay()
    results_v1 = await replay.replay(recording, agent_v1, session_id="replay-v1")
    results_v2 = await replay.replay(recording, agent_v2, session_id="replay-v2")

    print(f"  V1 errors: {results_v1['error_count']}")
    print(f"  V2 errors: {results_v2['error_count']}")

    # Compare
    comparison = await replay.compare(results_v1, results_v2)
    print(f"\n📊 Comparison:")
    print(f"  Latency diff: {comparison['latency_diff_ms']:.2f}ms ({comparison['latency_diff_percent']:.1f}%)")
    print(f"  Output differences: {len(comparison['output_differences'])}")

    return recorder


async def demo_extreme_scale():
    """Demo 5: Extreme-scale benchmarks for endless."""
    print("\n" + "=" * 60)
    print("Demo 5: Extreme-Scale Benchmarks (Preview)")
    print("=" * 60)

    print("\n🔬 Extreme-Scale Test Lengths:")
    print("  - 1M tokens")
    print("  - 10M tokens")
    print("  - 25M tokens (endless scale!)")

    print("\n📊 Test Methodology:")
    print("  - Needle-in-haystack at massive scale")
    print("  - Compression quality measurement")
    print("  - Information retention across context")
    print("  - Quality degradation curves")

    print("\n💡 Use Case: endless project")
    print("  Validates agent performance at 25M+ token contexts")
    print("  Measures compression ratios (100x-1000x)")
    print("  Ensures retrieval accuracy at unprecedented scale")

    # Show how to use (without actually running at scale)
    print("\n📝 Example Usage:")
    print("  from agenkit.evaluation import BenchmarkSuite")
    print("  suite = BenchmarkSuite.extreme_scale()")
    print("  # Tests at 1M, 10M, 25M tokens")
    print("  # With compression quality and retrieval accuracy metrics")


async def main():
    """Run all demos."""
    print("\n🚀 Agenkit Evaluation Framework Demo")
    print("=" * 60)

    # Run demos
    await demo_basic_evaluation()
    await demo_benchmark_suite()
    await demo_regression_detection()
    await demo_session_recording()
    await demo_extreme_scale()

    print("\n" + "=" * 60)
    print("✅ Demo Complete!")
    print("=" * 60)
    print("\n💡 Key Takeaways:")
    print("  1. Evaluator measures agent quality with custom metrics")
    print("  2. Benchmark suites provide standard test sets")
    print("  3. Regression detector catches quality degradation")
    print("  4. Session recording enables replay and A/B testing")
    print("  5. Extreme-scale benchmarks validate 25M+ token performance")
    print("\n📚 See agenkit/evaluation/README.md for full documentation")


if __name__ == "__main__":
    asyncio.run(main())
