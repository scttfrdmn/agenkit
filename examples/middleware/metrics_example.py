"""
Metrics Middleware Example

This example demonstrates WHY and HOW to use metrics middleware for observability,
debugging, capacity planning, and SLA tracking.

WHY USE METRICS MIDDLEWARE?
---------------------------
1. Observability: Understand system behavior in production
2. Debugging: Quickly identify bottlenecks and performance issues
3. Capacity Planning: Know when to scale based on real usage patterns
4. SLA Tracking: Ensure you're meeting latency and reliability targets
5. Anomaly Detection: Catch unusual patterns before they become incidents
6. Cost Attribution: Understand which operations are expensive

WHEN TO USE:
- Production systems (always!)
- Load testing and benchmarking
- Debugging performance issues
- Before and after optimization work
- Multi-tenant systems (per-tenant metrics)
- Microservices architectures (per-service metrics)

WHEN NOT TO USE:
- Early prototyping (adds cognitive overhead)
- Single-use scripts
- When latency overhead is absolutely critical (though it's minimal)

TRADE-OFFS:
- Small overhead (~1-2% latency) vs critical visibility
- Memory usage (metrics storage) vs historical data
- Metrics collection cost vs debugging time saved
- False sense of security if metrics aren't monitored
"""

import asyncio
import random
from agenkit.interfaces import Agent, Message
from agenkit.middleware import MetricsDecorator


# Example agent: Simulates an LLM API with variable latency
class LLMAgent(Agent):
    """Simulates an LLM API call with realistic latency patterns."""

    def __init__(self, name: str = "llm", mean_latency: float = 0.5,
                 error_rate: float = 0.0):
        """
        Args:
            name: Agent identifier
            mean_latency: Average response time in seconds
            error_rate: Probability of failure (0.0 to 1.0)
        """
        self._name = name
        self._mean_latency = mean_latency
        self._error_rate = error_rate

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["text_generation"]

    async def process(self, message: Message) -> Message:
        """Simulate LLM processing with variable latency."""
        # Simulate realistic latency distribution (log-normal)
        latency = random.lognormvariate(
            self._mean_latency,
            0.3  # Standard deviation
        )
        await asyncio.sleep(latency)

        # Simulate occasional failures
        if random.random() < self._error_rate:
            raise Exception("LLM API Error: Rate limit exceeded (429)")

        return Message(
            role="agent",
            content=f"Response from {self._name}",
            metadata={"model": "gpt-4", "tokens": 150}
        )


async def example_basic_metrics():
    """Example 1: Basic metrics collection for observability."""
    print("\n=== Example 1: Basic Metrics Collection ===")
    print("Use case: Monitor LLM API latency and error rates\n")

    # Create agent and wrap with metrics
    agent = LLMAgent(name="gpt-4", mean_latency=0.1, error_rate=0.1)
    monitored_agent = MetricsDecorator(agent)

    # Simulate production traffic
    print("Simulating 20 API calls...")
    for i in range(20):
        try:
            await monitored_agent.process(
                Message(role="user", content=f"Request {i+1}")
            )
        except Exception:
            pass  # Expected - some will fail

    # Analyze metrics
    metrics = monitored_agent.get_metrics()
    print(f"\n📊 Metrics Report:")
    print(f"   Total Requests:   {metrics.total_requests}")
    print(f"   Successful:       {metrics.success_requests}")
    print(f"   Failed:           {metrics.error_requests}")
    print(f"   Error Rate:       {metrics.error_rate():.1%}")
    print(f"   Avg Latency:      {metrics.average_latency():.3f}s")
    print(f"   Min Latency:      {metrics.min_latency:.3f}s")
    print(f"   Max Latency:      {metrics.max_latency:.3f}s")
    print(f"   In Flight:        {metrics.in_flight_requests}")

    print("\n💡 Insight: Track these metrics over time to detect:")
    print("   - Gradual latency increases (capacity issues)")
    print("   - Error rate spikes (service degradation)")
    print("   - Unusual traffic patterns (potential attacks)")


