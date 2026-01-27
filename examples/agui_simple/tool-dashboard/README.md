# Tool Visualization Dashboard

Production-ready example demonstrating real-time tool execution monitoring with AG-UI protocol.

## 🎯 Overview

This example showcases an agent that uses multiple tools (web search, calculator, weather, database) and visualizes their execution in real-time. Perfect for understanding how to monitor and debug agent tool usage.

### Key Features

- ✅ **Real-time Tool Monitoring**: Watch tools execute live
- ✅ **Performance Metrics**: Execution time, success rate, call counts
- ✅ **Visual Feedback**: Tool status indicators and animations
- ✅ **Multiple Tools**: Search, calculator, weather, database
- ✅ **Detailed Logging**: Complete execution history with timestamps
- ✅ **Production Ready**: Proper error handling and logging

## 🏗️ Architecture

```
┌─────────────────────┐                  ┌──────────────────────┐
│                     │   WebSocket      │                      │
│  Dashboard UI       │◄─────────────────►│  FastAPI Backend     │
│                     │                  │                      │
│  - Tool Status      │                  │  - ResearchAgent     │
│  - Execution Log    │                  │  - 4 Tools:          │
│  - Metrics Display  │                  │    • Web Search      │
│  - Query Input      │                  │    • Calculator      │
│                     │                  │    • Weather         │
└─────────────────────┘                  │    • Database        │
        │                                │  - AG-UI Adapter     │
        │                                │  - Event Stream      │
        ▼                                │                      │
   User Queries                          └──────────────────────┘
   Multiple Tools                                 │
   Executed                                       │
                                                  ▼
                                          Tool Execution
                                          with Metrics
```

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+ (optional, for static file serving)
- Docker & Docker Compose (optional)

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and start both services
docker-compose up --build

# Access the application
open http://localhost:3000
```

### Option 2: Run Locally

#### Backend

```bash
cd backend

# Install dependencies
pip install -e ../../../../  # Install agenkit locally
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: `http://localhost:8000`
WebSocket: `ws://localhost:8000/ws`

#### Frontend

```bash
cd frontend

# Serve with any static file server
python -m http.server 3000

# Or use Node.js
npx serve -p 3000
```

Frontend available at: `http://localhost:3000`

## 🎮 Usage

### 1. Open the Dashboard

Navigate to http://localhost:3000 and you'll see:
- **Left Panel**: Available tools with execution stats
- **Right Panel**: Execution log with query input
- **Top Bar**: Connection status and global metrics

### 2. Try Quick Queries

Click any quick query button:
- 🔍 **Search News**: Triggers web search tool
- 🔢 **Calculate**: Triggers calculator tool
- ☀️ **Weather**: Triggers weather tool
- 💾 **Database**: Triggers database query tool
- 🚀 **All Tools**: Triggers all tools simultaneously!

### 3. Watch Tool Execution

As tools execute, you'll see:
- Tool cards highlight in real-time
- Execution times displayed
- Success/error indicators
- Detailed results in execution log

### 4. Monitor Metrics

The status bar shows:
- **Connection**: WebSocket status
- **Tools Executed**: Total tool call count
- **Avg Execution Time**: Mean time across all calls
- **Success Rate**: Percentage of successful executions

## 💬 Example Interactions

### Single Tool - Web Search

**You**: `Search for latest AI news`

**Tool Execution**:
- Tool: `web_search`
- Parameters: `{"query": "latest AI news", "num_results": 3}`
- Execution Time: ~1.2s
- Result: 3 search results with titles and URLs

### Single Tool - Calculator

**You**: `Calculate 156 * 23`

**Tool Execution**:
- Tool: `calculator`
- Parameters: `{"operation": "multiply", "a": 156, "b": 23}`
- Execution Time: ~0.15s
- Result: `3588`

### Multiple Tools - Complex Query

**You**: `Search weather calculate database all`

**Tool Executions** (4 tools in sequence):
1. `web_search` - 1.1s
2. `calculator` - 0.2s
3. `get_weather` - 0.8s
4. `query_database` - 0.4s

Total Execution Time: ~2.5s

## 🔧 Configuration

### Tool Execution Settings

