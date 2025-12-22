"""
Example production-ready Agenkit agent with full observability.

Features:
- HTTP server with health checks
- Redis caching
- Prometheus metrics
- OpenTelemetry tracing
- Structured logging
- Graceful shutdown
"""

import asyncio
import logging
import os
import signal
from typing import Optional

from agenkit import Agent, Message
from agenkit.middleware import CachingMiddleware, RetryMiddleware, TimeoutMiddleware
from agenkit.observability import MetricsMiddleware, TracingMiddleware
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from starlette.requests import Request
import uvicorn
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Custom metrics
REQUEST_COUNT = Counter("agent_requests_total", "Total agent requests", ["status"])
REQUEST_DURATION = Histogram("agent_request_duration_seconds", "Request duration")
ACTIVE_REQUESTS = Gauge("agent_active_requests", "Active requests")


class ProductionAgent(Agent):
    """Example production agent with business logic."""

    def __init__(self):
        self._name = "production-agent"
        logger.info(f"Initialized {self._name}")

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["text-processing", "analysis", "production"]

    async def process(self, message: Message) -> Message:
        """
        Process a message with business logic.

        In a real production agent, this would:
        - Call LLM APIs
        - Execute business logic
        - Access databases
        - Call external services
        """
        logger.info(f"Processing message: {message.content[:50]}...")

        # Simulate processing
        await asyncio.sleep(0.1)

        # Example response
        response_content = f"Processed: {message.content}"

        return Message(
            role="assistant",
            content=response_content,
            metadata={"agent": self._name, "processed_at": asyncio.get_event_loop().time()},
        )


async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for load balancers."""
    return JSONResponse({"status": "healthy", "service": "agenkit-agent", "version": "1.0.0"})


async def ready_check(request: Request) -> JSONResponse:
    """Readiness check endpoint for Kubernetes."""
    # Check dependencies (Redis, DB, etc.)
    try:
        redis_client = request.app.state.redis
        await redis_client.ping()
        return JSONResponse({"status": "ready"})
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse({"status": "not ready", "error": str(e)}, status_code=503)


async def process_endpoint(request: Request) -> JSONResponse:
    """Agent processing endpoint."""
    ACTIVE_REQUESTS.inc()
    try:
        # Parse request
        data = await request.json()
        message = Message(role=data.get("role", "user"), content=data["content"])

        # Process with agent
        with REQUEST_DURATION.time():
            agent = request.app.state.agent
            response = await agent.process(message)

        REQUEST_COUNT.labels(status="success").inc()

        return JSONResponse(
            {"role": response.role, "content": response.content, "metadata": response.metadata}
        )

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        REQUEST_COUNT.labels(status="error").inc()
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        ACTIVE_REQUESTS.dec()


async def startup(app: Starlette):
    """Application startup: initialize dependencies."""
    logger.info("Starting application...")

    # Initialize Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    app.state.redis = await redis.from_url(redis_url, decode_responses=True)
    logger.info(f"Connected to Redis: {redis_url}")

    # Create base agent
    base_agent = ProductionAgent()

    # Add middleware layers
    # 1. Timeout protection
    agent = TimeoutMiddleware(base_agent, timeout=30.0)

    # 2. Retry logic
    agent = RetryMiddleware(agent, max_retries=3, backoff_factor=2.0)

    # 3. Caching (using Redis)
    agent = CachingMiddleware(agent, redis_client=app.state.redis, ttl=3600)

    # 4. Observability
    agent = MetricsMiddleware(agent, prefix="agenkit_")
    agent = TracingMiddleware(agent, service_name="production-agent")

    app.state.agent = agent
    logger.info("Agent initialized with middleware")


async def shutdown(app: Starlette):
    """Application shutdown: cleanup resources."""
    logger.info("Shutting down application...")

    # Close Redis connection
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
        logger.info("Closed Redis connection")

    logger.info("Shutdown complete")


# Create Starlette application
app = Starlette(
    debug=False,
    routes=[
        Route("/health", health_check),
        Route("/ready", ready_check),
        Route("/process", process_endpoint, methods=["POST"]),
        Mount("/metrics", make_asgi_app()),  # Prometheus metrics
    ],
    on_startup=[startup],
    on_shutdown=[shutdown],
)


def handle_signal(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    raise KeyboardInterrupt


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))

    logger.info(f"Starting server on {host}:{port} with {workers} workers")

    # Run server
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
        access_log=True,
        server_header=False,  # Security: don't leak server info
        date_header=False,  # Security: don't leak server time
    )