async def example_performance_comparison():
    """Example 2: Compare performance of different models/services."""
    print("\n=== Example 2: Performance Comparison ===")
    print("Use case: A/B test different LLM providers\n")

    # Create agents for different providers
    gpt4_agent = MetricsDecorator(
        LLMAgent(name="gpt-4", mean_latency=0.3, error_rate=0.02)
    )

    claude_agent = MetricsDecorator(
        LLMAgent(name="claude-3", mean_latency=0.2, error_rate=0.01)
    )

    gemini_agent = MetricsDecorator(
        LLMAgent(name="gemini-pro", mean_latency=0.15, error_rate=0.05)
    )

    # Run same workload on all agents
    agents = [
        ("GPT-4", gpt4_agent),
        ("Claude-3", claude_agent),
        ("Gemini Pro", gemini_agent)
    ]

    print("Running 10 requests on each provider...")
    for name, agent in agents:
        for i in range(10):
            try:
                await agent.process(
                    Message(role="user", content=f"Test query {i+1}")
                )
            except Exception:
                pass

    # Compare metrics
    print("\n📊 Performance Comparison:\n")
    print(f"{'Provider':<15} {'Latency (avg)':<15} {'Error Rate':<15} {'P99 Latency':<15}")
    print("-" * 60)

    for name, agent in agents:
        metrics = agent.get_metrics()
        print(f"{name:<15} {metrics.average_latency():<15.3f} "
              f"{metrics.error_rate():<15.1%} {metrics.max_latency:<15.3f}")

    print("\n💡 Decision Framework:")
    print("   - Gemini Pro: Fastest but highest error rate")
    print("   - Claude-3: Best balance of speed and reliability")
    print("   - GPT-4: Slowest but most reliable")
    print("   Choose based on your SLA requirements!")


