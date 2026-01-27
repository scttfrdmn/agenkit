# AG-UI Protocol Comparison: Simple vs Standard

> **Quick Decision Guide**: Use **AG-UI Simple** for learning, prototyping, and internal tools. Use **AG-UI Standard** for production deployments with CopilotKit or other framework integrations.

## Overview

Agenkit provides two implementations of the AG-UI (Agent-User Interface) protocol, each optimized for different use cases:

- **AG-UI Simple** (`agenkit.protocols.agui_simple`): Lightweight 5-event protocol with WebSocket transport
- **AG-UI Standard** (`agenkit.protocols.agui`): Full 15+ event specification with SSE transport

Both implementations enable real-time streaming communication between agents and user interfaces, but they differ in complexity, features, and intended use cases.

---

## Quick Comparison

| Feature | AG-UI Simple | AG-UI Standard |
|---------|--------------|----------------|
| **Event Types** | 5 core events | 15+ events |
| **Transport** | WebSocket | Server-Sent Events (SSE) |
| **Complexity** | ~200 LOC | ~1,000 LOC |
| **Use Cases** | Learning, MVPs, internal tools | Production, CopilotKit, enterprise |
| **Tool Tracking** | Basic | Detailed (start/args/end/result) |
| **State Management** | Simple key-value | JSON Patch (RFC 6902) |
| **Framework Integration** | Custom frontends | CopilotKit, Vercel AI SDK |
| **Specification** | Agenkit-specific | AG-UI Standard (docs.ag-ui.com) |
| **Examples** | 8 learning examples | CopilotKit integration |

---

## When to Use Each

### Use AG-UI Simple When:

✅ **Learning Agenkit**: Get started quickly with minimal setup
✅ **Rapid Prototyping**: Build MVPs and proof-of-concepts fast
✅ **Internal Tools**: Dashboards, admin interfaces, team tools
✅ **Simple Streaming**: Basic text streaming without complex state
✅ **Custom Frontends**: Building your own UI from scratch
✅ **WebSocket Preference**: Your infrastructure favors WebSocket
✅ **Minimal Dependencies**: Want to keep bundle size small

**Example Use Cases**:
- Customer support chatbot for internal team
- Data analysis dashboard with agent assistance
- Code review tool with AI suggestions
- Personal productivity assistant

### Use AG-UI Standard When:

✅ **Production Deployments**: Enterprise-grade applications
✅ **CopilotKit Integration**: Using CopilotKit React framework
✅ **Framework Compatibility**: Integrating with Vercel AI SDK, etc.
✅ **Complex Tool Tracking**: Need detailed tool execution visibility
✅ **State Management**: Require JSON Patch for efficient state updates
✅ **Multi-Agent Systems**: Coordinating multiple agents
✅ **SSE Requirements**: Infrastructure optimized for SSE
✅ **Compliance**: Need to follow AG-UI Standard specification

**Example Use Cases**:
- Customer-facing AI assistant on website
- Multi-agent research platform
- Enterprise workflow automation
- AI-powered SaaS product

---

## Architecture Comparison

### AG-UI Simple Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Web Frontend   │◄───────►│   Agenkit Agent  │
│   (Custom UI)   │  WebSocket  │  + AGUISimple    │
└─────────────────┘         └──────────────────┘
         │                           │
         │                           │
    5 Event Types              Simple Handler
    - connected                     │
    - message                       │
    - chunk                    Text Streaming
    - tool_call                     │
    - error                    Basic Tools
```

**Key Components**:
- `AGUISimpleServer`: WebSocket server
- `AGUISimpleHandler`: Event handler
- 5 event types (connected, message, chunk, tool_call, error)
- Direct WebSocket bidirectional communication

**Code Example**:
```python
from agenkit.protocols.agui_simple import AGUISimpleServer

# Create server
server = AGUISimpleServer(agent, host="0.0.0.0", port=8765)

# Start server
await server.start()
```

### AG-UI Standard Architecture

```
┌─────────────────┐         ┌──────────────────────┐
│   CopilotKit    │         │    FastAPI Server    │
│  React Frontend │◄────────┤  + AGUIAdapter       │
└─────────────────┘   SSE   │  + SSE Transport     │
         │                  └──────────────────────┘
         │                            │
    POST /agui                   AGUIAdapter
         │                            │
         │                       Event Stream
         │                            │
    15+ Event Types            Tool Tracking
    - run_started              State Manager
    - text_message_*           Tool Registry
    - tool_call_*                    │
    - state_*                   Agenkit Agent
    - activity_*
