# Streaming Chat Example

Production-ready example demonstrating real-time streaming chat with AG-UI protocol.

## 🎯 Overview

This example shows a conversational agent that streams responses token-by-token to create a smooth, interactive chat experience. Perfect for understanding the basics of AG-UI streaming without additional complexity.

### Key Features

- ✅ **Real-time Streaming**: Token-by-token response display
- ✅ **Smooth UX**: Typing indicators and animations
- ✅ **Conversation History**: Full chat history preserved
- ✅ **Modern UI**: Clean, responsive chat interface
- ✅ **Production Ready**: Proper error handling and logging
- ✅ **Simple Architecture**: Minimal complexity, maximum clarity

## 🏗️ Architecture

```
┌──────────────────┐                  ┌───────────────────┐
│                  │   WebSocket      │                   │
│  Chat Interface  │◄─────────────────►│  FastAPI Backend  │
│                  │                  │                   │
│  - Message Input │                  │  - ChatAgent      │
│  - Streaming     │                  │  - AG-UI Adapter  │
│    Display       │                  │  - Event Stream   │
│  - History       │                  │                   │
└──────────────────┘                  └───────────────────┘
        │                                      │
        │                                      │
        ▼                                      ▼
   User Types                          Token-by-Token
   Message                             Streaming
```

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+ (optional, for React frontend)
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

### 1. Start the Chat

Open http://localhost:3000 and you'll see the chat interface.

### 2. Try Quick Prompts

Click any of the quick prompt buttons:
- 👋 Say Hello
- ❓ What can you do?
- 📡 About AG-UI
- 🔧 About Agenkit

### 3. Watch the Streaming

Notice how responses appear smoothly, word by word, creating a natural conversational flow.

### 4. Have a Conversation

Type your own messages and experience the real-time streaming effect!

## 💬 Example Conversations

### Getting Started

**You**: `Hello!`

**Agent**: `Hello! 👋 I'm your AI assistant, here to help with questions, provide information, or just have a friendly chat. What would you like to know?`

### Learning About AG-UI

**You**: `Tell me about AG-UI streaming`

**Agent**: `AG-UI (Agent-User Interaction) is a protocol for streaming agent responses to frontends in real-time. Key features include:

**Streaming**: Responses appear token-by-token as they're generated, providing immediate feedback to users.

**Events**: Different event types (metadata, text chunks, tool calls, interrupts) enable rich interactions.

**Transport**: Works over WebSockets or Server-Sent Events (SSE) for flexible deployment.

**Interactivity**: Supports bidirectional communication for human-in-the-loop workflows, approvals, and interactive tools.

You're experiencing AG-UI streaming right now!`

## 🔧 Configuration

### Streaming Settings

Edit `backend/main.py`:

```python
adapter = AGUIAdapter(
    chat_agent,
    agent_name="StreamingAssistant",
    chunk_size=10,  # Adjust for faster/slower streaming
)
```

**chunk_size** controls streaming speed:
- Smaller values (5-10): Slower, more dramatic streaming effect
- Larger values (20-50): Faster streaming, still smooth
- Very large (100+): Almost instant display

### Agent Behavior

Edit `backend/agent.py` to customize:
- Response content and style
- Conversation topics
- Response classification
- Metadata included

## 📊 AG-UI Events

This example demonstrates these AG-UI events:

### 1. MetadataEvent

Sent on connection:
```json
{
  "event_type": "metadata",
  "data": {
    "agent_name": "StreamingAssistant",
    "capabilities": ["chat", "conversation", "streaming", "q&a"],
    "protocol": "AG-UI",
    "version": "1.0"
  }
}
```

### 2. TextMessageStart

Marks beginning of response:
```json
{
  "event_type": "text_message_start",
  "message_id": "msg_abc123",
  "role": "assistant",
  "metadata": {"agent_name": "StreamingAssistant"}
}
```

### 3. TextMessageChunk

Streams content:
```json
{
  "event_type": "text_message_chunk",
  "message_id": "msg_abc123",
  "content": "Hello! I'm",
  "metadata": {"chunk_index": 0}
}
```

### 4. TextMessageComplete

Marks end of response:
```json
{
  "event_type": "text_message_complete",
  "message_id": "msg_abc123",
  "content": "Hello! I'm your AI assistant...",
  "finish_reason": "stop",
  "metadata": {
    "agent_name": "StreamingAssistant",
    "conversation_count": 1,
    "response_type": "greeting"
  }
}
```

## 🧪 Testing

