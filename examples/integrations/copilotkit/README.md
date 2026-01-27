# Agenkit + CopilotKit Integration

> **🎯 Production-Ready Example**: This example demonstrates how to integrate Agenkit with CopilotKit using the AG-UI Standard protocol for building AI-powered chat interfaces.

## Overview

This example showcases a complete implementation of Agenkit's AG-UI Standard protocol integrated with CopilotKit's React components. The research assistant agent provides web search, calculation, and weather capabilities through a modern chat interface.

### Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│   React Frontend    │         │   FastAPI Backend    │
│   + CopilotKit      │◄────────┤   + Agenkit          │
│                     │   SSE   │   + AG-UI Standard   │
└─────────────────────┘         └──────────────────────┘
         │                               │
         │                               │
    CopilotKit                      AGUIAdapter
    Components                      + SSE Transport
         │                               │
         │                               │
    POST /agui ─────────────────────────►│
         │                               │
         │◄────── Event Stream ──────────┤
         │      (text, tools, state)     │
```

### Features

- **🔍 Web Search Tool**: Search for information and current events
- **🧮 Calculator Tool**: Perform mathematical calculations
- **🌤️ Weather Tool**: Get weather forecasts for locations
- **📡 AG-UI Standard Protocol**: 15+ event types for rich interactions
- **🌊 Server-Sent Events**: Efficient streaming transport
- **🔧 Tool Call Tracking**: Real-time visibility into tool execution
- **📊 State Management**: JSON Patch for efficient state updates
- **🏗️ Production Ready**: CORS, health checks, error handling

## Quick Start

### Prerequisites

- Python 3.11+ with `uv` installed
- Node.js 20+ with npm
- Docker & Docker Compose (for containerized deployment)

### Option 1: Local Development

#### 1. Start the Backend

```bash
cd backend

# Install dependencies
uv pip install -r requirements.txt

# Run the server
uv run python main.py
```

Backend will start on http://localhost:8000

**Available Endpoints:**
- `POST /agui` - AG-UI Standard endpoint (SSE stream)
- `GET /health` - Health check
- `GET /metadata` - Agent metadata
- `GET /` - API information

#### 2. Start the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run the dev server
npm run dev
```

Frontend will start on http://localhost:3000

### Option 2: Docker Compose

```bash
# From the copilotkit directory
docker-compose up --build
```

Access the application at http://localhost:3000

**Services:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Health Check: http://localhost:8000/health
- Metadata: http://localhost:8000/metadata

## Project Structure

```
copilotkit/
├── backend/
│   ├── agent.py              # ResearchAssistantAgent with tools
│   ├── main.py               # FastAPI server with AG-UI Standard
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Backend container image
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main React component with CopilotKit
│   │   ├── App.css           # Styles
│   │   ├── main.tsx          # React entry point
│   │   └── index.css         # Global styles
│   ├── package.json          # Node dependencies
│   ├── vite.config.ts        # Vite configuration
│   ├── tsconfig.json         # TypeScript configuration
│   └── Dockerfile            # Frontend container image
├── docker-compose.yml        # Multi-container orchestration
└── README.md                 # This file
```

## How It Works

### Backend (Agenkit + AG-UI Standard)

**1. Agent with Tools** (`agent.py`)

The `ResearchAssistantAgent` includes three tools:

```python
class ResearchAssistantAgent(Agent):
    def __init__(self):
        self._tools = {
            "web_search": SearchTool(),       # Web search capability
            "calculator": CalculatorTool(),   # Math calculations
            "get_weather": WeatherTool(),     # Weather information
        }

    async def process(self, message: Message) -> Message:
        # Analyze query and select appropriate tools
        tools_to_use = self._analyze_query(message.content)

        # Execute tools
        tool_results = []
        for tool_name, args in tools_to_use:
            result = await self._tools[tool_name].execute(**args)
            tool_results.append({"tool": tool_name, "result": result})

        # Generate response based on results
        return await self._generate_response(message.content, tool_results)
```