Edit `backend/agent.py` to customize tools:

```python
class SearchTool(Tool):
    async def execute(self, query: str, num_results: int = 5) -> dict:
        # Customize search behavior
        await asyncio.sleep(random.uniform(0.8, 1.5))  # Adjust latency
        # ... custom logic
```

### Streaming Settings

Edit `backend/main.py`:

```python
adapter = AGUIAdapter(
    research_agent,
    agent_name="ResearchAssistant",
    chunk_size=15,  # Adjust for faster/slower streaming
)
```

### Tool Selection Logic

Edit `backend/agent.py` `_select_tools()` method:

```python
def _select_tools(self, content: str) -> list[tuple[str, dict]]:
    """Customize which tools execute based on query."""
    tools = []

    if "custom_keyword" in content:
        tools.append(("custom_tool", {"param": "value"}))

    return tools
```

## 📊 AG-UI Events

This example demonstrates these AG-UI events:

### 1. MetadataEvent

Sent on connection with available tools:
```json
{
  "event_type": "metadata",
  "data": {
    "agent_name": "ResearchAssistant",
    "available_tools": [
      {"name": "web_search", "description": "Search the web"},
      {"name": "calculator", "description": "Perform calculations"},
      {"name": "get_weather", "description": "Get weather info"},
      {"name": "query_database", "description": "Query database"}
    ]
  }
}
```

### 2. TextMessageComplete

Includes tool execution metadata:
```json
{
  "event_type": "text_message_complete",
  "message_id": "msg_abc123",
  "content": "# Results for: \"search weather\"...",
  "metadata": {
    "tools_used": ["web_search", "get_weather"],
    "total_execution_time": 2.1,
    "tool_results": [
      {
        "tool": "web_search",
        "status": "success",
        "execution_time": 1.2,
        "result": {...}
      },
      {
        "tool": "get_weather",
        "status": "success",
        "execution_time": 0.9,
        "result": {...}
      }
    ]
  }
}
```

## 🧪 Testing

### Manual Testing

1. **Single Tool**: Send query that triggers one tool, verify execution
2. **Multiple Tools**: Send query triggering all tools, verify parallel execution
3. **Error Handling**: Modify tool to throw error, verify error display
4. **Metrics**: Execute several queries, verify metrics update correctly
5. **Connection**: Disconnect backend, verify reconnection behavior

### Automated Testing

```bash
cd backend
pytest tests/
```

### Load Testing

```bash
# Install dependencies
pip install locust

# Run load test (simulates multiple concurrent users)
locust -f tests/load_test.py --host=ws://localhost:8000
```

## 📚 Code Walkthrough

### Backend: Tools Implementation

```python
class SearchTool(Tool):
    """Mock web search tool with realistic latency."""

    @property
    def name(self) -> str:
        return "web_search"

    async def execute(self, query: str, num_results: int = 5) -> dict:
        # Simulate network latency
        await asyncio.sleep(random.uniform(0.8, 1.5))

        # Return mock results
        return {
            "query": query,
            "results_count": num_results,
            "results": [...]
        }
```

### Backend: Agent Processing

```python
async def process(self, message: Message) -> Message:
    """Execute appropriate tools and return results."""
    tools_to_execute = self._select_tools(content)

    results = []
    for tool_name, params in tools_to_execute:
        tool = self._tools[tool_name]
        start_time = datetime.utcnow()

        result = await tool.execute(**params)
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        results.append({
            "tool": tool_name,
            "result": result,
            "execution_time": execution_time,
            "status": "success"
        })

    return Message(
        role="assistant",
        content=self._format_results(content, results),
        metadata={"tool_results": results}
    )
```

### Frontend: Tool Status Visualization

```javascript
visualizeToolExecution(result) {
    const toolName = result.tool;
    const status = result.status;

    // Highlight tool card
    const toolCard = document.querySelector(`[data-tool="${toolName}"]`);
    toolCard.classList.add('executing');  // Yellow animation

    setTimeout(() => {
        toolCard.classList.remove('executing');
        toolCard.classList.add(status);  // Green (success) or Red (error)
    }, result.execution_time * 1000);
}
```

### Frontend: Metrics Tracking