async def example_capacity_planning():
    """Example 3: Use metrics for capacity planning."""
    print("\n=== Example 3: Capacity Planning ===")
    print("Use case: Determine when to scale your infrastructure\n")

    agent = LLMAgent(name="production-api", mean_latency=0.2)
    monitored_agent = MetricsDecorator(agent)

    # Simulate increasing load
    load_levels = [5, 10, 20, 30]  # Concurrent requests

    print("Testing system under increasing load...\n")

    for load in load_levels:
        # Reset metrics for each test
        await monitored_agent.get_metrics().reset()

        # Simulate concurrent requests
        tasks = [
            monitored_agent.process(Message(role="user", content=f"Req {i}"))
            for i in range(load)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        metrics = monitored_agent.get_metrics()

        print(f"Load: {load:2d} concurrent requests")
        print(f"  Avg Latency: {metrics.average_latency():.3f}s")
        print(f"  Max Latency: {metrics.max_latency:.3f}s (P99)")

        # Decision logic
        if metrics.average_latency() > 1.0:
            print(f"  ⚠️  WARNING: Latency exceeds SLA (>1s)")
            print(f"  📈 Action: Scale up before reaching {load} concurrent users")
            break
        else:
            print(f"  ✅ Within SLA")
        print()

    print("💡 Capacity Planning Insights:")
    print("   - Set up alerts for latency thresholds")
    print("   - Use metrics to trigger auto-scaling")
    print("   - Test with realistic load profiles")


async def example_anomaly_detection():
    """Example 4: Detect anomalies using metrics patterns."""
    print("\n=== Example 4: Anomaly Detection ===")
    print("Use case: Identify unusual system behavior early\n")

    agent = LLMAgent(name="monitored-service", mean_latency=0.1)
    monitored_agent = MetricsDecorator(agent)

    # Establish baseline
    print("Phase 1: Establishing baseline (normal operation)...")
    for i in range(20):
        await monitored_agent.process(
            Message(role="user", content=f"Normal request {i}")
        )

    baseline_metrics = monitored_agent.get_metrics().snapshot()
    baseline_latency = baseline_metrics.average_latency()
    baseline_error_rate = baseline_metrics.error_rate()

    print(f"Baseline established:")
    print(f"  Avg Latency: {baseline_latency:.3f}s")
    print(f"  Error Rate:  {baseline_error_rate:.1%}")

    # Simulate anomaly (degraded service)
    print("\nPhase 2: Simulating service degradation...")
    agent._mean_latency = 0.5  # 5x slower
    agent._error_rate = 0.2     # 20% errors

    await monitored_agent.get_metrics().reset()

    for i in range(20):
        try:
            await monitored_agent.process(
                Message(role="user", content=f"Degraded request {i}")
            )
        except Exception:
            pass

    current_metrics = monitored_agent.get_metrics()
    current_latency = current_metrics.average_latency()
    current_error_rate = current_metrics.error_rate()

    print(f"\nCurrent metrics:")
    print(f"  Avg Latency: {current_latency:.3f}s")
    print(f"  Error Rate:  {current_error_rate:.1%}")

    # Anomaly detection logic
    print("\n🔍 Anomaly Detection:")

    latency_increase = (current_latency - baseline_latency) / baseline_latency
    if latency_increase > 0.5:  # 50% increase
        print(f"  🚨 ALERT: Latency increased by {latency_increase:.1%}")
        print(f"     Action: Investigate backend services")

    error_increase = current_error_rate - baseline_error_rate
    if error_increase > 0.1:  # 10% increase
        print(f"  🚨 ALERT: Error rate increased by {error_increase:.1%}")
        print(f"     Action: Check service health, review recent deployments")

    print("\n💡 Anomaly Detection Best Practices:")
    print("   - Use moving averages to smooth out noise")
    print("   - Set thresholds based on historical data")
    print("   - Combine multiple signals (latency + errors)")
    print("   - Alert on trends, not just absolute values")


async def example_multi_agent_monitoring():
    """Example 5: Monitor complex multi-agent systems."""
    print("\n=== Example 5: Multi-Agent System Monitoring ===")
    print("Use case: Monitor a pipeline with multiple stages\n")

    # Create a pipeline of agents
    validator = MetricsDecorator(
        LLMAgent(name="validator", mean_latency=0.05)
    )

    processor = MetricsDecorator(
        LLMAgent(name="processor", mean_latency=0.2)
    )

    formatter = MetricsDecorator(
        LLMAgent(name="formatter", mean_latency=0.03)
    )

    # Run requests through the pipeline
    print("Processing 10 requests through 3-stage pipeline...")
    for i in range(10):
        try:
            msg = Message(role="user", content=f"Request {i}")
            msg = await validator.process(msg)
            msg = await processor.process(msg)
            msg = await formatter.process(msg)
        except Exception:
            pass

    # Analyze each stage
    print("\n📊 Pipeline Performance Analysis:\n")
    print(f"{'Stage':<15} {'Requests':<12} {'Avg Latency':<15} {'% of Total':<12}")
    print("-" * 60)

    total_latency = 0.0
    stages = [
        ("Validator", validator),
        ("Processor", processor),
        ("Formatter", formatter)
    ]

    for name, agent in stages:
        metrics = agent.get_metrics()
        total_latency += metrics.average_latency()

    for name, agent in stages:
        metrics = agent.get_metrics()
        pct = (metrics.average_latency() / total_latency) * 100
        print(f"{name:<15} {metrics.total_requests:<12} "
              f"{metrics.average_latency():<15.3f} {pct:<12.1f}%")

    print(f"\nTotal Pipeline Latency: {total_latency:.3f}s")

    print("\n💡 Optimization Strategy:")
    print("   1. Focus on the slowest stage (Processor = 71% of latency)")
    print("   2. Consider caching for repeated requests")
    print("   3. Parallelize independent stages when possible")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("METRICS MIDDLEWARE EXAMPLES")
    print("="*70)
    print("\nMetrics are the foundation of observable, reliable systems.")
    print("These examples show why and how to instrument your agents.\n")

    await example_basic_metrics()
    await example_performance_comparison()
    await example_capacity_planning()
    await example_anomaly_detection()
    await example_multi_agent_monitoring()

    print("\n" + "="*70)
    print("KEY TAKEAWAYS")
    print("="*70)
    print("""
1. ALWAYS instrument production agents - metrics pay for themselves
2. Track the 4 golden signals: Latency, Traffic, Errors, Saturation
3. Use metrics for:
   - Real-time monitoring and alerting
   - Capacity planning and scaling decisions
   - Performance optimization (measure before and after)
   - Cost attribution in multi-tenant systems
4. Set up alerts based on:
   - Absolute thresholds (e.g., latency > 1s)
   - Rate of change (e.g., error rate up 50%)
   - Statistical anomalies (e.g., > 3 standard deviations)
5. Export metrics to monitoring systems (Prometheus, Datadog, CloudWatch)
6. Remember: You can't optimize what you don't measure

REAL-WORLD TIPS:
- Metrics add ~1-2% overhead but save 100x in debugging time
- Use percentiles (P50, P95, P99) not just averages
- Tag metrics with context (user_id, model, region) for better insights
- Set up dashboards before you need them
- Correlate metrics across the stack (agent -> API -> database)
    """)


if __name__ == "__main__":
    asyncio.run(main())
