"""
Multimodal Agent Backend Server

FastAPI application that handles text, images, and file uploads,
processing them through the MultimodalAgent with AG-UI protocol.
"""

import logging
from contextlib import asynccontextmanager

from agent import MultimodalAgent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agenkit import Message
from agenkit.protocols.agui import AGUIAdapter
from agenkit.protocols.agui.transports import WebSocketMessageFormat

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global agent and adapter
multimodal_agent = None
adapter = None
formatter = WebSocketMessageFormat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent and adapter on startup."""
    global multimodal_agent, adapter  # noqa: PLW0603

    logger.info("Starting Multimodal Agent backend...")

    # Create agent
    multimodal_agent = MultimodalAgent(name="MultimodalAssistant")

    # Create AG-UI adapter
    adapter = AGUIAdapter(
        multimodal_agent,
        agent_name="MultimodalAssistant",
        chunk_size=15,
    )

    logger.info("Multimodal Agent backend ready!")
    yield

    logger.info("Shutting down Multimodal Agent backend...")


# Create FastAPI app
app = FastAPI(
    title="Multimodal Agent Backend",
    description="AG-UI backend for multimodal content processing",
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
        "agent": multimodal_agent.name if multimodal_agent else None,
        "capabilities": multimodal_agent.capabilities if multimodal_agent else [],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for multimodal content processing.

    Handles:
    - Text queries
    - Image uploads (base64 encoded)
    - File uploads (base64 encoded)
    - Combined text + media
    """
    await websocket.accept()
    client_id = id(websocket)
    logger.info(f"Client {client_id} connected")

    try:
        # Send initial metadata
        metadata_event = {
            "event_type": "metadata",
            "data": {
                "agent_name": "MultimodalAssistant",
                "capabilities": multimodal_agent.capabilities,
                "supported_formats": {
                    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
                    "documents": [".txt", ".md", ".pdf", ".doc", ".docx"],
                    "code": [".py", ".js", ".ts", ".go", ".rs", ".cpp", ".java"],
                    "data": [".json", ".csv", ".xml", ".yaml", ".yml"],
                },
                "max_file_size": 10 * 1024 * 1024,  # 10MB
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
                # Text-only message
                user_content = data.get("message", "")
                logger.info(f"Client {client_id}: Text query - {user_content[:50]}")

                user_message = Message(
                    role="user",
                    content=user_content,
                    metadata={"client_id": str(client_id)},
                )

                # Stream response
                async for event in adapter.stream_events(user_message, emit_metadata=False):
                    formatted = formatter.format_event(event)
                    await websocket.send_text(formatted)

            elif message_type == "image":
                # Image upload
                user_content = data.get("message", "Analyze this image")
                image_data = data.get("image_data")  # base64 encoded
                image_format = data.get("image_format", "unknown")
                image_size = data.get("image_size", 0)

                logger.info(
                    f"Client {client_id}: Image upload - {image_format} "
                    f"({image_size/1024:.1f}KB)"
                )

                user_message = Message(
                    role="user",
                    content=user_content,
                    metadata={
                        "client_id": str(client_id),
                        "image_data": image_data,
                        "image_format": image_format,
                        "image_size": image_size,
                    },
                )

                # Stream response
                async for event in adapter.stream_events(user_message, emit_metadata=False):
                    formatted = formatter.format_event(event)
                    await websocket.send_text(formatted)

            elif message_type == "file":
                # File upload
                user_content = data.get("message", "Analyze this file")
                file_data = data.get("file_data")  # base64 encoded
                file_name = data.get("file_name", "unknown")
                file_size = data.get("file_size", 0)
                file_type = data.get("file_type", "unknown")

                logger.info(
                    f"Client {client_id}: File upload - {file_name} " f"({file_size/1024:.1f}KB)"
                )

                user_message = Message(
                    role="user",
                    content=user_content,
                    metadata={
                        "client_id": str(client_id),
                        "file_data": file_data,
                        "file_name": file_name,
                        "file_size": file_size,
                        "file_type": file_type,
                    },
                )

                # Stream response
                async for event in adapter.stream_events(user_message, emit_metadata=False):
                    formatted = formatter.format_event(event)
                    await websocket.send_text(formatted)

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
