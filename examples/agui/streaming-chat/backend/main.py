"""
FastAPI Backend for Streaming Chat Example

Provides WebSocket endpoint for AG-UI protocol with real-time
token-by-token streaming of agent responses.
"""

import logging
from contextlib import asynccontextmanager

from agent import ChatAgent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agenkit import Message
from agenkit.protocols.agui.adapter import AGUIAdapter
from agenkit.protocols.agui.transports.websocket import WebSocketMessageFormat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Streaming Chat Backend")
    logger.info("WebSocket endpoint: ws://localhost:8000/ws")
    yield
    logger.info("Shutting down Streaming Chat Backend")


# Create FastAPI app
app = FastAPI(
    title="AG-UI Streaming Chat Example",
    description="Simple conversational agent demonstrating real-time streaming",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create agent and adapter
chat_agent = ChatAgent(name="StreamingAssistant")
adapter = AGUIAdapter(
    chat_agent,
    agent_name="StreamingAssistant",
    chunk_size=10,  # Small chunks for smooth streaming effect
)

# Message formatter
formatter = WebSocketMessageFormat()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return JSONResponse(
        {
            "name": "AG-UI Streaming Chat Example",
            "version": "1.0.0",
            "endpoints": {
                "websocket": "/ws",
                "health": "/health",
            },
            "agent": {
                "name": chat_agent.name,
                "capabilities": chat_agent.capabilities,
            },
            "streaming": {
                "enabled": True,
                "chunk_size": 10,
                "protocol": "AG-UI",
            },
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "agent": chat_agent.name})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for AG-UI protocol.

    Handles:
    - Connection management
    - Real-time message streaming from agent
    - Token-by-token response display
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted from {websocket.client}")

    try:
        # Send metadata on connect
        metadata_message = Message(role="system", content="")
        async for event in adapter.stream_events(metadata_message, emit_metadata=True):
            if event.__class__.__name__ == "MetadataEvent":
                formatted = formatter.format_event(event)
                await websocket.send_text(formatted)
                logger.info("Sent metadata event")
                break

        # Message loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received: {data[:100]}...")

            try:
                message_dict = formatter.parse_message(data)
                message_content = message_dict.get("message", message_dict.get("content", ""))

                if not message_content.strip():
                    logger.warning("Received empty message")
                    continue

                user_message = Message(role="user", content=message_content)
                logger.info(f"Processing message: {message_content}")

                # Stream events from agent
                event_count = 0
                async for event in adapter.stream_events(user_message, emit_metadata=False):
                    formatted = formatter.format_event(event)
                    await websocket.send_text(formatted)
                    event_count += 1

                logger.info(f"Streamed {event_count} events for response")

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                # Send error event
                error_event = {
                    "event_type": "error",
                    "error_code": "processing_error",
                    "error_message": str(e),
                    "recoverable": True,
                }
                await websocket.send_text(formatter.format_event_dict(error_event))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=True,
        log_level="info",
    )
