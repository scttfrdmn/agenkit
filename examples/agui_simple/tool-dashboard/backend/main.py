"""
Tool Dashboard Backend Server

FastAPI application that serves the ResearchAgent with tool execution
visualization through AG-UI protocol.
"""

import logging
from contextlib import asynccontextmanager

from agent import ResearchAgent
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

# Global agent and adapter
research_agent = None
adapter = None
formatter = WebSocketMessageFormat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent and adapter on startup."""
    global research_agent, adapter  # noqa: PLW0603

    logger.info("Starting Tool Dashboard backend...")

    # Create agent
    research_agent = ResearchAgent(name="ResearchAssistant")

    # Create AG-UI adapter with small chunks for smooth streaming
    adapter = AGUIAdapter(
        research_agent,
        agent_name="ResearchAssistant",
        chunk_size=15,  # Slightly larger chunks than chat for faster tool results
    )

    logger.info("Tool Dashboard backend ready!")
    yield

    logger.info("Shutting down Tool Dashboard backend...")


# Create FastAPI app
app = FastAPI(
    title="Tool Dashboard Backend",
    description="AG-UI backend for tool execution visualization",
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
        "agent": research_agent.name if research_agent else None,
        "capabilities": research_agent.capabilities if research_agent else [],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for AG-UI communication.

    Streams tool execution events in real-time:
    - metadata: Agent capabilities and info
    - text_message_start: Begin response
    - text_message_chunk: Stream response chunks
    - text_message_complete: Complete response with tool metadata
    """
    await websocket.accept()
    client_id = id(websocket)
    logger.info(f"Client {client_id} connected")

    try:
        # Send initial metadata
        metadata_event = {
            "event_type": "metadata",
            "data": {
                "agent_name": "ResearchAssistant",
                "capabilities": research_agent.capabilities,
                "available_tools": [
                    {
                        "name": "web_search",
                        "description": "Search the web for information",
                    },
                    {
                        "name": "calculator",
                        "description": "Perform mathematical calculations",
                    },
                    {
                        "name": "get_weather",
                        "description": "Get weather information",
                    },
                    {
                        "name": "query_database",
                        "description": "Query database records",
                    },
                ],
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

                # Stream response with tool execution
                async for event in adapter.stream_events(user_message, emit_metadata=False):
                    formatted = formatter.format_event(event)
                    await websocket.send_text(formatted)

                logger.info(f"Response streamed to client {client_id}")

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
