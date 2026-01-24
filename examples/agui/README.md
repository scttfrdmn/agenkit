# AG-UI Example Gallery

Production-ready examples demonstrating Agenkit agents with AG-UI protocol for real-time streaming to frontends.

## 📚 Examples

### 1. HITL Approval Workflow
**Directory**: [`hitl-approval/`](./hitl-approval/)
**Features**: Bidirectional human-in-the-loop, approval workflow, confidence-based gates
**Use Case**: Financial trading agent requiring user approval for low-confidence trades

### 2. Streaming Chat
**Directory**: [`streaming-chat/`](./streaming-chat/)
**Features**: Real-time streaming, token-by-token display, conversation history
**Use Case**: Interactive chatbot with streaming responses

### 3. Tool Visualization Dashboard
**Directory**: [`tool-dashboard/`](./tool-dashboard/)
**Features**: Real-time tool execution, performance metrics, result visualization
**Use Case**: Development/debugging tool for monitoring agent tool usage

### 4. Collaborative Document Editing
**Directory**: [`shared-state/`](./shared-state/)
**Features**: State synchronization, conflict resolution, real-time collaboration
**Use Case**: Agent and user co-editing documents with live updates

### 5. Multimodal Agent
**Directory**: [`multimodal/`](./multimodal/)
**Features**: Image analysis, file uploads, chart generation
**Use Case**: Data analysis agent handling multiple content types

### 6. Multi-Agent Coordination
**Directory**: [`multi-agent/`](./multi-agent/)
**Features**: Multiple agents, delegation, unified interface
**Use Case**: Complex workflows requiring specialized agents

### 7. Customer Support Bot
**Directory**: [`customer-support/`](./customer-support/)
**Features**: Context tracking, human escalation, FAQ handling
**Use Case**: Support agent with HITL escalation to human operators

### 8. Code Assistant
**Directory**: [`code-assistant/`](./code-assistant/)
**Features**: Documentation search, code generation, testing
**Use Case**: Developer productivity tool with code understanding

## 🚀 Quick Start

Each example includes:
- **Backend**: FastAPI server with AG-UI protocol
- **Frontend**: React UI with real-time streaming
- **Docker**: Complete Docker Compose setup
- **README**: Detailed setup and usage instructions

### Running an Example

```bash
# Choose an example
cd examples/agui/hitl-approval

# Start with Docker (recommended)
docker-compose up

# Or run locally
cd backend && uvicorn main:app --reload
cd frontend && npm install && npm run dev
```

## 🎯 Features Demonstrated

| Example | Streaming | HITL | Tools | State | Multimodal | Multi-Agent |
|---------|-----------|------|-------|-------|------------|-------------|
| HITL Approval | ✅ | ✅ | ✅ | | | |
| Streaming Chat | ✅ | | | ✅ | | |
| Tool Dashboard | ✅ | | ✅ | | | |
| Shared State | ✅ | | | ✅ | | |
| Multimodal | ✅ | | ✅ | | ✅ | |
| Multi-Agent | ✅ | ✅ | ✅ | ✅ | | ✅ |
| Customer Support | ✅ | ✅ | ✅ | ✅ | | |
| Code Assistant | ✅ | | ✅ | ✅ | | |

## 📖 Architecture

All examples follow a consistent architecture:

```
example-name/
├── backend/
│   ├── main.py           # FastAPI app with AG-UI
│   ├── agent.py          # Agent implementation
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile        # Backend container
├── frontend/
│   ├── src/
│   │   ├── App.tsx       # Main React component
│   │   ├── AGUIClient.ts # AG-UI WebSocket/SSE client
│   │   └── components/   # UI components
│   ├── package.json      # Node dependencies
│   └── Dockerfile        # Frontend container
├── docker-compose.yml    # Run everything together
└── README.md             # Setup instructions
```

## 🛠️ Technology Stack

**Backend**:
- **Agenkit**: Agent framework with AG-UI protocol
- **FastAPI**: Modern Python web framework
- **WebSockets/SSE**: Real-time streaming transport

**Frontend**:
- **React**: UI framework
- **TypeScript**: Type-safe JavaScript
- **TailwindCSS**: Utility-first styling
- **AG-UI Client**: WebSocket/SSE client library

## 📝 Common Patterns

### 1. Setting Up AG-UI Backend

```python
from fastapi import FastAPI, WebSocket
from agenkit import Agent
from agenkit.protocols.agui import AGUIAdapter
from agenkit.protocols.agui.transports.websocket import AGUIWebSocketHandler

app = FastAPI()
agent = MyAgent()
adapter = AGUIAdapter(agent)
handler = AGUIWebSocketHandler(agent)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handler.handle(websocket)
```

### 2. Connecting from Frontend

```typescript
const client = new AGUIWebSocketClient('ws://localhost:8000/ws');

client.on('text_message_chunk', (event) => {
  // Update UI with streaming text
  appendToChat(event.content);
});

client.on('interrupt', (event) => {
  // Show approval UI
  showApprovalDialog(event);
});

await client.connect();
await client.sendMessage('Hello, agent!');
```

### 3. Handling HITL Interrupts

```typescript
client.on('interrupt', async (interrupt) => {
  const action = await showApprovalDialog(interrupt);

  await client.sendInterruptResponse({
    interrupt_id: interrupt.interrupt_id,
    action: action,
    context: { feedback: 'User approved' }
  });
});
```

## 🎓 Learning Path

**Beginner**: Start with **Streaming Chat** to understand basic AG-UI streaming

**Intermediate**: Try **HITL Approval** to learn bidirectional agent control

**Advanced**: Explore **Multi-Agent** to see complex coordination patterns

## 🔗 Resources

- [AG-UI Protocol Specification](../../docs/agui-protocol.md)
- [Agenkit Documentation](https://docs.agenkit.dev)
- [API Reference](https://docs.agenkit.dev/api)
- [Community Discord](https://discord.gg/agenkit)

## 📄 License

Apache 2.0 - See [LICENSE](../../LICENSE) for details

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

---

**Built with ❤️ by the Agenkit community**