```

**Key Components**:
- `AGUIAdapter`: Wraps agent and produces events
- `SSETransport`: Handles HTTP/SSE transport
- `StateManager`: JSON Patch state management
- `ToolCallTracker`: Detailed tool execution tracking
- `ToolRegistry`: Tool metadata and discovery
- 15+ event types with Pydantic models

**Code Example**:
```python
from agenkit.protocols.agui import AGUIAdapter, SSETransport
from fastapi import FastAPI

# Create adapter and transport
adapter = AGUIAdapter(agent, chunk_size=20)
transport = SSETransport(adapter)

# FastAPI endpoint
@app.post("/agui")
async def agui_endpoint(request: Request):
    return await transport.handle_request(request)
```

---

## Event Type Comparison

### AG-UI Simple Events (5 Total)

| Event | Purpose | Payload |
|-------|---------|---------|
| `connected` | WebSocket connection established | Session info |
| `message` | Complete message from agent | Full text |
| `chunk` | Streaming text chunk | Text delta |
| `tool_call` | Tool execution notification | Tool name, args, result |
| `error` | Error notification | Error message |

**Example**:
```json
{
  "type": "chunk",
  "data": "Hello! I can help you with that."
}
```

### AG-UI Standard Events (15+ Total)

#### Lifecycle Events
- `run_started` - Begin agent execution
- `run_finished` - Complete agent execution
- `run_error` - Report execution errors
- `step_started` - Begin processing step
- `step_finished` - Complete processing step

#### Text Message Events
- `text_message_start` - Begin streaming message
- `text_message_content` - Stream message chunks
- `text_message_end` - Complete message streaming

#### Tool Call Events
- `tool_call_start` - Begin tool execution
- `tool_call_args` - Stream tool arguments
- `tool_call_end` - Complete argument streaming
- `tool_call_result` - Provide tool result

#### State Management Events
- `state_snapshot` - Complete state snapshot
- `state_delta` - State changes (JSON Patch)
- `messages_snapshot` - Conversation history

#### Activity Events
- `activity_snapshot` - Activity updates
- `activity_delta` - Activity changes

**Example**:
```json
{
  "type": "text_message_content",
  "message_id": "msg-123",
  "delta": "Hello! ",
  "timestamp": 1737936000100
}
```

---

## Feature Comparison

### Text Streaming

**AG-UI Simple**:
```python
# Single chunk event
yield {"type": "chunk", "data": "Hello"}
```

**AG-UI Standard**:
```python
# Three-phase streaming
yield TextMessageStartEvent(message_id="msg-1", role="assistant")
yield TextMessageContentEvent(message_id="msg-1", delta="Hello")
yield TextMessageEndEvent(message_id="msg-1")
```

### Tool Call Tracking

**AG-UI Simple**:
```python
# Single tool_call event
yield {
    "type": "tool_call",
    "tool": "search",
    "args": {"query": "AI"},
    "result": {"results": [...]}
}
```

**AG-UI Standard**:
```python
# Four-phase tool tracking
yield ToolCallStartEvent(tool_call_id="tool-1", tool_call_name="search")
yield ToolCallArgsEvent(tool_call_id="tool-1", delta='{"query":"AI"}')
yield ToolCallEndEvent(tool_call_id="tool-1")
yield ToolCallResultEvent(tool_call_id="tool-1", content={"results": [...]})
```

### State Management

**AG-UI Simple**:
```python
# Simple key-value state
state = {"count": 1, "user": "Alice"}
yield {"type": "state", "data": state}
```

**AG-UI Standard**:
```python
# JSON Patch operations (RFC 6902)
state_manager = StateManager({"count": 0})
state_manager.update("/count", 1)
delta_event = state_manager.get_delta_event()
# delta_event.delta = [{"op": "replace", "path": "/count", "value": 1}]
```

---

## Transport Comparison

### WebSocket (AG-UI Simple)

**Advantages**:
- ✅ Bidirectional communication (client can send anytime)
- ✅ Lower latency for real-time interactions
- ✅ Built-in connection management
- ✅ Simpler for custom frontends
- ✅ Better for high-frequency updates

**Disadvantages**:
- ❌ More complex infrastructure (sticky sessions, load balancing)
- ❌ Firewall/proxy compatibility issues
- ❌ Not HTTP-compatible (separate protocol)
- ❌ Harder to cache or CDN
- ❌ Connection management overhead

**Code**:
```python
# Server
server = AGUISimpleServer(agent, host="0.0.0.0", port=8765)
await server.start()

