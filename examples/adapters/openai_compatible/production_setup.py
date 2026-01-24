#!/usr/bin/env python3
"""
Production Deployment Example

This example demonstrates production-ready patterns for deploying
OpenAI-compatible inference services with Agenkit:

1. Health checks and connection validation
2. Load balancing across multiple instances
3. Automatic failover and retry logic
4. Monitoring and observability
5. Docker Compose setup for local testing
6. Kubernetes deployment patterns (commented guides)

This is a complete, production-grade example you can adapt for your needs.

Run:
    uv run python examples/adapters/openai_compatible/production_setup.py
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any

from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """Configuration for a service endpoint."""

    name: str
    base_url: str
    model: str
    provider: str
    weight: int = 1  # For weighted load balancing
    healthy: bool = True
    consecutive_failures: int = 0


class ProductionLLMService:
    """
    Production-grade LLM service with health checks, failover, and monitoring.

    Features:
    - Health checking with automatic endpoint removal/addition
    - Round-robin load balancing with weights
    - Automatic failover to healthy endpoints
    - Retry logic with exponential backoff
    - Request/response logging for monitoring
    - Performance metrics tracking
    """

    def __init__(
        self,
        endpoints: list[ServiceEndpoint],
        health_check_interval: float = 30.0,
        max_retries: int = 3,
        failure_threshold: int = 3,
    ):
        """
        Initialize production service.

        Args:
            endpoints: List of service endpoints
            health_check_interval: Seconds between health checks
            max_retries: Maximum retry attempts for failed requests
            failure_threshold: Consecutive failures before marking unhealthy
        """
        self.endpoints = endpoints
        self.health_check_interval = health_check_interval
        self.max_retries = max_retries
        self.failure_threshold = failure_threshold
        self.current_index = 0
        self._health_check_task = None
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency": 0.0,
        }

    async def start(self) -> None:
        """Start the service and health checking."""
        logger.info("Starting production LLM service...")
        logger.info(f"Configured {len(self.endpoints)} endpoint(s)")

        # Start health checks
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        # Initial health check
        await self._check_all_endpoints()

    async def stop(self) -> None:
        """Stop the service and health checking."""
        logger.info("Stopping production LLM service...")
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    async def complete(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> Message:
        """
        Complete a request with automatic failover and retry.

        Args:
            messages: Conversation messages
            **kwargs: Additional LLM parameters

        Returns:
            Response message

        Raises:
            Exception: If all endpoints fail after retries
        """
        self.metrics["total_requests"] += 1

        # Try each endpoint with retries
        for attempt in range(self.max_retries):
            endpoint = self._get_next_endpoint()

            if not endpoint:
                logger.error("No healthy endpoints available!")
                raise Exception("No healthy endpoints available")

            try:
                logger.info(
                    f"Request attempt {attempt + 1}/{self.max_retries} "
                    f"using {endpoint.name} ({endpoint.base_url})"
                )

                llm = OpenAICompatibleLLM(
                    base_url=endpoint.base_url,
                    model=endpoint.model,
                    provider=endpoint.provider,
                    timeout=30.0,
                )

                import time

                start = time.perf_counter()
                response = await llm.complete(messages, **kwargs)
                duration = time.perf_counter() - start

                # Success - update metrics
                self.metrics["successful_requests"] += 1
                self.metrics["total_latency"] += duration
                endpoint.consecutive_failures = 0

                logger.info(
                    f"✅ Request succeeded in {duration:.2f}s "
                    f"(tokens: {response.metadata.get('usage', {}).get('total_tokens', 'N/A')})"
                )

                return response

            except Exception as e:
                logger.warning(f"❌ Request failed: {e}")
                endpoint.consecutive_failures += 1

                # Mark unhealthy if threshold exceeded
                if endpoint.consecutive_failures >= self.failure_threshold:
                    logger.error(
                        f"Endpoint {endpoint.name} marked unhealthy after "
                        f"{endpoint.consecutive_failures} consecutive failures"
                    )
                    endpoint.healthy = False

                # Wait before retry (exponential backoff)
                if attempt < self.max_retries - 1:
                    backoff = 2**attempt
                    logger.info(f"Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)

        # All retries exhausted
        self.metrics["failed_requests"] += 1
        raise Exception(f"All endpoints failed after {self.max_retries} retries")

    def _get_next_endpoint(self) -> ServiceEndpoint | None:
        """Get next healthy endpoint using weighted round-robin."""
        healthy = [e for e in self.endpoints if e.healthy]

        if not healthy:
            return None

        # Weighted round-robin (simple implementation)
        # In production, consider more sophisticated algorithms
        total_weight = sum(e.weight for e in healthy)
        choice = random.randint(1, total_weight)

        cumulative = 0
        for endpoint in healthy:
            cumulative += endpoint.weight
            if choice <= cumulative:
                return endpoint

        return healthy[0]  # Fallback

    async def _health_check_loop(self) -> None:
        """Continuously check endpoint health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_endpoints()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _check_all_endpoints(self) -> None:
        """Check health of all endpoints."""
        logger.info("Running health checks...")

        for endpoint in self.endpoints:
            is_healthy = await self._check_endpoint(endpoint)

            if is_healthy and not endpoint.healthy:
                logger.info(f"✅ Endpoint {endpoint.name} is now healthy")
                endpoint.healthy = True
                endpoint.consecutive_failures = 0
            elif not is_healthy and endpoint.healthy:
                logger.warning(f"⚠️  Endpoint {endpoint.name} health check failed")

    async def _check_endpoint(self, endpoint: ServiceEndpoint) -> bool:
        """Check if an endpoint is healthy."""
        try:
            llm = OpenAICompatibleLLM(
                base_url=endpoint.base_url,
                model=endpoint.model,
                provider=endpoint.provider,
                timeout=10.0,
            )

            # Simple health check with minimal request
            test_msg = [Message(role="user", content="Hi")]
            await llm.complete(test_msg, max_tokens=5)

            return True

        except Exception as e:
            logger.debug(f"Health check failed for {endpoint.name}: {e}")
            return False

    def get_metrics(self) -> dict[str, Any]:
        """Get service metrics."""
        avg_latency = (
            self.metrics["total_latency"] / self.metrics["successful_requests"]
            if self.metrics["successful_requests"] > 0
            else 0.0
        )

        return {
            **self.metrics,
            "average_latency": avg_latency,
            "success_rate": (
                self.metrics["successful_requests"] / self.metrics["total_requests"]
                if self.metrics["total_requests"] > 0
                else 0.0
            ),
            "healthy_endpoints": sum(1 for e in self.endpoints if e.healthy),
            "total_endpoints": len(self.endpoints),
        }


