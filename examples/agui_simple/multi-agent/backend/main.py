"""
Multi-Agent Coordination Backend

FastAPI application that coordinates multiple specialized agents
through the CoordinatorAgent with AG-UI protocol.
"""

import logging
from contextlib import asynccontextmanager

from agent import CoordinatorAgent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agenkit import Message
from agenkit.protocols.agui_simple import AGUIAdapter
from agenkit.protocols.agui_simple.transports import WebSocketMessageFormat

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global coordinator and adapter
coordinator = None
adapter = None
formatter = WebSocketMessageFormat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize coordinator and adapter on startup."""
    global coordinator, adapter  # noqa: PLW0603

    logger.info("Starting Multi-Agent Coordination backend...")

    # Create coordinator agent
    coordinator = CoordinatorAgent(name="TaskCoordinator")

    # Create AG-UI adapter
    adapter = AGUIAdapter(
        coordinator,
        agent_name="TaskCoordinator",
        chunk_size=20,
    )

    logger.info("Multi-Agent Coordination backend ready!")
    logger.info(f"Available specialized agents: {', '.join(coordinator._agents.keys())}")
    yield

    logger.info("Shutting down Multi-Agent Coordination backend...")


# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Coordination Backend",
    description="AG-UI backend for multi-agent task coordination",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "coordinator": coordinator.name if coordinator else None,
        "specialized_agents": (list(coordinator._agents.keys()) if coordinator else []),
        "capabilities": coordinator.capabilities if coordinator else [],
    }


@app.get("/agents")
async def list_agents():
    """List available specialized agents."""
    if not coordinator:
        return {"agents": []}

    agents_info = []
    for agent_name, agent in coordinator._agents.items():
        agents_info.append(
            {
                "name": agent_name,
                "full_name": agent.name,
                "capabilities": agent.capabilities,
            }
        )

    return {"coordinator": coordinator.name, "specialized_agents": agents_info}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for multi-agent coordination.

    Receives user queries, coordinates specialized agents,
    and streams aggregated results via AG-UI protocol.
    """
    await websocket.accept()
    client_id = id(websocket)
    logger.info(f"Client {client_id} connected")

    try:
        # Send initial metadata
        metadata_event = {
            "event_type": "metadata",
            "data": {
                "agent_name": "TaskCoordinator",
                "capabilities": coordinator.capabilities,
                "specialized_agents": [
                    {
                        "name": agent_name,
                        "capabilities": agent.capabilities,
                    }
                    for agent_name, agent in coordinator._agents.items()
                ],
                "coordination_strategy": "parallel_execution",
                "protocol": "AG-UI",
                "version": "1.0",
            },
        }
        await websocket.send_text(formatter.format_event(metadata_event))

        # Process messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "message":
                user_content = data.get("message", "")
                logger.info(f"Client {client_id}: {user_content}")

                # Create user message
                user_message = Message(
                    role="user",
                    content=user_content,
                    metadata={"client_id": str(client_id)},
                )

                # Stream coordinated response
                async for event in adapter.stream_events(user_message, emit_metadata=False):
                    formatted = formatter.format_event(event)
                    await websocket.send_text(formatted)

                logger.info(f"Coordination complete for client {client_id}")

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error with client {client_id}: {e}", exc_info=True)
        try:
            error_event = {
                "event_type": "error",
                "error": {
                    "type": "server_error",
                    "message": str(e),
                },
            }
            await websocket.send_text(formatter.format_event(error_event))
        except Exception:
            pass  # Connection likely closed


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104
        port=8000,
        log_level="info",
    )
