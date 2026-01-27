"""Code Assistant Backend"""

import logging
from contextlib import asynccontextmanager

from agent import CodeAssistantAgent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agenkit import Message
from agenkit.protocols.agui_simple import AGUIAdapter
from agenkit.protocols.agui_simple.transports import WebSocketMessageFormat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

code_agent = None
adapter = None
formatter = WebSocketMessageFormat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global code_agent, adapter  # noqa: PLW0603
    code_agent = CodeAssistantAgent()
    adapter = AGUIAdapter(code_agent, agent_name="CodeAssistant", chunk_size=20)
    logger.info("Code Assistant ready!")
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": code_agent.name if code_agent else None}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_text(
            formatter.format_event(
                {
                    "event_type": "metadata",
                    "data": {
                        "agent_name": "CodeAssistant",
                        "capabilities": code_agent.capabilities,
                    },
                }
            )
        )
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "message":
                msg = Message(role="user", content=data.get("message", ""))
                async for event in adapter.stream_events(msg, emit_metadata=False):
                    await websocket.send_text(formatter.format_event(event))
    except WebSocketDisconnect:
        pass
