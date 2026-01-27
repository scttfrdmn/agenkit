"""Shared FastAPI backend for custom frontend examples."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agenkit.protocols.agui import AGUIAdapter
from agenkit.protocols.agui.transports import SSETransport

from agent import SimpleChatAgent

agent = None
adapter = None
transport = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, adapter, transport  # noqa: PLW0603

    agent = SimpleChatAgent(name="ChatBot")
    adapter = AGUIAdapter(agent, chunk_size=15, agent_name="ChatBot")
    transport = SSETransport(adapter)

    print("🚀 Custom frontends backend started")
    print("📡 Serving: React, Vue, and Svelte examples")

    yield

    print("👋 Backend shutting down")


app = FastAPI(
    title="Agenkit Custom Frontends Backend",
    description="Shared AG-UI backend for React, Vue, and Svelte examples",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for demo purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/agui")
async def agui_endpoint(request: Request):
    """AG-UI Standard endpoint with SSE streaming."""
    return await transport.handle_request(request)


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy", "agent": agent.name if agent else None})


@app.get("/")
async def root():
    return JSONResponse(
        {
            "service": "Custom Frontends Backend",
            "examples": ["React", "Vue", "Svelte"],
            "endpoint": "POST /agui",
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")  # noqa: S104
