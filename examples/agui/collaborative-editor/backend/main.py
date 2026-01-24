"""
Collaborative Document Editor Backend

FastAPI application that manages shared document state and coordinates
multiple clients with AI writing assistance through AG-UI protocol.
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from agent import DocumentEditorAgent
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

# Global state
editor_agent = None
adapter = None
formatter = WebSocketMessageFormat()

# Document state management
documents = {}  # document_id -> document_content
active_connections = {}  # client_id -> websocket
client_documents = {}  # client_id -> document_id


class DocumentManager:
    """Manages shared document state and broadcasts changes."""

    def __init__(self):
        self.documents = {}
        self.document_locks = {}
        self.edit_history = {}

    def get_document(self, document_id: str) -> str:
        """Get document content."""
        if document_id not in self.documents:
            self.documents[document_id] = ""
            self.document_locks[document_id] = asyncio.Lock()
            self.edit_history[document_id] = []

        return self.documents[document_id]

    async def update_document(self, document_id: str, content: str, client_id: str) -> dict:
        """Update document content and record edit."""
        async with self.document_locks.get(document_id, asyncio.Lock()):
            old_content = self.documents.get(document_id, "")
            self.documents[document_id] = content

            # Record edit
            edit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": client_id,
                "content_length": len(content),
                "diff_length": len(content) - len(old_content),
            }

            if document_id not in self.edit_history:
                self.edit_history[document_id] = []

            self.edit_history[document_id].append(edit_record)

            # Keep last 50 edits
            self.edit_history[document_id] = self.edit_history[document_id][-50:]

            return edit_record

    def get_edit_history(self, document_id: str) -> list[dict]:
        """Get edit history for document."""
        return self.edit_history.get(document_id, [])

    def get_active_documents(self) -> list[str]:
        """Get list of active document IDs."""
        return list(self.documents.keys())


# Initialize document manager
doc_manager = DocumentManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent and adapter on startup."""
    global editor_agent, adapter  # noqa: PLW0603

    logger.info("Starting Collaborative Editor backend...")

    # Create agent
    editor_agent = DocumentEditorAgent(name="EditorAssistant")

    # Create AG-UI adapter
    adapter = AGUIAdapter(
        editor_agent,
        agent_name="EditorAssistant",
        chunk_size=20,  # Moderate chunk size for suggestions
    )

    logger.info("Collaborative Editor backend ready!")
    yield

    logger.info("Shutting down Collaborative Editor backend...")


# Create FastAPI app
app = FastAPI(
    title="Collaborative Editor Backend",
    description="AG-UI backend for collaborative document editing with AI assistance",
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
        "agent": editor_agent.name if editor_agent else None,
        "active_connections": len(active_connections),
        "active_documents": len(doc_manager.get_active_documents()),
    }


@app.get("/documents")
async def list_documents():
    """List all active documents."""
    return {
        "documents": [
            {
                "id": doc_id,
                "length": len(doc_manager.get_document(doc_id)),
                "edits": len(doc_manager.get_edit_history(doc_id)),
            }
            for doc_id in doc_manager.get_active_documents()
        ]
    }


async def broadcast_document_update(
    document_id: str, content: str, exclude_client: str | None = None
):
    """Broadcast document update to all clients editing the same document."""
    update_message = {
        "type": "document_update",
        "document_id": document_id,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Send to all clients editing this document
    for client_id, websocket in active_connections.items():
        if client_documents.get(client_id) == document_id and client_id != exclude_client:
            try:
                await websocket.send_json(update_message)
            except Exception as e:
                logger.error(f"Failed to broadcast to client {client_id}: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for collaborative editing with AI assistance.

    Handles:
    - Document state synchronization
    - Real-time change broadcasting
    - AI writing assistance requests
    - Multi-client coordination
    """
    await websocket.accept()
    client_id = str(uuid.uuid4())
    active_connections[client_id] = websocket
    logger.info(f"Client {client_id} connected")

    try:
        # Send initial metadata
        metadata_event = {
            "event_type": "metadata",
            "data": {
                "agent_name": "EditorAssistant",
                "capabilities": editor_agent.capabilities,
                "client_id": client_id,
                "protocol": "AG-UI",
                "version": "1.0",
            },
        }
        await websocket.send_text(formatter.format_event(metadata_event))

        # Process messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "join_document":
                # Client joins a document
                document_id = data.get("document_id", "default")
                client_documents[client_id] = document_id

                # Send current document content
                content = doc_manager.get_document(document_id)
                await websocket.send_json(
                    {
                        "type": "document_state",
                        "document_id": document_id,
                        "content": content,
                        "edit_history": doc_manager.get_edit_history(document_id)[-10:],
                    }
                )

                logger.info(f"Client {client_id} joined document {document_id}")

            elif message_type == "document_edit":
                # Client edited document
                document_id = data.get("document_id")
                content = data.get("content", "")
                cursor_position = data.get("cursor_position", 0)

                if document_id:
                    # Update document
                    await doc_manager.update_document(document_id, content, client_id)

                    # Broadcast to other clients
                    await broadcast_document_update(document_id, content, exclude_client=client_id)

                    logger.info(
                        f"Client {client_id} edited document {document_id} "
                        f"({len(content)} chars, cursor at {cursor_position})"
                    )

            elif message_type == "ai_assistance":
                # Client requests AI assistance
                document_id = data.get("document_id")
                command = data.get("command", "")
                selection = data.get("selection", "")
                cursor_position = data.get("cursor_position", 0)

                if document_id:
                    document_content = doc_manager.get_document(document_id)

                    # Create message for agent
                    user_message = Message(
                        role="user",
                        content=command,
                        metadata={
                            "document_content": document_content,
                            "selection": selection,
                            "cursor_position": cursor_position,
                            "client_id": client_id,
                            "document_id": document_id,
                        },
                    )

                    # Stream AI assistance
                    async for event in adapter.stream_events(user_message, emit_metadata=False):
                        formatted = formatter.format_event(event)
                        await websocket.send_text(formatted)

                    logger.info(f"AI assistance for client {client_id}: {command}")

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error with client {client_id}: {e}", exc_info=True)
    finally:
        # Cleanup
        active_connections.pop(client_id, None)
        client_documents.pop(client_id, None)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104
        port=8000,
        log_level="info",
    )
