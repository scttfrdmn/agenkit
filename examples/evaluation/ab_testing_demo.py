"""
A/B Testing Framework Demo

Demonstrates:
1. Basic A/B testing with statistical significance
2. Multiple metrics comparison (accuracy, latency)
3. Different statistical tests (t-test, Mann-Whitney U)
4. Sample size calculation
5. Experiment result interpretation
"""

import asyncio
import random

from agenkit.evaluation.ab_testing import (
    ABTest,
    SignificanceLevel,
    StatisticalTestType,
    calculate_sample_size,
)
from agenkit.interfaces import Message


class PromptVariantAgent:
    """Agent with configurable prompt strategy."""

    def __init__(self, name, accuracy_rate=0.7, avg_latency_ms=100):
        """
        Initialize agent with simulated performance characteristics.

        Args:
            name: Agent name
            accuracy_rate: Simulated accuracy (0.0 to 1.0)
            avg_latency_ms: Simulated average latency in milliseconds
        """
        self.name = name
        self.accuracy_rate = accuracy_rate
        self.avg_latency_ms = avg_latency_ms

    async def process(self, message: Message, session_id=None):
        """Process message with simulated latency and accuracy."""
        # Simulate latency with variation
        latency = self.avg_latency_ms + random.gauss(0, 10)
        await asyncio.sleep(max(0, latency) / 1000)

        # Simulate accuracy
        is_correct = random.random() < self.accuracy_rate
        content = "correct answer" if is_correct else "incorrect answer"

        return Message(role="assistant", content=content)


async def demo_basic_ab_test():
    """Demo 1: Basic A/B testing."""
    print("=" * 70)
    print("Demo 1: Basic A/B Test - Prompt Optimization")
    print("=" * 70)

    # Set seed for reproducibility
    random.seed(42)

    # Create control and treatment agents
    control_agent = PromptVariantAgent(
        name="baseline_prompt", accuracy_rate=0.75, avg_latency_ms=120
    )

    treatment_agent = PromptVariantAgent(
        name="optimized_prompt", accuracy_rate=0.85, avg_latency_ms=110
    )

    # Create A/B test
    ab_test = ABTest(
        name="prompt_optimization_experiment",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
        significance_level=SignificanceLevel.P_0_05,
    )

    # Generate test cases
    test_cases = [{"input": f"Test question {i}", "expected": "correct answer"} for i in range(50)]

    print("\n🔬 Running A/B experiment...")
    print(f"  Sample size: {len(test_cases)} per variant")
    print("  Metrics: accuracy")
    print("  Significance level: α = 0.05 (95% confidence)")

    # Run experiment
    results = await ab_test.run(test_cases, sample_size=50, shuffle=False)

    # Analyze results
    accuracy_result = results["accuracy"]

    print("\n📊 Results:")
    print("  Control (baseline_prompt):")
    print(f"    Mean accuracy: {accuracy_result.control_variant.mean:.3f}")
    print(f"    Std dev: {accuracy_result.control_variant.std:.3f}")

    print("\n  Treatment (optimized_prompt):")
    print(f"    Mean accuracy: {accuracy_result.treatment_variant.mean:.3f}")
    print(f"    Std dev: {accuracy_result.treatment_variant.std:.3f}")

    print("\n  Statistical Analysis:")
    print(f"    p-value: {accuracy_result.p_value:.4f}")
    print(f"    Effect size (Cohen's d): {accuracy_result.effect_size:.2f}")
    print(f"    Confidence interval: {accuracy_result.confidence_interval}")
    print(f"    Is significant: {accuracy_result.is_significant}")

    if accuracy_result.is_significant:
        print(f"\n✅ Result: {accuracy_result.winner} wins!")
        print(f"   Improvement: {accuracy_result.improvement_percent:.1f}%")
    else:
        print("\n❌ Result: No statistically significant difference detected")

    return results


