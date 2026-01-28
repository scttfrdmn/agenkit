"""Production-ready agent with load balancing, health checks, and enhanced retry.

This example demonstrates how to build a production agent system with:
- Load balancing across multiple backend agents
- Health monitoring with Kubernetes-style probes
- Enhanced retry with jitter and backpressure detection
- Prometheus metrics export

Perfect for 30-hour autonomous agent deployments.
"""

import asyncio
import logging
from datetime import datetime

from agenkit.core import Agent, Message
from agenkit.infrastructure import (
    EnhancedRetryConfig,
    EnhancedRetryDecorator,
    HealthCheckConfig,
    HealthChecker,
    LoadBalancer,
    LoadBalancerConfig,
    LoadBalancingStrategy,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SimulatedAgent(Agent):
    """Simulated agent for testing production infrastructure."""

    def __init__(self, name: str, failure_rate: float = 0.0) -> None:
        self._name = name
        self._failure_rate = failure_rate
        self._request_count = 0

    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[str]:
        return ["text_generation", "reasoning"]

    async def process(self, message: Message) -> Message:
        """Process message with simulated work and occasional failures."""
        self._request_count += 1

        # Simulate processing time
        await asyncio.sleep(0.1)

        # Simulate occasional failures for testing retry
        import random

        if random.random() < self._failure_rate:
            raise RuntimeError(f"{self._name}: Simulated transient error")

        return Message(
            role="agent",
            content=f"{self._name} processed: {message.content}",
            metadata={
                "agent": self._name,
                "request_count": self._request_count,
                "timestamp": datetime.now().isoformat(),
            },
        )


async def main() -> None:
    """Run production agent system demonstration."""
    logger.info("Starting production agent system...")

    # 1. Create backend agents with varying failure rates
    backend1 = SimulatedAgent("agent-1", failure_rate=0.1)
    backend2 = SimulatedAgent("agent-2", failure_rate=0.05)
    backend3 = SimulatedAgent("agent-3", failure_rate=0.15)

    # 2. Wrap each backend with enhanced retry
    retry_config = EnhancedRetryConfig(
        max_attempts=3,
        initial_backoff_ms=100,
        max_backoff_ms=5000,
        backoff_multiplier=2.0,
        jitter_type="full",
        enable_backpressure=True,
        backpressure_threshold=0.3,
        backpressure_window=10,
    )

    retry_backend1 = EnhancedRetryDecorator(backend1, retry_config)
    retry_backend2 = EnhancedRetryDecorator(backend2, retry_config)
    retry_backend3 = EnhancedRetryDecorator(backend3, retry_config)

    # 3. Create load balancer with health checking
    lb_config = LoadBalancerConfig(
        strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
        health_check_enabled=True,
        health_check_interval_ms=5000,
        health_check_timeout_ms=2000,
        max_retries_per_backend=2,
    )

    load_balancer = LoadBalancer(
        agents=[retry_backend1, retry_backend2, retry_backend3],
        config=lb_config,
    )

    # 4. Set up health checker for the load balancer
    health_config = HealthCheckConfig(
        liveness_enabled=True,
        liveness_interval_ms=10000,
        liveness_failure_threshold=3,
        readiness_enabled=True,
        readiness_interval_ms=5000,
        readiness_failure_threshold=2,
        startup_enabled=True,
        startup_timeout_ms=30000,
        startup_failure_threshold=5,
    )

    health_checker = HealthChecker(load_balancer, health_config)
    health_checker.start()

    # Wait for startup to complete
    logger.info("Waiting for startup checks...")
    await asyncio.sleep(2)

    if not health_checker.is_healthy():
        logger.error("System failed startup checks")
        return

    logger.info("System is healthy and ready!")

    # 5. Process requests through the production system
    requests = [
        Message(role="user", content=f"Request {i}") for i in range(20)
    ]

    successful = 0
    failed = 0

    for i, request in enumerate(requests):
        try:
            response = await load_balancer.process(request)
            logger.info(f"Request {i}: SUCCESS - {response.content}")
            successful += 1
        except Exception as e:
            logger.error(f"Request {i}: FAILED - {e}")
            failed += 1

        # Brief pause between requests
        await asyncio.sleep(0.2)

    # 6. Export metrics
    logger.info("\n" + "=" * 60)
    logger.info("FINAL METRICS")
    logger.info("=" * 60)

    # Load balancer metrics
    lb_metrics = load_balancer.get_metrics()
    logger.info(f"\nLoad Balancer:")
    logger.info(f"  Total requests: {lb_metrics.total_requests}")
    logger.info(f"  Successful: {lb_metrics.successful_requests}")
    logger.info(f"  Failed: {lb_metrics.failed_requests}")
    logger.info(
        f"  Success rate: {lb_metrics.successful_requests / max(lb_metrics.total_requests, 1) * 100:.1f}%"
    )

    # Backend distribution
    logger.info(f"\nBackend Distribution:")
    for backend_id, count in lb_metrics.backend_request_counts.items():
        logger.info(f"  {backend_id}: {count} requests")

    # Retry metrics for each backend
    logger.info(f"\nRetry Metrics:")
    for i, backend in enumerate(
        [retry_backend1, retry_backend2, retry_backend3], 1
    ):
        metrics = backend.get_metrics()
        logger.info(f"  Agent {i}:")
        logger.info(f"    Total attempts: {metrics.total_attempts}")
        logger.info(f"    Successful on first: {metrics.successful_first_attempt}")
        logger.info(f"    Successful on retry: {metrics.successful_on_retry}")
        logger.info(f"    Failed after retries: {metrics.failed_after_retries}")
        logger.info(f"    Total retries: {metrics.total_retries}")
        if metrics.backpressure_detected > 0:
            logger.info(
                f"    Backpressure detected: {metrics.backpressure_detected} times"
            )

    # Health metrics
    health_metrics = health_checker.get_metrics()
    logger.info(f"\nHealth Checks:")
    for probe_type, count in health_metrics.total_checks.items():
        success = health_metrics.successful_checks.get(probe_type, 0)
        failed = health_metrics.failed_checks.get(probe_type, 0)
        logger.info(
            f"  {probe_type}: {success}/{count} passed ({failed} failed)"
        )

    # Export Prometheus metrics
    logger.info(f"\nPrometheus Metrics:")
    logger.info("=" * 60)
    prometheus_metrics = health_checker.export_prometheus_metrics()
    logger.info(prometheus_metrics)

    # Stop health checker
    health_checker.stop()
    logger.info("\nProduction agent system stopped.")


if __name__ == "__main__":
    asyncio.run(main())