# Client (JavaScript)
const ws = new WebSocket('ws://localhost:8765');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

### Server-Sent Events (AG-UI Standard)

**Advantages**:
- ✅ HTTP-based (works with standard infrastructure)
- ✅ Firewall/proxy friendly
- ✅ Simpler load balancing (no sticky sessions)
- ✅ Automatic reconnection built-in
- ✅ Framework standard (CopilotKit uses SSE)
- ✅ Better for unidirectional streaming

**Disadvantages**:
- ❌ Unidirectional only (server → client)
- ❌ Client must use separate HTTP requests for input
- ❌ Text-based encoding (slightly larger payloads)
- ❌ Browser connection limits (6 per domain)

**Code**:
```python
# Server (FastAPI)
@app.post("/agui")
async def agui_endpoint(request: Request):
    return await transport.handle_request(request)

# Client (JavaScript)
const eventSource = new EventSource('/agui');
eventSource.addEventListener('text_message_content', (event) => {
  const data = JSON.parse(event.data);
  console.log(data.delta);
});
```

---

## Performance Comparison

### Message Throughput

| Metric | AG-UI Simple | AG-UI Standard |
|--------|--------------|----------------|
| **Events per message** | 1-3 | 5-10 |
| **Overhead per event** | ~50 bytes | ~150 bytes |
| **Serialization** | JSON | JSON + Pydantic |
| **Network protocol** | WebSocket (binary) | SSE (text) |
| **Typical latency** | <10ms | <20ms |

### Memory Usage

| Component | AG-UI Simple | AG-UI Standard |
|-----------|--------------|----------------|
| **Server memory** | ~5 MB per agent | ~15 MB per agent |
| **Client bundle** | ~50 KB (custom) | ~300 KB (CopilotKit) |
| **Connection state** | ~10 KB per connection | ~20 KB per connection |

### Scalability

**AG-UI Simple**:
- ✅ Efficient for high-frequency updates
- ❌ WebSocket connection limits
- ❌ Sticky session requirements

**AG-UI Standard**:
- ✅ Stateless HTTP (easier to scale)
- ✅ Standard load balancing
- ❌ More events per message

---

## Code Size Comparison

### Implementation Size

| Component | AG-UI Simple | AG-UI Standard |
|-----------|--------------|----------------|
| **Protocol core** | ~200 LOC | ~1,000 LOC |
| **Event definitions** | ~50 LOC | ~400 LOC |
| **Server/transport** | ~150 LOC | ~300 LOC |
| **State management** | ~50 LOC | ~200 LOC |
| **Tool tracking** | ~50 LOC | ~200 LOC |
| **Tests** | ~300 LOC | ~420 LOC |
| **Total** | ~800 LOC | ~2,520 LOC |

### Example Application Size

**AG-UI Simple Example** (Chat Bot):
```
backend/     ~150 LOC (agent + server)
frontend/    ~200 LOC (HTML + JS)
Total:       ~350 LOC
```

**AG-UI Standard Example** (CopilotKit):
```
backend/     ~600 LOC (agent + FastAPI + AG-UI)
frontend/    ~400 LOC (React + TypeScript)
Total:       ~1,000 LOC
```

---

## Migration Guide

### From AG-UI Simple to AG-UI Standard

**Step 1: Update Imports**

```python
# Before (Simple)
from agenkit.protocols.agui_simple import AGUISimpleServer

# After (Standard)
from agenkit.protocols.agui import AGUIAdapter, SSETransport
from agenkit.protocols.agui.transports import SSETransport
```

**Step 2: Replace Server with Adapter**

```python
# Before (Simple)
server = AGUISimpleServer(agent, host="0.0.0.0", port=8765)
await server.start()

# After (Standard)
adapter = AGUIAdapter(agent, chunk_size=20)
transport = SSETransport(adapter)

# Use with FastAPI
@app.post("/agui")
async def agui_endpoint(request: Request):
    return await transport.handle_request(request)
```

**Step 3: Update Event Handling**

```python
# Before (Simple) - Single chunk event
yield {"type": "chunk", "data": text}

# After (Standard) - Three-phase streaming
yield TextMessageStartEvent(message_id=msg_id, role="assistant")
yield TextMessageContentEvent(message_id=msg_id, delta=text)
yield TextMessageEndEvent(message_id=msg_id)
```

**Step 4: Update Frontend**

