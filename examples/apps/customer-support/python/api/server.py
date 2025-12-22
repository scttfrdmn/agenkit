"""FastAPI server with health checks and observability."""

import logging
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agenkit.adapters.python import RemoteAgent
from agenkit.interfaces import Message

from ..agents import FAQAgent, RouterAgent
from ..config import Settings, get_settings
from ..middleware import create_middleware_stack

logger = logging.getLogger(__name__)


# Request/Response models
class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    user_id: str = "anonymous"
    metadata: dict[str, Any] = {}


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str
    route: str
    confidence: float
    source: str
    metadata: dict[str, Any] = {}


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        settings: Application settings (uses environment if None)

    Returns:
        Configured FastAPI app
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Customer Support API",
        description="Production customer support system with multi-agent routing",
        version="1.0.0",
    )

    # Initialize agents
    router = RouterAgent(settings.anthropic_api_key)
    faq_agent = FAQAgent(settings.anthropic_api_key)

    # Wrap with middleware
    faq_with_middleware = create_middleware_stack(faq_agent, settings, agent_type="faq")

    # Initialize Go specialist worker (RemoteAgent)
    specialist_agent = RemoteAgent(name="specialist", endpoint=settings.go_worker_endpoint, timeout=settings.timeout_rag)

    specialist_with_middleware = create_middleware_stack(specialist_agent, settings, agent_type="rag")

    logger.info("All agents initialized with middleware")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Basic health check."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "customer-support-api",
        }

    @app.get("/ready")
    async def readiness_check():
        """
        Readiness check - verify dependencies.

        Checks:
        - Go worker connectivity
        - Configuration valid
        """
        checks = {
            "config": True,
            "go_worker": False,
            "anthropic": bool(settings.anthropic_api_key),
        }

        # Try to ping Go worker
        try:
            test_msg = Message(role="user", content="health_check", metadata={"type": "health_check"})
            await specialist_agent.process(test_msg)
            checks["go_worker"] = True
        except Exception as e:
            logger.warning(f"Go worker health check failed: {e}")

        all_ready = all(checks.values())

        return JSONResponse(
            status_code=200 if all_ready else 503,
            content={
                "status": "ready" if all_ready else "not_ready",
                "checks": checks,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    @app.get("/metrics")
    async def metrics():
        """
        Prometheus metrics endpoint.

        Returns:
            Metrics in Prometheus format
        """
        # In production, use prometheus_client library
        return {
            "requests_total": 0,
            "requests_faq": 0,
            "requests_specialist": 0,
            "requests_escalation": 0,
        }

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """
        Process customer support chat message.

        Args:
            request: Chat request with message and user_id

        Returns:
            Chat response with answer and routing info
        """
        try:
            # Create message
            user_message = Message(
                role="user", content=request.message, metadata={**request.metadata, "user_id": request.user_id}
            )

            # Step 1: Route the message
            routing_result = await router.process(user_message)
            route = routing_result.metadata["route"]
            confidence = routing_result.metadata["confidence"]

            logger.info(f"Routed to {route} with confidence {confidence}")

            # Step 2: Process with appropriate agent
            if route == "faq":
                agent = faq_with_middleware
            elif route == "specialist":
                agent = specialist_with_middleware
            else:  # escalation
                return ChatResponse(
                    response="Your request has been escalated to our support team. You'll receive a response within 24 hours.",
                    route="escalation",
                    confidence=confidence,
                    source="escalation",
                    metadata={"escalated": True},
                )

            # Process with selected agent
            response = await agent.process(user_message)

            return ChatResponse(
                response=str(response.content),
                route=route,
                confidence=confidence,
                source=response.metadata.get("source", "unknown"),
                metadata=response.metadata,
            )

        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error processing request: {e!s}")

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler."""
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug else "An error occurred",
            },
        )

    return app