async def demo_multiple_metrics():
    """Demo 2: A/B testing with multiple metrics."""
    print("\n" + "=" * 70)
    print("Demo 2: Multi-Metric A/B Test - Speed vs Quality Trade-off")
    print("=" * 70)

    random.seed(42)

    # Fast but less accurate
    control_agent = PromptVariantAgent(name="fast_agent", accuracy_rate=0.70, avg_latency_ms=50)

    # Slower but more accurate
    treatment_agent = PromptVariantAgent(name="accurate_agent", accuracy_rate=0.85, avg_latency_ms=150)

    # Test both accuracy and latency
    ab_test = ABTest(
        name="speed_quality_tradeoff",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy", "latency_ms"],
        significance_level=SignificanceLevel.P_0_05,
    )

    test_cases = [{"input": f"Test {i}", "expected": "correct answer"} for i in range(40)]

    print("\n🔬 Running multi-metric experiment...")
    print("  Comparing: accuracy vs latency trade-off")
    print(f"  Sample size: {len(test_cases)} per variant")

    results = await ab_test.run(test_cases, sample_size=40, shuffle=False)

    # Analyze accuracy
    accuracy_result = results["accuracy"]
    print("\n📊 Accuracy Results:")
    print(f"  Control: {accuracy_result.control_variant.mean:.3f}")
    print(f"  Treatment: {accuracy_result.treatment_variant.mean:.3f}")
    print(f"  p-value: {accuracy_result.p_value:.4f}")
    print(f"  Significant: {accuracy_result.is_significant}")

    # Analyze latency
    latency_result = results["latency_ms"]
    print("\n⚡ Latency Results:")
    print(f"  Control: {latency_result.control_variant.mean:.1f}ms")
    print(f"  Treatment: {latency_result.treatment_variant.mean:.1f}ms")
    print(f"  p-value: {latency_result.p_value:.4f}")
    print(f"  Significant: {latency_result.is_significant}")

    # Overall assessment
    print("\n💡 Trade-off Analysis:")
    if accuracy_result.is_significant and accuracy_result.winner == "treatment":
        improvement = accuracy_result.improvement_percent
        latency_increase = (
            (latency_result.treatment_variant.mean - latency_result.control_variant.mean)
            / latency_result.control_variant.mean
            * 100
        )
        print(f"  Treatment is {improvement:.1f}% more accurate")
        print(f"  But {latency_increase:.1f}% slower")
        print("  Decision: Consider use case requirements")

    return results


async def demo_sample_size_calculation():
    """Demo 3: Sample size calculation."""
    print("\n" + "=" * 70)
    print("Demo 3: Sample Size Calculation")
    print("=" * 70)

    print("\n📏 Calculating required sample sizes...")

    # Scenario 1: Detect 5% improvement in accuracy
    baseline = 0.75
    min_effect = 0.05
    n1 = calculate_sample_size(
        baseline_mean=baseline,
        minimum_detectable_effect=min_effect,
        alpha=0.05,
        power=0.80,
        std_dev=0.15,
    )

    print("\nScenario 1: Detect 5% improvement")
    print(f"  Baseline accuracy: {baseline:.2%}")
    print(f"  Minimum detectable effect: {min_effect:.2%}")
    print(f"  Required sample size per variant: {n1}")

    # Scenario 2: Detect smaller 2% improvement
    min_effect_small = 0.02
    n2 = calculate_sample_size(
        baseline_mean=baseline,
        minimum_detectable_effect=min_effect_small,
        alpha=0.05,
        power=0.80,
        std_dev=0.15,
    )

    print("\nScenario 2: Detect 2% improvement (smaller effect)")
    print(f"  Baseline accuracy: {baseline:.2%}")
    print(f"  Minimum detectable effect: {min_effect_small:.2%}")
    print(f"  Required sample size per variant: {n2}")
    print(f"  📈 {(n2 / n1):.1f}x more samples needed for smaller effect")

    # Scenario 3: Higher power (95%)
    n3 = calculate_sample_size(
        baseline_mean=baseline,
        minimum_detectable_effect=min_effect,
        alpha=0.05,
        power=0.95,  # Higher power
        std_dev=0.15,
    )

    print("\nScenario 3: 95% power (more confident)")
    print(f"  Baseline accuracy: {baseline:.2%}")
    print(f"  Minimum detectable effect: {min_effect:.2%}")
    print("  Statistical power: 95%")
    print(f"  Required sample size per variant: {n3}")
    print(f"  📈 {(n3 / n1):.1f}x more samples for higher confidence")

    print("\n💡 Key Takeaways:")
    print("  • Smaller effects require more samples")
    print("  • Higher confidence requires more samples")
    print("  • Plan your sample size before running experiments")


