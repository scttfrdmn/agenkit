"""FastAPI server for code review bot."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from agenkit.interfaces import Message
from python.agents.orchestrator import ReviewOrchestrator
from python.config.settings import Settings

logger = logging.getLogger(__name__)


class ReviewRequest(BaseModel):
    """Code review request."""

    code: str
    language: Optional[str] = None
    review_type: str = "general"


class ReviewResponse(BaseModel):
    """Code review response."""

    report: str
    consensus_score: float
    num_reviews: int
    timestamp: str


def create_app(settings: Settings) -> FastAPI:
    """Create FastAPI application with all routes and dependencies."""
    app = FastAPI(
        title="Code Review Bot API",
        description="Multi-LLM code review with consensus",
        version="1.0.0",
    )

    # Initialize orchestrator
    orchestrator = ReviewOrchestrator(
        anthropic_key=settings.anthropic_api_key,
        openai_key=settings.openai_api_key,
        google_key=settings.google_api_key,
    )

    @app.get("/health")
    async def health_check():
        """Basic health check."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    @app.get("/ready")
    async def readiness_check():
        """Readiness check with dependency verification."""
        checks = {
            "config": True,
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
            "google": bool(settings.google_api_key),
            "github": bool(settings.github_token),
        }

        status = "ready" if all(checks.values()) else "not_ready"
        return {"status": status, "checks": checks, "timestamp": datetime.utcnow().isoformat()}

    @app.post("/review", response_model=ReviewResponse)
    async def review_code(request: ReviewRequest):
        """Conduct multi-LLM code review with consensus."""
        logger.info(f"Starting review for {len(request.code)} characters of code")

        try:
            # Create message for orchestrator
            message = Message(
                role="user",
                content=request.code,
                metadata={
                    "review_type": request.review_type,
                    "language": request.language,
                },
            )

            # Conduct review
            result = await orchestrator.process(message)

            return ReviewResponse(
                report=str(result.content),
                consensus_score=result.metadata.get("consensus_score", 0.0),
                num_reviews=result.metadata.get("num_reviews", 0),
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            logger.error(f"Review failed: {e}")
            raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")

    @app.post("/webhook/github")
    async def github_webhook(request: Request):
        """Handle GitHub PR webhook events."""
        # Get event type
        event_type = request.headers.get("X-GitHub-Event")

        if event_type != "pull_request":
            return {"status": "ignored", "reason": f"Event type {event_type} not supported"}

        # Parse payload
        payload = await request.json()
        action = payload.get("action")

        # Only handle opened and synchronize events
        if action not in ["opened", "synchronize"]:
            return {"status": "ignored", "reason": f"Action {action} not supported"}

        pr_number = payload["pull_request"]["number"]
        repo_full_name = payload["repository"]["full_name"]

        logger.info(f"Received PR event: {repo_full_name}#{pr_number} ({action})")

        # TODO: Fetch PR files, conduct review, post comment
        # This would integrate with GitHub API to:
        # 1. Fetch changed files
        # 2. Review each file
        # 3. Calculate consensus
        # 4. Post review comment

        return {
            "status": "accepted",
            "pr": pr_number,
            "repo": repo_full_name,
            "message": "Review queued",
        }

    return app


def main():
    """Run the server."""
    import uvicorn

    settings = Settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = create_app(settings)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.python_api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