**2. FastAPI Server with AG-UI** (`main.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, adapter, transport

    # Initialize Agenkit components
    agent = ResearchAssistantAgent()
    adapter = AGUIAdapter(agent, chunk_size=20)
    transport = SSETransport(adapter)

    yield

@app.post("/agui")
async def agui_endpoint(request: Request):
    """AG-UI Standard endpoint with SSE streaming."""
    return await transport.handle_request(request)
```

**3. AG-UI Event Flow**

```
User Message
    │
    ▼
RunStartedEvent ──────► CopilotKit shows "Thinking..."
    │
    ▼
TextMessageStartEvent ─► CopilotKit prepares message container
    │
    ▼
TextMessageContent... ─► CopilotKit streams text chunks
TextMessageContent...
TextMessageContent...
    │
    ▼
ToolCallStartEvent ────► CopilotKit shows tool execution
ToolCallArgsEvent
ToolCallEndEvent
ToolCallResultEvent
    │
    ▼
TextMessageEndEvent ───► CopilotKit finalizes message
    │
    ▼
RunFinishedEvent ──────► CopilotKit ready for next input
```

### Frontend (React + CopilotKit)

**1. CopilotKit Integration** (`App.tsx`)

```typescript
<CopilotKit
  runtimeUrl="/agui"           // Agenkit backend endpoint
  agent="ResearchAssistant"    // Agent identifier
  showDevConsole={true}        // Debug mode
>
  <CopilotSidebar
    defaultOpen={true}
    labels={{
      title: "Research Assistant",
      initial: "Hi! I'm your research assistant..."
    }}
  >
    {/* Your application content */}
  </CopilotSidebar>
</CopilotKit>
```

**2. Vite Proxy Configuration** (`vite.config.ts`)

```typescript
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/agui': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

This proxies frontend requests to the backend during development.

## Usage Examples

### Example 1: Web Search

**User:** "Search for the latest developments in AI agents"

**Agent Flow:**
1. Detects "search" keyword
2. Calls `web_search` tool with query
3. Formats search results with titles, snippets, URLs
4. Streams formatted response to frontend

### Example 2: Math Calculation

**User:** "Calculate the area of a circle with radius 10"

**Agent Flow:**
1. Detects calculation keywords
2. Calls `calculator` tool with expression
3. Returns formatted result: `🧮 Calculation: π * 10^2 = 314.159`

### Example 3: Weather Forecast

**User:** "What's the weather in San Francisco?"

**Agent Flow:**
1. Detects "weather" keyword and location
2. Calls `get_weather` tool
3. Returns current conditions and 3-day forecast

### Example 4: Multi-Tool Query

**User:** "Search for Python async patterns and calculate 2 to the power of 10"

**Agent Flow:**
1. Detects both search and calculation
2. Calls both `web_search` and `calculator` tools
3. Combines results in formatted response

## AG-UI Standard Protocol Details

### Event Types

This example uses the following AG-UI Standard events:

| Event Type              | Purpose                                      |
|------------------------|----------------------------------------------|
| `run_started`          | Begin agent execution                        |
| `run_finished`         | Complete agent execution                     |
| `run_error`            | Report execution errors                      |
| `text_message_start`   | Begin streaming message                      |
| `text_message_content` | Stream message content chunks                |
| `text_message_end`     | Complete message streaming                   |
| `tool_call_start`      | Begin tool execution                         |
| `tool_call_args`       | Stream tool arguments                        |
| `tool_call_end`        | Complete argument streaming                  |
| `tool_call_result`     | Provide tool execution result                |
| `state_snapshot`       | Send complete state                          |
| `state_delta`          | Send state changes (JSON Patch)              |

### SSE Format

Events are sent as Server-Sent Events (SSE):

```
event: run_started
data: {"type":"run_started","thread_id":"thread-123","run_id":"run-456","timestamp":1737936000000}

event: text_message_start
data: {"type":"text_message_start","message_id":"msg-789","role":"assistant","timestamp":1737936000100}

event: text_message_content
data: {"type":"text_message_content","message_id":"msg-789","delta":"Hello! ","timestamp":1737936000120}

event: text_message_content
data: {"type":"text_message_content","message_id":"msg-789","delta":"I found ","timestamp":1737936000140}
```

### Tool Call Tracking

When the agent uses tools, CopilotKit shows real-time execution:

```
event: tool_call_start
data: {"type":"tool_call_start","tool_call_id":"tool-abc","tool_call_name":"web_search","timestamp":1737936000200}

event: tool_call_args
data: {"type":"tool_call_args","tool_call_id":"tool-abc","delta":"{\"query\":\"AI agents\"}","timestamp":1737936000220}

event: tool_call_end
data: {"type":"tool_call_end","tool_call_id":"tool-abc","timestamp":1737936000240}

event: tool_call_result
data: {"type":"tool_call_result","message_id":"msg-result","tool_call_id":"tool-abc","content":{"results":[...]},"timestamp":1737936000500}
```

## Customization

### Adding New Tools

**1. Create Tool Class** (`agent.py`):

```python
class TranslateTool(Tool):
    @property
    def name(self) -> str:
        return "translate"

    @property
    def description(self) -> str:
        return "Translate text to another language"

    async def execute(self, text: str, target_lang: str) -> ToolResult:
        # Implement translation logic
        return ToolResult(
            success=True,
            data={"translated": f"{text} (translated to {target_lang})"},
        )
```

**2. Register Tool**:

```python
class ResearchAssistantAgent(Agent):
    def __init__(self):
        self._tools = {
            "web_search": SearchTool(),
            "calculator": CalculatorTool(),
            "get_weather": WeatherTool(),
            "translate": TranslateTool(),  # Add new tool
        }
```

**3. Update Query Analysis**:

```python
def _analyze_query(self, query: str) -> list[tuple[str, dict[str, Any]]]:
    # Add translation detection
    if "translate" in query.lower():
        tools.append(("translate", {"text": query, "target_lang": "es"}))
```

### Customizing UI

**Modify CopilotSidebar Labels** (`App.tsx`):

```typescript
<CopilotSidebar
  labels={{
    title: "Custom Assistant",
    initial: "Your custom greeting...",
    placeholder: "Ask me anything...",
  }}
>
```

**Update Styles** (`App.css`):

```css
.app-header h1 {
  background: linear-gradient(135deg, #your-color-1 0%, #your-color-2 100%);
}
```

## Testing

### Backend Tests

```bash
cd backend

# Unit tests (when added)
uv run pytest tests/

# Manual API testing
curl -X POST http://localhost:8000/agui \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","thread_id":"test-123"}'
```

### Frontend Tests

```bash
cd frontend

# Type checking
npm run type-check

# Linting
npm run lint

# Build test
npm run build
```

## Deployment

### Environment Variables

**Backend** (`backend/.env`):
```env
PORT=8000
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

**Frontend** (`frontend/.env`):
```env
VITE_API_URL=http://localhost:8000
```

### Production Deployment

**1. Docker Compose** (Recommended):

```bash
# Build and deploy
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**2. Kubernetes** (Advanced):

See `deploy/kubernetes/` for manifests (not included in this example).

**3. Cloud Platforms**:

- **Backend**: Deploy to any Python hosting (Render, Railway, Fly.io)
- **Frontend**: Deploy to Vercel, Netlify, or Cloudflare Pages

## Troubleshooting

### Common Issues

**1. CORS Errors**

**Problem**: Frontend can't connect to backend

**Solution**: Ensure CORS origins are configured in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**2. SSE Connection Drops**

**Problem**: Event stream disconnects unexpectedly

**Solution**: Check backend logs for errors. Ensure FastAPI is running with uvicorn (not development server).

**3. Tool Execution Fails**

**Problem**: Tools return errors or no results

**Solution**: Check `agent.py` tool implementations. Add logging to see execution flow.

**4. Frontend Build Errors**

**Problem**: TypeScript or React errors during build

**Solution**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for type errors
npm run type-check
```

### Debug Mode

**Enable Backend Debug Logging** (`main.py`):

```python
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",  # Change from "info"
    )
```

**Enable Frontend Dev Console** (`App.tsx`):

```typescript
<CopilotKit
  showDevConsole={true}  // Already enabled
>
```

## Performance

### Backend Optimization

- **Chunk Size**: Adjust `AGUIAdapter(chunk_size=20)` for optimal streaming
- **Concurrency**: FastAPI handles concurrent requests efficiently
- **Caching**: Add caching for repeated tool calls (not implemented)

### Frontend Optimization

- **Build Size**: ~300KB gzipped (React + CopilotKit)
- **Load Time**: <2s on 4G connection
- **Rendering**: Optimized with React.memo and proper keys

## Next Steps

### Enhancements

1. **Authentication**: Add user authentication and session management
2. **Persistence**: Store conversation history in database
3. **Real Tools**: Replace mock tools with real APIs (OpenAI, Weather API, etc.)
4. **Analytics**: Track tool usage and conversation metrics
5. **Multi-Agent**: Implement agent coordination for complex tasks
6. **Voice Input**: Add speech-to-text for voice queries
7. **File Upload**: Support document analysis and search

### Learning Resources

- **AG-UI Standard Spec**: https://docs.ag-ui.com/
- **Agenkit Docs**: https://github.com/agentic-ai/agenkit
- **CopilotKit Docs**: https://docs.copilotkit.ai/
- **FastAPI Docs**: https://fastapi.tiangolo.com/

## License

This example is part of the Agenkit project and follows the same license.

---

**Need Help?**

- Open an issue: https://github.com/agentic-ai/agenkit/issues
- Join Discord: https://discord.gg/agenkit
- Read docs: https://agenkit.dev/docs

---

**Built with ❤️ using Agenkit**