async def basic_usage_example() -> None:
    """Basic usage with production service."""
    print("=" * 80)
    print(" " * 25 + "Basic Usage Example")
    print("=" * 80)

    # Configure endpoints
    endpoints = [
        ServiceEndpoint(
            name="vllm-1",
            base_url="http://localhost:8000/v1",
            model="meta-llama/Llama-2-7b-chat-hf",
            provider="vllm",
            weight=2,  # Higher weight = more traffic
        ),
        ServiceEndpoint(
            name="vllm-2",
            base_url="http://localhost:8001/v1",
            model="meta-llama/Llama-2-7b-chat-hf",
            provider="vllm",
            weight=1,
        ),
    ]

    service = ProductionLLMService(
        endpoints=endpoints,
        health_check_interval=30.0,
        max_retries=3,
        failure_threshold=3,
    )

    await service.start()

    try:
        # Make requests
        messages = [Message(role="user", content="What is Kubernetes?")]

        print("\n📤 Sending request...")
        response = await service.complete(messages)
        print(f"📥 Response: {response.content[:100]}...")

        # Show metrics
        metrics = service.get_metrics()
        print("\n📊 Metrics:")
        print(f"  • Total requests: {metrics['total_requests']}")
        print(f"  • Success rate: {metrics['success_rate']:.1%}")
        print(f"  • Average latency: {metrics['average_latency']:.2f}s")
        print(f"  • Healthy endpoints: {metrics['healthy_endpoints']}/{metrics['total_endpoints']}")

    finally:
        await service.stop()