```javascript
// Before (Simple) - WebSocket
const ws = new WebSocket('ws://localhost:8765');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'chunk') {
    appendText(data.data);
  }
};

// After (Standard) - SSE or CopilotKit
const eventSource = new EventSource('/agui');
eventSource.addEventListener('text_message_content', (event) => {
  const data = JSON.parse(event.data);
  appendText(data.delta);
});

// Or use CopilotKit
<CopilotKit runtimeUrl="/agui">
  <CopilotSidebar />
</CopilotKit>
```

**Step 5: Add State Management (Optional)**

```python
# Standard only - JSON Patch state tracking
from agenkit.protocols.agui import StateManager

state_manager = StateManager(initial_state={"count": 0})
state_manager.update("/count", 1)
delta_event = state_manager.get_delta_event()
```

---

## Framework Integration

### AG-UI Simple Integration

**Custom Frontend** (Vanilla JS):
```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'message',
    content: 'Hello agent!'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleEvent(data);
};
```

**React** (Custom Hook):
```typescript
function useAGUISimple(url: string) {
  const [messages, setMessages] = useState([]);
  const ws = useRef<WebSocket>();

  useEffect(() => {
    ws.current = new WebSocket(url);
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'chunk') {
        setMessages(prev => [...prev, data.data]);
      }
    };
  }, [url]);

  return { messages, send: (msg) => ws.current?.send(msg) };
}
```

### AG-UI Standard Integration

**CopilotKit** (Production-Ready):
```typescript
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";

function App() {
  return (
    <CopilotKit runtimeUrl="/agui" agent="MyAgent">
      <CopilotSidebar defaultOpen={true}>
        <YourApp />
      </CopilotSidebar>
    </CopilotKit>
  );
}
```

**Vercel AI SDK** (Compatible):
```typescript
import { useChat } from 'ai/react';

function Chat() {
  const { messages, input, handleSubmit } = useChat({
    api: '/agui',
  });

  return (
    <div>
      {messages.map(m => (
        <div key={m.id}>{m.content}</div>
      ))}
      <form onSubmit={handleSubmit}>
        <input value={input} onChange={handleInputChange} />
      </form>
    </div>
  );
}
```

---

## Testing Comparison

### AG-UI Simple Tests

```python
@pytest.mark.asyncio
async def test_simple_streaming():
    """Test basic WebSocket streaming."""
    server = AGUISimpleServer(agent)
    await server.start()

    # Connect client
    async with websockets.connect('ws://localhost:8765') as ws:
        # Send message
        await ws.send(json.dumps({"type": "message", "content": "Hello"}))

        # Receive chunks
        chunks = []
        async for message in ws:
            data = json.loads(message)
            if data["type"] == "chunk":
                chunks.append(data["data"])
            if data["type"] == "message":
                break

    assert len(chunks) > 0
```

### AG-UI Standard Tests

```python
@pytest.mark.asyncio
async def test_standard_streaming():
    """Test AG-UI Standard event flow."""
    adapter = AGUIAdapter(agent, chunk_size=10)

    events = []
    async for event in adapter.stream_events(
        message=Message(role="user", content="Hello"),
        thread_id="thread-1",
    ):
        events.append(event)

    # Verify event sequence
    assert isinstance(events[0], RunStartedEvent)
    assert isinstance(events[1], TextMessageStartEvent)
    assert any(isinstance(e, TextMessageContentEvent) for e in events)
    assert isinstance(events[-1], RunFinishedEvent)
```

---

## Deployment Comparison

### AG-UI Simple Deployment

**Docker**:
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install agenkit
CMD ["python", "server.py"]
```

**Kubernetes**:
- Requires sticky sessions for WebSocket
- Use `sessionAffinity: ClientIP`
- Configure load balancer for WebSocket

### AG-UI Standard Deployment

**Docker Compose**:
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
```

**Kubernetes**:
- Standard HTTP load balancing
- No sticky sessions required
- Compatible with any ingress controller

---

## Decision Matrix

### Choose AG-UI Simple If:

| Criteria | Weight | Rationale |
|----------|--------|-----------|
| Learning/Education | ⭐⭐⭐ | Simpler to understand and teach |
| Rapid Prototyping | ⭐⭐⭐ | Faster to set up and iterate |
| Internal Tools | ⭐⭐⭐ | Less complexity needed |
| Custom UI | ⭐⭐⭐ | Full control over frontend |
| WebSocket Required | ⭐⭐ | Bidirectional communication |
| Minimal Dependencies | ⭐⭐ | Smaller footprint |

