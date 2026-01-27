"""
FastAPI Backend for HITL Approval Example

Provides WebSocket endpoint for AG-UI protocol with bidirectional
human-in-the-loop approval workflow.
"""

import logging
from contextlib import asynccontextmanager

from agent import TradingAgent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agenkit.protocols.agui_simple.events import InterruptResponse
from agenkit.protocols.agui_simple.hitl import AGUIHumanInLoopAdapter
from agenkit.protocols.agui_simple.transports.websocket import WebSocketMessageFormat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting HITL Approval Backend")
    logger.info("WebSocket endpoint: ws://localhost:8000/ws")
    yield
    logger.info("Shutting down HITL Approval Backend")


# Create FastAPI app
app = FastAPI(
    title="AG-UI HITL Approval Example",
    description="Financial trading agent with human-in-the-loop approval workflow",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create agent and adapter
trading_agent = TradingAgent()
adapter = AGUIHumanInLoopAdapter(
    trading_agent,
    agent_name="TradingAgent",
    bidirectional=True,  # Enable bidirectional HITL
    approval_threshold=0.8,  # Trades below 80% confidence require approval
    timeout=300.0,  # 5 minute timeout for user decisions
)

# Message formatter
formatter = WebSocketMessageFormat()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return JSONResponse(
        {
            "name": "AG-UI HITL Approval Example",
            "version": "1.0.0",
            "endpoints": {
                "websocket": "/ws",
                "health": "/health",
            },
            "agent": {
                "name": trading_agent.name,
                "capabilities": trading_agent.capabilities,
            },
            "hitl": {
                "enabled": True,
                "mode": "bidirectional",
                "approval_threshold": 0.8,
                "timeout": 300.0,
            },
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "agent": trading_agent.name})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for AG-UI protocol.

    Handles:
    - Connection management
    - Message streaming from agent
    - Interrupt event emission (for approval requests)
    - Interrupt response handling (from user decisions)
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted from {websocket.client}")

    try:
        # Send metadata on connect
        from agenkit import Message

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
                message_type = message_dict.get("type", "message")

                if message_type == "interrupt_response":
                    # Handle interrupt response
                    interrupt_response = InterruptResponse(
                        interrupt_id=message_dict["interrupt_id"],
                        action=message_dict["action"],
                        response=message_dict.get("response"),
                        context=message_dict.get("context", {}),
                    )
                    logger.info(
                        f"Received interrupt response: {interrupt_response.action} "
                        f"for interrupt {interrupt_response.interrupt_id}"
                    )
                    await adapter.handle_interrupt_response(interrupt_response)

                else:
                    # Regular user message - stream agent response
                    message_content = message_dict.get("message", message_dict.get("content", ""))
                    user_message = Message(role="user", content=message_content)

                    logger.info(f"Processing message: {message_content}")

                    # Stream events from agent
                    async for event in adapter.stream_events(user_message, emit_metadata=False):
                        formatted = formatter.format_event(event)
                        await websocket.send_text(formatted)

                        # Log special events
                        event_type = event.__class__.__name__
                        if event_type == "Interrupt":
                            logger.info(
                                f"Emitted interrupt: {event.interrupt_id} - {event.reason}"
                            )
                        elif event_type == "TextMessageComplete":
                            approval_status = event.metadata.get("approval_status")
                            if approval_status:
                                logger.info(f"Message completed with status: {approval_status}")

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                # Send error event
                error_message = {
                    "event_type": "error",
                    "error_code": "processing_error",
                    "error_message": str(e),
                }
                await websocket.send_text(formatter.format_event_dict(error_message))

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
