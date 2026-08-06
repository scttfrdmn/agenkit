"""Comprehensive example of production infrastructure for autonomous agents.

Demonstrates:
1. Load balancing across multiple agents
2. Health checks with liveness/readiness probes
3. Enhanced retry logic with jitter and budget awareness
4. Prometheus metrics export
5. Production-ready deployment patterns
"""

import asyncio

from agenkit.adapters.echo import EchoAgent
from agenkit.infrastructure import (
    EnhancedRetryConfig,
    EnhancedRetryDecorator,
    ErrorClass,
    HealthCheckConfig,
    HealthChecker,
    JitterType,
    LoadBalancer,
    LoadBalancerConfig,
    LoadBalancingStrategy,
)
from agenkit.interfaces import Message


async def basic_load_balancing_example():
    """Example 1: Basic load balancing across multiple agents."""
    print("\n=== Basic Load Balancing Example ===\n")

    # Create multiple agent backends
    agents = [
        EchoAgent("backend-1"),
        EchoAgent("backend-2"),
        EchoAgent("backend-3"),
    ]

    # Create load balancer with round-robin strategy
    balancer = LoadBalancer(
        agents,
        config=LoadBalancerConfig(
            strategy=LoadBalancingStrategy.ROUND_ROBIN,
            enable_failover=True,
        ),
    )

    # Process messages - they'll be distributed across backends
    for i in range(6):
        message = Message(role="user", content=f"Request {i + 1}")
        response = await balancer.process(message)
        print(f"Request {i + 1}: {response.content}")

    # Show backend statistics
    print("\nBackend Statistics:")
    for stats in balancer.get_backend_stats():
        print(f"  {stats['name']}: {stats['total_requests']} requests")

    print(f"\nLoad Balancer Metrics:")
    print(f"  Total requests: {balancer.metrics.total_requests}")
    print(f"  Successful: {balancer.metrics.successful_requests}")


async def weighted_load_balancing_example():
    """Example 2: Weighted load balancing for different backend capacities."""
    print("\n=== Weighted Load Balancing Example ===\n")

    agents = [
        EchoAgent("high-capacity"),
        EchoAgent("medium-capacity"),
        EchoAgent("low-capacity"),
    ]

    # Weight 3:2:1 means high-capacity gets 50% of traffic
    weights = [3, 2, 1]

    balancer = LoadBalancer(
        agents,
        weights=weights,
        config=LoadBalancerConfig(
            strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
        ),
    )

    # Send 12 requests to see distribution
    for i in range(12):
        message = Message(role="user", content=f"Request {i + 1}")
        await balancer.process(message)

    print("Request distribution (weights 3:2:1):")
    for stats in balancer.get_backend_stats():
        print(f"  {stats['name']}: {stats['total_requests']} requests")


async def least_connections_example():
    """Example 3: Least connections strategy for balanced load."""
    print("\n=== Least Connections Strategy Example ===\n")

    agents = [
        EchoAgent("agent-1"),
        EchoAgent("agent-2"),
        EchoAgent("agent-3"),
    ]

    balancer = LoadBalancer(
        agents,
        config=LoadBalancerConfig(
            strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
        ),
    )

    # Simulate concurrent requests
    async def send_request(i: int):
        message = Message(role="user", content=f"Concurrent request {i}")
        response = await balancer.process(message)
        return response

    # Send 10 concurrent requests
    tasks = [send_request(i) for i in range(10)]
    await asyncio.gather(*tasks)

    print("Request distribution (least connections):")
    for stats in balancer.get_backend_stats():
        print(f"  {stats['name']}: {stats['total_requests']} requests")


async def health_check_example():
    """Example 4: Health checks with liveness and readiness probes."""
    print("\n=== Health Check Example ===\n")

    agent = EchoAgent("monitored-agent")

    # Configure health checks
    health = HealthChecker(
        agent,
        config=HealthCheckConfig(
            liveness_enabled=True,
            readiness_enabled=True,
            liveness_interval=5.0,
            readiness_interval=3.0,
        ),
    )

    # Perform manual health checks
    liveness_result = await health.check_liveness()
    print(f"Liveness: {liveness_result.status.value}")
    print(f"  Message: {liveness_result.message}")
    print(f"  Duration: {liveness_result.duration_ms:.2f}ms")

    readiness_result = await health.check_readiness()
    print(f"\nReadiness: {readiness_result.status.value}")
    print(f"  Message: {readiness_result.message}")
    print(f"  Duration: {readiness_result.duration_ms:.2f}ms")

    # Start background health checks
    print("\nStarting background health checks...")
    await health.start()

    # Let it run for a bit
    await asyncio.sleep(10)

    # Export Prometheus metrics
    print("\nPrometheus Metrics:")
    print(health.export_prometheus_metrics())

    # Stop health checks
    await health.stop()