async def demo_mann_whitney_test():
    """Demo 4: Non-parametric testing with Mann-Whitney U."""
    print("\n" + "=" * 70)
    print("Demo 4: Non-Parametric Testing (Mann-Whitney U)")
    print("=" * 70)

    random.seed(42)

    # Agents with non-normal distributions
    control_agent = PromptVariantAgent(name="control", accuracy_rate=0.65, avg_latency_ms=100)

    treatment_agent = PromptVariantAgent(name="treatment", accuracy_rate=0.80, avg_latency_ms=100)

    # Use Mann-Whitney U test (non-parametric)
    ab_test = ABTest(
        name="non_parametric_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
        test_type=StatisticalTestType.MANN_WHITNEY,  # Non-parametric
        significance_level=SignificanceLevel.P_0_05,
    )

    test_cases = [{"input": f"Test {i}", "expected": "correct answer"} for i in range(35)]

    print("\n🔬 Running experiment with Mann-Whitney U test...")
    print("  Use case: Non-normal distributions or small samples")
    print(f"  Sample size: {len(test_cases)} per variant")

    results = await ab_test.run(test_cases, sample_size=35, shuffle=False)

    accuracy_result = results["accuracy"]

    print("\n📊 Results:")
    print(f"  Test type: {accuracy_result.test_type.value}")
    print(f"  Control mean: {accuracy_result.control_variant.mean:.3f}")
    print(f"  Treatment mean: {accuracy_result.treatment_variant.mean:.3f}")
    print(f"  p-value: {accuracy_result.p_value:.4f}")
    print(f"  Effect size (rank-biserial): {accuracy_result.effect_size:.2f}")

    if accuracy_result.is_significant:
        print("\n✅ Result: Significant difference detected!")
        print(f"   Winner: {accuracy_result.winner}")
        print(f"   Improvement: {accuracy_result.improvement_percent:.1f}%")
    else:
        print("\n❌ No significant difference detected")

    print("\n💡 When to use Mann-Whitney U:")
    print("  • Non-normal distributions")
    print("  • Small sample sizes")
    print("  • Ordinal data")
    print("  • More robust to outliers than t-test")

    return results


async def demo_experiment_summary():
    """Demo 5: Complete experiment with summary."""
    print("\n" + "=" * 70)
    print("Demo 5: Complete Experiment with Summary")
    print("=" * 70)

    random.seed(42)

    # Test two different prompt strategies
    control_agent = PromptVariantAgent(name="zero_shot", accuracy_rate=0.70, avg_latency_ms=100)

    treatment_agent = PromptVariantAgent(name="few_shot", accuracy_rate=0.82, avg_latency_ms=120)

    ab_test = ABTest(
        name="zero_shot_vs_few_shot",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy", "latency_ms"],
    )

    test_cases = [{"input": f"Question {i}", "expected": "correct answer"} for i in range(45)]

    print("\n🔬 Experiment: Zero-shot vs Few-shot Prompting")
    results = await ab_test.run(test_cases, sample_size=45, shuffle=False)

    # Get full summary
    summary = ab_test.get_summary()

    print("\n📋 Experiment Summary:")
    print(f"  Name: {summary['experiment_name']}")
    print(f"  Variants: {summary['variants']['control']} vs {summary['variants']['treatment']}")
    print(f"  Metrics tested: {', '.join(summary['metrics'])}")

    print("\n📊 Detailed Results:")
    for metric_name, result_data in summary["results"].items():
        print(f"\n  Metric: {metric_name}")
        print(f"    Control: {result_data['control']['mean']:.3f}")
        print(f"    Treatment: {result_data['treatment']['mean']:.3f}")
        print(f"    p-value: {result_data['statistics']['p_value']:.4f}")
        print(f"    Significant: {result_data['statistics']['is_significant']}")

        if result_data["outcome"]["winner"]:
            print(f"    Winner: {result_data['outcome']['winner']}")
            print(f"    Improvement: {result_data['outcome']['improvement_percent']:.1f}%")

    return summary


async def main():
    """Run all demos."""
    print("\n" + "🧪" * 35)
    print("A/B TESTING FRAMEWORK DEMONSTRATION")
    print("🧪" * 35 + "\n")

    # Run demos
    await demo_basic_ab_test()
    await demo_multiple_metrics()
    await demo_sample_size_calculation()
    await demo_mann_whitney_test()
    await demo_experiment_summary()

    print("\n" + "=" * 70)
    print("🎉 All demos completed!")
    print("=" * 70)
    print("\n📚 Next steps:")
    print("  • Integrate A/B testing into your evaluation pipeline")
    print("  • Use sample size calculator to plan experiments")
    print("  • Compare different prompts, models, or strategies")
    print("  • Make data-driven decisions with statistical confidence")
    print()


if __name__ == "__main__":
    asyncio.run(main())