### Choose AG-UI Standard If:

| Criteria | Weight | Rationale |
|----------|--------|-----------|
| Production Deployment | ⭐⭐⭐ | Enterprise-grade features |
| CopilotKit Integration | ⭐⭐⭐ | Built for framework compatibility |
| Complex State | ⭐⭐⭐ | JSON Patch state management |
| Tool Tracking | ⭐⭐⭐ | Detailed execution visibility |
| Scalability | ⭐⭐⭐ | Stateless HTTP scales better |
| Framework Integration | ⭐⭐⭐ | Works with AI SDK ecosystem |

---

## Real-World Examples

### AG-UI Simple Examples

1. **Learning Examples** (`examples/agui_simple/`)
   - Basic chatbot
   - Code assistant
   - Customer support
   - Multi-agent coordination
   - All 8 examples use Simple protocol

2. **Internal Tool**: Company Dashboard
   ```python
   # Monitoring dashboard with agent assistance
   server = AGUISimpleServer(MonitoringAgent())
   # Employees connect via WebSocket for real-time alerts
   ```

3. **Prototype**: AI Writing Assistant
   ```python
   # Quick MVP for content generation
   server = AGUISimpleServer(WritingAgent())
   # Simple HTML/JS frontend for testing
   ```

### AG-UI Standard Examples

1. **CopilotKit Integration** (`examples/integrations/copilotkit/`)
   - Research assistant with tools
   - Production-ready React frontend
   - Full AG-UI Standard implementation

2. **Customer-Facing Product**: SaaS AI Assistant
   ```python
   # Production deployment with CopilotKit
   adapter = AGUIAdapter(SupportAgent())
   transport = SSETransport(adapter)
   # Integrated into main product website
   ```

3. **Enterprise Platform**: Multi-Agent Research Tool
   ```python
   # Complex state management across agents
   adapter = AGUIAdapter(CoordinatorAgent())
   state_manager = StateManager({"agents": [], "tasks": []})
   # JSON Patch for efficient state sync
   ```

---

## Summary

### AG-UI Simple: Lightweight & Fast

**Best For**: Learning, prototyping, internal tools
**Protocol**: 5 events, WebSocket
**Complexity**: Low (~800 LOC total)
**Setup Time**: < 30 minutes
**Examples**: 8 learning examples

**Key Strength**: Simplicity and speed to production for internal use cases.

### AG-UI Standard: Production-Ready

**Best For**: Customer-facing products, framework integration
**Protocol**: 15+ events, SSE
**Complexity**: Medium (~2,500 LOC total)
**Setup Time**: 1-2 hours
**Examples**: CopilotKit integration

**Key Strength**: Enterprise features and framework compatibility for production deployments.

---

## Resources

### AG-UI Simple
- **Documentation**: `docs/protocols/agui_simple.md`
- **Examples**: `examples/agui_simple/`
- **Tests**: `tests/protocols/test_agui_simple.py`

### AG-UI Standard
- **Documentation**: `docs/protocols/agui_standard.md`
- **Examples**: `examples/integrations/copilotkit/`
- **Tests**: `tests/protocols/test_agui_standard.py`
- **Specification**: https://docs.ag-ui.com/

### Framework Integration
- **CopilotKit**: https://docs.copilotkit.ai/
- **Vercel AI SDK**: https://sdk.vercel.ai/

---

## FAQ

**Q: Can I use both protocols in the same application?**
A: Yes, but not recommended. Choose one based on your primary use case. They serve different purposes.

**Q: Can I migrate from Simple to Standard later?**
A: Yes, but it requires rewriting event handling and frontend integration. Plan ahead.

**Q: Which is faster?**
A: AG-UI Simple has lower latency (WebSocket) but AG-UI Standard scales better (stateless HTTP).

**Q: Which should I use for production?**
A: If integrating with CopilotKit or similar frameworks, use Standard. For custom internal tools, Simple is fine.

**Q: Is AG-UI Standard compatible with OpenAI's protocol?**
A: No, it follows the AG-UI Standard specification (docs.ag-ui.com), which is different from OpenAI's format.

**Q: Can I extend either protocol with custom events?**
A: Yes. Simple is easier to extend (just add event types). Standard has a `CustomEvent` type for extensions.

---

**Need help choosing?** Open an issue with your use case: https://github.com/agentic-ai/agenkit/issues

**Built with ❤️ using Agenkit**