async def enhanced_retry_example():
    """Example 5: Enhanced retry with jitter and error classification."""
    print("\n=== Enhanced Retry Example ===\n")

    agent = EchoAgent("unreliable-agent")

    # Configure enhanced retry
    config = EnhancedRetryConfig(
        max_attempts=5,
        jitter_type=JitterType.FULL,
        enable_backpressure=True,
        enable_budget=False,  # Disabled for example
    )

    retry_agent = EnhancedRetryDecorator(agent, config)

    # Process messages with automatic retry
    message = Message(role="user", content="Test with retry")
    response = await retry_agent.process(message)
    print(f"Response: {response.content}")

    # Show retry metrics
    metrics = retry_agent.metrics
    print(f"\nRetry Metrics:")
    print(f"  Total attempts: {metrics.total_attempts}")
    print(f"  Successful on first try: {metrics.successful_first_attempt}")
    print(f"  Successful after retry: {metrics.successful_on_retry}")
    print(f"  Total jitter added: {metrics.total_jitter_added:.2f}s")


async def error_classification_example():
    """Example 6: Per-error-type retry strategies."""
    print("\n=== Error Classification Example ===\n")

    agent = EchoAgent("agent-with-errors")

    # Custom error classifier
    def classify_error(e: Exception) -> ErrorClass:
        error_str = str(e).lower()
        if "rate limit" in error_str:
            return ErrorClass.RATE_LIMIT
        elif "timeout" in error_str:
            return ErrorClass.TIMEOUT
        elif "500" in error_str:
            return ErrorClass.SERVER_ERROR
        return ErrorClass.UNKNOWN

    config = EnhancedRetryConfig(
        error_classifier=classify_error,
        jitter_type=JitterType.FULL,
    )

    retry_agent = EnhancedRetryDecorator(agent, config)

    # The agent will use different retry strategies based on error type
    message = Message(role="user", content="Test error classification")
    response = await retry_agent.process(message)

    print(f"Response: {response.content}")
    print(f"\nError class distribution:")
    for error_class, count in retry_agent.metrics.error_class_counts.items():
        print(f"  {error_class.value}: {count}")


async def production_deployment_example():
    """Example 7: Complete production deployment with all components."""
    print("\n=== Production Deployment Example ===\n")

    # Step 1: Create backend agents
    backends = [
        EchoAgent("prod-backend-1"),
        EchoAgent("prod-backend-2"),
        EchoAgent("prod-backend-3"),
    ]

    # Step 2: Wrap each backend with enhanced retry
    retry_config = EnhancedRetryConfig(
        max_attempts=3,
        jitter_type=JitterType.FULL,
        enable_backpressure=True,
    )

    retry_backends = [EnhancedRetryDecorator(agent, retry_config) for agent in backends]

    # Step 3: Add load balancer
    load_balancer = LoadBalancer(
        retry_backends,
        config=LoadBalancerConfig(
            strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
            health_check_interval=30.0,
            enable_failover=True,
        ),
    )

    # Step 4: Add health checks
    health_checker = HealthChecker(
        load_balancer,
        config=HealthCheckConfig(
            liveness_enabled=True,
            readiness_enabled=True,
            startup_enabled=True,
        ),
    )

    await health_checker.start()

    # Step 5: Process production traffic
    print("Processing production traffic...")

    tasks = []
    for i in range(20):
        message = Message(role="user", content=f"Production request {i + 1}")
        tasks.append(load_balancer.process(message))

    responses = await asyncio.gather(*tasks)

    print(f"\nProcessed {len(responses)} requests")
    print(f"Load balancer metrics:")
    print(f"  Successful: {load_balancer.metrics.successful_requests}")
    print(f"  Failed: {load_balancer.metrics.failed_requests}")
    print(f"  Failovers: {load_balancer.metrics.failover_attempts}")

    # Export health metrics
    print("\nHealth Status:")
    print(f"  Overall health: {'Healthy' if health_checker.is_healthy else 'Unhealthy'}")
    print(f"  Uptime: {health_checker.metrics.get_uptime():.1f}s")

    await health_checker.stop()


async def main():
    """Run all production infrastructure examples."""
    print("Agenkit Production Infrastructure Examples")
    print("=" * 50)

    await basic_load_balancing_example()
    await weighted_load_balancing_example()
    await least_connections_example()
    await health_check_example()
    await enhanced_retry_example()
    await error_classification_example()
    await production_deployment_example()

    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