async def docker_compose_example() -> None:
    """Show Docker Compose configuration."""
    print("\n\n" + "=" * 80)
    print(" " * 22 + "Docker Compose Configuration")
    print("=" * 80)

    print("\n📦 docker-compose.yml for multi-instance vLLM:")

    compose_yaml = """
version: '3.8'

services:
  vllm-1:
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    environment:
      - CUDA_VISIBLE_DEVICES=0
    command: --model meta-llama/Llama-2-7b-chat-hf --dtype float16
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  vllm-2:
    image: vllm/vllm-openai:latest
    ports:
      - "8001:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    environment:
      - CUDA_VISIBLE_DEVICES=1
    command: --model meta-llama/Llama-2-7b-chat-hf --dtype float16
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Nginx load balancer (optional)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - vllm-1
      - vllm-2
"""

    print(compose_yaml)

    print("\n🚀 Start with: docker-compose up -d")
    print("📊 Monitor with: docker-compose logs -f")
    print("🛑 Stop with: docker-compose down")


async def kubernetes_example() -> None:
    """Show Kubernetes deployment pattern."""
    print("\n\n" + "=" * 80)
    print(" " * 23 + "Kubernetes Deployment Pattern")
    print("=" * 80)

    print("\n☸️  deployment.yaml for vLLM on Kubernetes:")

    k8s_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-inference
  labels:
    app: vllm
spec:
  replicas: 3  # Auto-scaling possible
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
          - --model
          - meta-llama/Llama-2-7b-chat-hf
          - --dtype
          - float16
        ports:
        - containerPort: 8000
        resources:
          requests:
            nvidia.com/gpu: 1
            memory: "16Gi"
            cpu: "4"
          limits:
            nvidia.com/gpu: 1
            memory: "32Gi"
            cpu: "8"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 180
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
"""

    print(k8s_yaml)

    print("\n🚀 Deploy with: kubectl apply -f deployment.yaml")
    print("📊 Check status: kubectl get pods -l app=vllm")
    print("🔍 View logs: kubectl logs -l app=vllm --tail=100")


async def monitoring_example() -> None:
    """Show monitoring and observability patterns."""
    print("\n\n" + "=" * 80)
    print(" " * 23 + "Monitoring and Observability")
    print("=" * 80)

    print("\n📊 Key metrics to track in production:")

    print("""
1. Request Metrics:
   • Total requests per second (RPS)
   • Success rate (%)
   • P50, P95, P99 latencies
   • Token throughput (tokens/second)

2. Service Health:
   • Healthy endpoints count
   • Failed health checks
   • Circuit breaker states
   • Connection pool utilization

3. Model Performance:
   • GPU utilization (%)
   • Memory usage (MB)
   • Queue depth
   • Time to first token (TTFT)

4. Error Tracking:
   • Error rate by type
   • Timeout frequency
   • OOM events
   • Failover occurrences

Integration examples:

# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

request_counter = Counter('llm_requests_total', 'Total LLM requests')
request_latency = Histogram('llm_request_duration_seconds', 'Request duration')
healthy_endpoints = Gauge('llm_healthy_endpoints', 'Number of healthy endpoints')

# OpenTelemetry tracing
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("llm_request"):
    response = await llm.complete(messages)
""")


async def main() -> None:
    """Run all production examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Production Deployment Examples" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")

    # Show examples (most don't need running services)
    await docker_compose_example()
    await kubernetes_example()
    await monitoring_example()

    print("\n\n" + "=" * 80)
    print("📚 Production Deployment Guide Complete")
    print("=" * 80)

    print("\n💡 Key production patterns:")
    print("  • Health checks prevent routing to failed endpoints")
    print("  • Load balancing distributes requests efficiently")
    print("  • Automatic retry with backoff handles transient failures")
    print("  • Monitoring enables proactive issue detection")

    print("\n🔒 Security considerations:")
    print("  • Use API keys for authentication (api_key parameter)")
    print("  • Enable TLS/SSL for all connections")
    print("  • Implement rate limiting per client")
    print("  • Monitor for unusual request patterns")

    print("\n📈 Scaling strategies:")
    print("  • Horizontal: Add more service replicas")
    print("  • Vertical: Use larger GPU instances")
    print("  • Batch: Group requests for higher throughput")
    print("  • Cache: Cache common responses")

    print("\n📖 Next steps:")
    print("  • Adapt examples to your infrastructure")
    print("  • Set up monitoring and alerting")
    print("  • Test failover scenarios")
    print("  • Implement gradual rollout")

    # Optionally run live example if services are available
    print("\n\n💻 To run live example with actual services:")
    print("  1. Start multiple vLLM instances (see docker-compose example)")
    print("  2. Update endpoint URLs in this script")
    print("  3. Uncomment the line below:")
    # await basic_usage_example()


if __name__ == "__main__":
    asyncio.run(main())
