"""
Customer Support Bot Backend

FastAPI application providing customer support with ticket tracking,
conversation history, and escalation management through AG-UI protocol.
"""

import logging
from contextlib import asynccontextmanager

from agent import CustomerSupportAgent
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

# Global support agent and adapter
support_agent = None
adapter = None
formatter = WebSocketMessageFormat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize support agent and adapter on startup."""
    global support_agent, adapter  # noqa: PLW0603

    logger.info("Starting Customer Support Bot backend...")

    # Create support agent
    support_agent = CustomerSupportAgent(name="SupportBot")

    # Create AG-UI adapter
    adapter = AGUIAdapter(
        support_agent,
        agent_name="SupportBot",
        chunk_size=15,
    )

    logger.info("Customer Support Bot backend ready!")
    yield

    logger.info("Shutting down Customer Support Bot backend...")


# Create FastAPI app
app = FastAPI(
    title="Customer Support Bot Backend",
    description="AG-UI backend for customer support with context tracking",
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
    stats = support_agent.get_statistics() if support_agent else {}
    return {
        "status": "healthy",
        "agent": support_agent.name if support_agent else None,
        "statistics": stats,
    }


@app.get("/tickets")
async def list_tickets():
    """List all support tickets."""
    if not support_agent:
        return {"tickets": []}

    tickets = [
        {
            "ticket_id": ticket.ticket_id,
            "customer_id": ticket.customer_id,
            "issue_type": ticket.issue_type,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_at": ticket.created_at.isoformat(),
            "message_count": len(ticket.messages),
            "escalated": ticket.escalated,
        }
        for ticket in support_agent._tickets.values()
    ]

    return {"tickets": tickets}


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get specific ticket details."""
    if not support_agent:
        return {"error": "Support agent not initialized"}

    ticket = support_agent.get_ticket(ticket_id)
    if not ticket:
        return {"error": "Ticket not found"}

    return {
        "ticket_id": ticket.ticket_id,
        "customer_id": ticket.customer_id,
        "issue_type": ticket.issue_type,
        "priority": ticket.priority,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat(),
        "messages": ticket.messages,
        "escalated": ticket.escalated,
        "resolution": ticket.resolution,
    }


@app.get("/statistics")
async def get_statistics():
    """Get support statistics."""
    if not support_agent:
        return {"statistics": {}}

    return {"statistics": support_agent.get_statistics()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for customer support chat.

    Maintains conversation history, tracks tickets,
    and provides context-aware support through AG-UI protocol.
    """
    await websocket.accept()
    client_id = id(websocket)
    customer_id = f"customer_{client_id}"
    logger.info(f"Customer {customer_id} connected")

    try:
        # Send initial metadata
        metadata_event = {
            "event_type": "metadata",
            "data": {
                "agent_name": "SupportBot",
                "capabilities": support_agent.capabilities,
                "customer_id": customer_id,
                "support_info": {
                    "hours": "24/7 automated support, human agents Mon-Fri 9AM-5PM PST",
                    "average_response_time": "< 5 minutes",
                    "escalation_available": True,
                },
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
                logger.info(f"Customer {customer_id}: {user_content}")

                # Create user message with customer context
                user_message = Message(
                    role="user",
                    content=user_content,
                    metadata={
                        "customer_id": customer_id,
                        "client_id": str(client_id),
                    },
                )

                # Stream response
                async for event in adapter.stream_events(user_message, emit_metadata=False):
                    formatted = formatter.format_event(event)
                    await websocket.send_text(formatted)

                logger.info(f"Response sent to customer {customer_id}")

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                logger.warning(f"Unknown message type from customer {customer_id}: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"Customer {customer_id} disconnected")
    except Exception as e:
        logger.error(f"Error with customer {customer_id}: {e}", exc_info=True)
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