```javascript
updateToolStats(result) {
    const stats = this.toolStats.get(result.tool);
    stats.executionCount++;
    stats.totalTime += result.execution_time;
    stats.successCount++;

    this.executionMetrics.totalExecutions++;
    this.executionMetrics.totalTime += result.execution_time;

    this.updateMetrics();  // Refresh display
}
```

## 🎨 Customization

### Add New Tool

1. **Create tool class** in `backend/agent.py`:

```python
class CustomTool(Tool):
    @property
    def name(self) -> str:
        return "custom_tool"

    @property
    def description(self) -> str:
        return "Description of custom tool"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
            },
            "required": ["param1"]
        }

    async def execute(self, param1: str) -> dict:
        # Your custom logic
        return {"result": "..."}
```

2. **Register tool** in `ResearchAgent.__init__()`:

```python
self._tools["custom_tool"] = CustomTool()
```

3. **Add tool selection logic** in `_select_tools()`:

```python
if "custom_keyword" in content:
    tools.append(("custom_tool", {"param1": "value"}))
```

4. **Update frontend** to display in metadata (automatic)

### Modify Dashboard Layout

Edit `frontend/index.html` CSS:

```css
.dashboard {
    grid-template-columns: 400px 1fr;  /* Wider tool panel */
}

.tool-card {
    background: #f0f9ff;  /* Custom color */
}
```

### Change Tool Colors

Edit `frontend/index.html`:

```css
.tool-card.executing {
    border-left-color: #3b82f6;  /* Blue instead of orange */
}

.tool-card.success {
    border-left-color: #22c55e;  /* Custom green */
}
```

## 🐛 Troubleshooting

### Tools Not Executing

```bash
# Check backend logs
docker-compose logs backend

# Verify agent processes message
# Look for: "Client <id>: <message>"
```

### Metrics Not Updating

- **Check browser console** for JavaScript errors
- **Verify metadata** in message_complete event includes `tool_results`
- **Review** `handleMessageComplete()` in client.js

### Slow Tool Execution

Adjust simulated latency in `backend/agent.py`:

```python
# In each tool's execute() method:
await asyncio.sleep(random.uniform(0.1, 0.3))  # Faster
```

### Connection Issues

```bash
# Test backend directly
curl http://localhost:8000/health

# Test WebSocket
wscat -c ws://localhost:8000/ws
```

## 📖 API Reference

### Tool Interface

All tools must implement:

```python
class Tool(ABC):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def parameters(self) -> dict: ...

    async def execute(self, **kwargs) -> dict: ...
```

### Tool Result Format

```python
{
    "tool": "tool_name",
    "params": {"param1": "value"},
    "result": {"data": "..."},  # Or "error": "message"
    "execution_time": 1.234,
    "status": "success"  # Or "error"
}
```

## 🚢 Production Deployment

### Environment Variables

```bash
# .env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_URL=https://your-domain.com
LOG_LEVEL=info
```

### Docker Production

```bash
# Build for production
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Performance Tuning

- **Chunk Size**: Increase for faster streaming
- **Tool Latency**: Reduce sleep times for faster execution
- **Connection Pooling**: For multiple concurrent users
- **Caching**: Cache tool results when appropriate

## 📈 Metrics & Monitoring

### Key Metrics

- Tool execution count (per tool)
- Average execution time (per tool and global)
- Success rate (percentage)
- Total processing time
- WebSocket connection count

### Logging

Backend logs include:
- Tool execution start/complete
- Execution times
- Error details
- WebSocket events

## 🔗 Next Steps

After mastering tool visualization, explore:

1. **Multi-Agent** (`../multi-agent/`) - Coordinate multiple agents
2. **HITL Approval** (`../hitl-approval/`) - Add approval workflows
3. **Multimodal Agent** (`../multimodal/`) - Handle images and files

## 📄 License

Apache 2.0 - See [LICENSE](../../../../LICENSE)

## 🔗 Resources

- [AG-UI Protocol Specification](../../../../docs/agui-protocol.md)
- [Agenkit Documentation](https://docs.agenkit.dev)
- [AG-UI Example Gallery](../)

---

**Built with ❤️ using Agenkit**
