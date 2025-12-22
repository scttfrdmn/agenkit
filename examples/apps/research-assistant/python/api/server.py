"""FastAPI server with WebSocket streaming."""

import logging
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from agenkit.adapters.python import RemoteAgent
from agenkit.interfaces import Message

from ..agents.planner import PlannerAgent
from ..agents.writer import WriterAgent
from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class ResearchRequest(BaseModel):
    query: str
    user_id: str = "anonymous"


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()

    app = FastAPI(title="Research Assistant API", version="1.0.0")

    # Initialize agents
    planner = PlannerAgent(settings.openai_api_key)
    writer = WriterAgent(settings.openai_api_key)
    scraper = RemoteAgent(
        "scraper", settings.go_scraper_endpoint, timeout=settings.timeout_scraping
    )

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    @app.get("/ready")
    async def readiness_check():
        checks = {"config": True, "openai": bool(settings.openai_api_key), "scraper": False}

        try:
            test_msg = Message(
                role="user", content="health_check", metadata={"type": "health_check"}
            )
            await scraper.process(test_msg)
            checks["scraper"] = True
        except Exception as e:
            logger.warning(f"Scraper health check failed: {e}")

        return {"status": "ready" if all(checks.values()) else "not_ready", "checks": checks}

    @app.post("/research")
    async def research(request: ResearchRequest):
        """Simple synchronous research endpoint."""
        try:
            # Create plan
            plan_msg = Message(role="user", content=request.query)
            plan = await planner.process(plan_msg)

            # Simulate findings (in production, execute plan steps)
            findings = [f"Finding 1 for: {request.query}", f"Finding 2 for: {request.query}"]

            # Write report
            report_msg = Message(
                role="user", content="", metadata={"findings": findings, "query": request.query}
            )
            report = await writer.process(report_msg)

            return {
                "query": request.query,
                "plan": str(plan.content),
                "report": str(report.content),
                "status": "completed",
            }
        except Exception as e:
            logger.error(f"Research error: {e}", exc_info=True)
            return {"error": str(e), "status": "failed"}

    @app.websocket("/ws/research")
    async def websocket_research(websocket: WebSocket):
        """WebSocket endpoint for streaming research progress."""
        await websocket.accept()

        try:
            data = await websocket.receive_json()
            query = data.get("query", "")

            # Stream progress updates
            await websocket.send_json({"type": "status", "message": "Planning research..."})

            plan_msg = Message(role="user", content=query)
            plan = await planner.process(plan_msg)

            await websocket.send_json({"type": "plan", "content": str(plan.content)})

            # Simulate research steps
            await websocket.send_json({"type": "status", "message": "Gathering information..."})
            findings = [f"Finding for: {query}"]

            await websocket.send_json({"type": "status", "message": "Writing report..."})
            report_msg = Message(
                role="user", content="", metadata={"findings": findings, "query": query}
            )
            report = await writer.process(report_msg)

            await websocket.send_json({"type": "report", "content": str(report.content)})
            await websocket.send_json({"type": "completed"})

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.send_json({"type": "error", "message": str(e)})

    return app
