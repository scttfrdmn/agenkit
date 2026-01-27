"""FastAPI backend with AG-UI Standard for CopilotKit integration.

This demonstrates:
- AG-UI Standard protocol with SSE transport
- Tool call tracking and visualization
- State management with JSON Patch
- Production-ready FastAPI setup
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agenkit import Message
from agenkit.protocols.agui import AGUIAdapter, StateManager, ToolRegistry
from agenkit.protocols.agui.transports import SSETransport

from agent import ResearchAssistantAgent

# ============================================================================
# Global State (initialized in lifespan)
# ============================================================================

agent = None
adapter = None
state_manager = None
tool_registry = None
transport = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Initializes agent, adapter, and AG-UI components on startup.
    """
    global agent, adapter, state_manager, tool_registry, transport  # noqa: PLW0603

    # Initialize agent
    agent = ResearchAssistantAgent(name="ResearchAssistant")

    # Initialize AG-UI components
    adapter = AGUIAdapter(agent, chunk_size=20, agent_name="ResearchAssistant")
    state_manager = StateManager(initial_state={"message_count": 0})
    tool_registry = ToolRegistry()

    # Register tools
    for tool_name, tool in agent.tools.items():
        tool_registry.register(tool)

    # Initialize SSE transport
    transport = SSETransport(adapter)

    print("🚀 CopilotKit backend started")
    print(f"📡 AG-UI endpoint: POST /agui")
    print(f"🔧 Tools available: {', '.join(tool_registry.get_metadata())}")

    yield

    print("👋 CopilotKit backend shutting down")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Agenkit CopilotKit Integration",
    description="Research assistant with AG-UI Standard protocol for CopilotKit",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# AG-UI Endpoint
# ============================================================================


@app.post("/agui")
async def agui_endpoint(request: Request):
    """AG-UI Standard endpoint for CopilotKit.

    Accepts AG-UI requests and returns SSE stream with events.

    Expected request body:
        {
            "thread_id": "thread-123",
            "run_id": "run-456",  # optional
            "message": "What's the weather?",
            "messages": [...],  # conversation history
            "tools": [...]  # available tools
        }

    Returns:
        StreamingResponse with AG-UI Standard events (SSE format)
    """
    return await transport.handle_request(request)


# ============================================================================
# Health & Metadata Endpoints
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        Health status
    """
    return JSONResponse(
        {
            "status": "healthy",
            "service": "agenkit-copilotkit",
            "version": "0.1.0",
            "agent": agent.name if agent else None,
        }
    )


@app.get("/metadata")
async def get_metadata():
    """Get agent metadata.

    Returns metadata about the agent, including available tools,
    capabilities, and configuration.

    Returns:
        Agent metadata
    """
    return JSONResponse(
        {
            "agent": {
                "name": agent.name,
                "type": "ResearchAssistant",
                "description": "Research assistant with search, calculation, and weather capabilities",
            },
            "tools": tool_registry.get_metadata() if tool_registry else [],
            "capabilities": {
                "streaming": True,
                "tool_calls": True,
                "state_management": True,
                "hitl": False,  # Not implemented in this example
            },
            "protocol": {
                "name": "AG-UI Standard",
                "version": "1.0",
                "transport": "SSE",
                "endpoint": "/agui",
            },
        }
    )


@app.get("/")
async def root():
    """Root endpoint with API information.

    Returns:
        API information
    """
    return JSONResponse(
        {
            "service": "Agenkit CopilotKit Integration",
            "version": "0.1.0",
            "endpoints": {
                "agui": "POST /agui - AG-UI Standard endpoint",
                "health": "GET /health - Health check",
                "metadata": "GET /metadata - Agent metadata",
            },
            "documentation": "/docs",
        }
    )


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler.

    Args:
        request: The request that caused the exception
        exc: The exception

    Returns:
        Error response
    """
    print(f"❌ Error processing request: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104
        port=8000,
        log_level="info",
    )