### Manual Testing

1. **Connection**: Verify WebSocket connects on page load
2. **Streaming**: Send message and watch token-by-token display
3. **History**: Send multiple messages, verify all preserved
4. **Error Handling**: Disconnect backend, verify error message
5. **Reconnection**: Restart backend, verify reconnects

### Automated Testing

```bash
cd backend
pytest tests/
```

### Load Testing

```bash
# Install dependencies
pip install locust

# Run load test
locust -f tests/load_test.py --host=ws://localhost:8000
```

## 📚 Code Walkthrough

### Backend: Setting Up Streaming

```python
# Create agent
chat_agent = ChatAgent(name="StreamingAssistant")

# Wrap with AG-UI adapter
adapter = AGUIAdapter(
    chat_agent,
    chunk_size=10,  # Small chunks for smooth streaming
)

# Stream events
async for event in adapter.stream_events(message):
    formatted = formatter.format_event(event)
    await websocket.send_text(formatted)
```

### Frontend: Handling Streaming

```javascript
client.on('text_message_chunk', (chunk) => {
  // Append chunk to current message
  currentMessage.textContent += chunk.content;

  // Show blinking cursor
  showCursor();
});

client.on('text_message_complete', (event) => {
  // Remove cursor
  hideCursor();

  // Format final message
  currentMessage.innerHTML = formatMessage(event.content);
});
```

## 🎨 Customization

### Change Color Scheme

Edit `frontend/index.html` CSS:

```css
.message.user .message-content {
    background: #667eea;  /* User message color */
}

.message.agent .message-content {
    background: white;    /* Agent message color */
}
```

### Add Custom Prompts

Edit `frontend/index.html`:

```html
<div class="quick-prompt" onclick="sendQuickPrompt('Your prompt')">
    🎯 Your Prompt
</div>
```

### Modify Agent Personality

Edit `backend/agent.py`:

```python
def _generate_response(self, content: str) -> str:
    # Add your custom response logic
    if "custom_keyword" in content:
        return "Your custom response here!"
```

## 🐛 Troubleshooting

### WebSocket Won't Connect

```bash
# Check if backend is running
curl http://localhost:8000/health

# Test WebSocket directly
wscat -c ws://localhost:8000/ws
```

### Streaming Not Smooth

- **Increase chunk size** for faster streaming
- **Check network latency** with browser DevTools
- **Verify WebSocket** isn't being buffered by proxy

### Messages Not Appearing

- **Check browser console** for JavaScript errors
- **Verify event handling** in client.js
- **Review backend logs** for errors

## 📖 API Reference

### WebSocket Protocol

**Client → Server** (Send message):
```json
{
  "type": "message",
  "message": "Hello, agent!",
  "message_id": "optional-id"
}
```

**Server → Client** (Stream response):
```json
// 1. Start
{"event_type": "text_message_start", "message_id": "msg_1", ...}

// 2. Chunks (many)
{"event_type": "text_message_chunk", "content": "Hello", ...}
{"event_type": "text_message_chunk", "content": " there", ...}

// 3. Complete
{"event_type": "text_message_complete", "content": "Hello there!", ...}
```

## 🚢 Production Deployment

### Environment Variables

```bash
# .env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_URL=https://your-domain.com
CHUNK_SIZE=10
```

### Docker Production

```bash
# Build for production
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Performance Tuning

- **Chunk Size**: Balance between smoothness and latency
- **WebSocket Buffer**: Increase for high-throughput scenarios
- **Connection Pooling**: For multiple concurrent users

## 📈 Metrics & Monitoring

### Key Metrics

- WebSocket connection count
- Message throughput (msgs/sec)
- Average streaming latency
- Error rate

### Logging

Backend logs include:
- WebSocket connections/disconnections
- Message processing times
- Streaming event counts
- Errors and exceptions

## 🔗 Next Steps

After mastering streaming chat, explore:

1. **HITL Approval** (`../hitl-approval/`) - Add approval workflows
2. **Tool Dashboard** (`../tool-dashboard/`) - Visualize tool execution
3. **Multi-Agent** (`../multi-agent/`) - Coordinate multiple agents

## 📄 License

Apache 2.0 - See [LICENSE](../../../../LICENSE)

## 🔗 Resources

- [AG-UI Protocol Specification](../../../../docs/agui-protocol.md)
- [Agenkit Documentation](https://docs.agenkit.dev)
- [AG-UI Example Gallery](../)

---

**Built with ❤️ using Agenkit**
