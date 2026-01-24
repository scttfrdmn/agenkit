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
**Directory**: [`collaborative-editor/`](./collaborative-editor/)
**Features**: State synchronization, conflict resolution, real-time collaboration, AI writing assistant
**Use Case**: Agent and user co-editing documents with live updates and AI suggestions

### 5. Multimodal Agent
**Directory**: [`multimodal-agent/`](./multimodal-agent/)
**Features**: Image analysis, file uploads, document processing, drag-and-drop support
**Use Case**: Data analysis agent handling images, documents, code, and data files

### 6. Multi-Agent Coordination
**Directory**: [`multi-agent/`](./multi-agent/)
**Features**: Parallel agent execution, task delegation, result aggregation
**Use Case**: Complex workflows requiring specialized agents (research, calculation, analysis, writing)

### 7. Customer Support Bot
**Directory**: [`support-bot/`](./support-bot/)
**Features**: Ticket management, context tracking, escalation logic, knowledge base
**Use Case**: Support agent with automatic escalation to human operators based on complexity

### 8. Code Assistant
**Directory**: [`code-assistant/`](./code-assistant/)
**Features**: Documentation search, code generation, testing
**Use Case**: Developer productivity tool with code understanding

## 🚀 Quick Start

Each example includes:
- **Backend**: FastAPI server with AG-UI protocol integration
- **Frontend**: Modern vanilla JavaScript UI with WebSocket streaming
- **Docker**: Complete Docker Compose setup with health checks
- **README**: Detailed setup and usage instructions

### Running an Example

```bash
# Choose an example
cd examples/agui/hitl-approval

# Start with Docker (recommended)
docker-compose up --build

# Then open in browser
open http://localhost:3000

# Or run locally
# Terminal 1 - Backend
cd backend
uv pip install -r requirements.txt
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend (serves static files)
cd frontend
python -m http.server 3000
```

## 🎯 Features Demonstrated

| Example | Streaming | HITL | Tools | State Mgmt | Multimodal | Multi-Agent | LOC |
|---------|-----------|------|-------|------------|------------|-------------|-----|
| HITL Approval | ✅ | ✅ | ✅ | | | | ~1,200 |
| Streaming Chat | ✅ | | | ✅ | | | ~800 |
| Tool Dashboard | ✅ | | ✅ | | | | ~1,100 |
| Collaborative Editor | ✅ | | | ✅ | | | ~1,500 |
| Multimodal Agent | ✅ | | ✅ | | ✅ | | ~1,200 |
| Multi-Agent | ✅ | ✅ | ✅ | ✅ | | ✅ | ~1,400 |
| Support Bot | ✅ | ✅ | ✅ | ✅ | | | ~1,100 |
| Code Assistant | ✅ | | ✅ | ✅ | | | ~900 |

**Total**: 8 examples, ~9,200 lines of code, 100% production-ready

## 📖 Architecture

All examples follow a consistent architecture:

```
example-name/
├── backend/
│   ├── main.py           # FastAPI app with AG-UI protocol
│   ├── agent.py          # Agent implementation
│   ├── requirements.txt  # Python dependencies (fastapi, uvicorn, websockets)
│   └── Dockerfile        # Backend container (Python 3.12-slim)
├── frontend/
│   ├── index.html        # Single-page UI with embedded CSS
│   ├── client.js         # AG-UI WebSocket client
│   └── Dockerfile        # Frontend container (nginx)
├── docker-compose.yml    # Orchestrates backend + frontend
└── README.md             # Setup and usage instructions
```

**Key Design Decisions**:
- **Vanilla JavaScript**: No build tools required, easy to understand and modify
- **Single HTML file**: Entire UI in one file for simplicity
- **WebSocket transport**: Real-time bidirectional communication
- **Nginx for frontend**: Production-ready static file serving
- **Health checks**: Both services include health endpoints for Docker

## 🛠️ Technology Stack

**Backend**:
- **Agenkit 0.49+**: Agent framework with AG-UI protocol support
- **FastAPI 0.115+**: Modern async Python web framework
- **WebSockets**: Real-time streaming transport (websockets 14.1+)
- **Uvicorn**: ASGI server with WebSocket support

**Frontend**:
- **Vanilla JavaScript**: No frameworks, no build tools - just ES6+
- **HTML5**: Semantic markup with embedded CSS
- **CSS3**: Modern styling with gradients, animations, flexbox/grid
- **WebSocket API**: Native browser WebSocket implementation
- **Nginx**: Production-ready static file serving (Docker deployments)

**Infrastructure**:
- **Docker Compose**: Multi-container orchestration
- **Health Checks**: Automatic service monitoring and restart
- **Python 3.12+**: Modern Python with async/await support

## 📡 AG-UI Protocol Overview

The AG-UI (Agent-User Interface) protocol enables real-time streaming communication between agents and frontends.

### Event Types

All examples use these standard AG-UI events:

| Event Type | Direction | Purpose | Example Data |
|------------|-----------|---------|--------------|
| `metadata` | Agent → UI | Initial connection info | `{"agent_name": "...", "capabilities": [...]}` |
| `text_message_start` | Agent → UI | Begin new message | `{}` |
| `text_message_chunk` | Agent → UI | Streaming text content | `{"content": "Hello"}` |
| `text_message_complete` | Agent → UI | Message finished | `{"metadata": {...}}` |
| `interrupt` | Agent → UI | Request user input | `{"interrupt_id": "...", "data": {...}}` |
| `interrupt_response` | UI → Agent | User's response | `{"interrupt_id": "...", "action": "approve"}` |
| `error` | Agent → UI | Error occurred | `{"error": "...", "code": 500}` |

### Message Flow

**Simple Streaming** (Streaming Chat, Code Assistant):
```
1. User sends: {type: "message", message: "Hello"}
2. Agent emits: {event_type: "text_message_start"}
3. Agent emits: {event_type: "text_message_chunk", content: "Hi"}
4. Agent emits: {event_type: "text_message_chunk", content: " there"}
5. Agent emits: {event_type: "text_message_chunk", content: "!"}
6. Agent emits: {event_type: "text_message_complete", metadata: {...}}
```

**HITL Flow** (HITL Approval, Support Bot):
```
1. User sends: {type: "message", message: "Buy 100 shares"}
2. Agent emits: {event_type: "text_message_start"}
3. Agent emits: {event_type: "text_message_chunk", content: "Analyzing..."}
4. Agent emits: {event_type: "interrupt", interrupt_id: "abc", data: {proposal: "..."}}
   [Agent pauses, waiting for user response]
5. User sends: {type: "interrupt_response", interrupt_id: "abc", action: "approve"}
6. Agent emits: {event_type: "text_message_chunk", content: "Executing..."}
7. Agent emits: {event_type: "text_message_complete", metadata: {...}}
```

**Multimodal Flow** (Multimodal Agent):
```
1. User sends: {type: "image", message: "Analyze this", image_data: "base64...", ...}
2. Agent emits: {event_type: "text_message_start"}
3. Agent emits: {event_type: "text_message_chunk", content: "Processing image..."}
4. Agent emits: {event_type: "text_message_chunk", content: "\nDetected: ..."}
5. Agent emits: {event_type: "text_message_complete", metadata: {image_analysis: {...}}}
```

### Transport Layers

AG-UI protocol is transport-agnostic. These examples use WebSocket, but SSE (Server-Sent Events) and HTTP polling are also supported.

**WebSocket** (used in all examples):
- ✅ Bidirectional (agent can request input)
- ✅ Low latency
- ✅ Efficient for streaming
- ❌ More complex than SSE

**SSE** (alternative, not shown):
- ✅ Simpler than WebSocket
- ✅ Auto-reconnection built-in
- ❌ Unidirectional (UI → Agent requires separate HTTP)
- ✅ Better for read-only streaming

---

## 📝 Common Patterns

### 1. Setting Up AG-UI Backend

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from agenkit import Agent, Message
from agenkit.protocols.agui import AGUIAdapter
from agenkit.protocols.agui.transports import WebSocketMessageFormat

# Global state (initialized in lifespan)
agent = None
adapter = None
formatter = WebSocketMessageFormat()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, adapter  # noqa: PLW0603
    agent = MyAgent()
    adapter = AGUIAdapter(agent, agent_name="MyAgent", chunk_size=20)
    yield

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    # Send initial metadata
    await websocket.send_text(
        formatter.format_event({
            "event_type": "metadata",
            "data": {
                "agent_name": "MyAgent",
                "capabilities": agent.capabilities,
            },
        })
    )
    # Handle messages
    while True:
        data = await websocket.receive_json()
        if data.get("type") == "message":
            msg = Message(role="user", content=data.get("message", ""))
            async for event in adapter.stream_events(msg, emit_metadata=False):
                await websocket.send_text(formatter.format_event(event))
```

### 2. Connecting from Frontend (Vanilla JavaScript)

```javascript
class MyClient {
    constructor() {
        this.ws = new WebSocket('ws://localhost:8000/ws');
        this.currentMsg = '';
        this.currentEl = null;

        this.ws.onopen = () => console.log('Connected');
        this.ws.onmessage = (e) => this.handleMessage(JSON.parse(e.data));
    }

    handleMessage(msg) {
        if (msg.event_type === 'text_message_chunk') {
            if (!this.currentEl) {
                this.currentEl = document.createElement('div');
                this.currentEl.className = 'message agent';
                document.getElementById('messages').appendChild(this.currentEl);
            }
            this.currentMsg += msg.content;
            this.currentEl.textContent = this.currentMsg;
        } else if (msg.event_type === 'text_message_complete') {
            this.currentMsg = '';
            this.currentEl = null;
        }
    }

    send(text) {
        this.ws.send(JSON.stringify({type: 'message', message: text}));
    }
}

const client = new MyClient();
```

### 3. Handling HITL Interrupts

```javascript
handleMessage(msg) {
    if (msg.event_type === 'interrupt') {
        // Show approval dialog
        const dialog = document.getElementById('approval-dialog');
        dialog.querySelector('.proposal').textContent = msg.data.proposal;
        dialog.style.display = 'block';

        // Handle approval/rejection
        dialog.querySelector('.approve').onclick = () => {
            this.ws.send(JSON.stringify({
                type: 'interrupt_response',
                interrupt_id: msg.interrupt_id,
                action: 'approve',
                context: {feedback: 'Approved by user'}
            }));
            dialog.style.display = 'none';
        };

        dialog.querySelector('.reject').onclick = () => {
            this.ws.send(JSON.stringify({
                type: 'interrupt_response',
                interrupt_id: msg.interrupt_id,
                action: 'reject',
                context: {reason: 'Rejected by user'}
            }));
            dialog.style.display = 'none';
        };
    }
}
```

### 4. Processing Multimodal Content

```javascript
// File upload handler
async handleFileSelect(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const base64Data = e.target.result.split(',')[1];
        this.ws.send(JSON.stringify({
            type: file.type.startsWith('image/') ? 'image' : 'file',
            message: 'Analyze this file',
            [file.type.startsWith('image/') ? 'image_data' : 'file_data']: base64Data,
            [file.type.startsWith('image/') ? 'image_format' : 'file_name']:
                file.type.startsWith('image/') ? file.type.split('/')[1] : file.name,
            [file.type.startsWith('image/') ? 'image_size' : 'file_size']: file.size
        }));
    };
    reader.readAsDataURL(file);
}
```

## ⚡ Performance & Best Practices

### Streaming Configuration

**chunk_size parameter**: Controls how many characters are sent per chunk
- `chunk_size=1`: Character-by-character (slowest, most granular)
- `chunk_size=10`: Token-by-token (good balance, used in Streaming Chat)
- `chunk_size=20`: Default (faster, less network overhead)
- `chunk_size=50+`: Fast streaming (less granular, better performance)

**Network optimization**:
- Use debouncing for high-frequency updates (300ms in Collaborative Editor)
- Batch tool status updates when executing multiple tools
- Close WebSocket connections gracefully on page unload

### Production Checklist

Before deploying to production:

- [ ] Add authentication to WebSocket endpoints
- [ ] Implement rate limiting to prevent abuse
- [ ] Add CORS configuration for allowed origins
- [ ] Enable HTTPS/WSS for secure connections
- [ ] Set up monitoring and logging
- [ ] Configure health checks for load balancers
- [ ] Add error boundaries in frontend
- [ ] Implement reconnection logic for dropped connections
- [ ] Add request timeouts and circuit breakers
- [ ] Test with multiple concurrent users

### Docker Tips

**Health checks**: All examples include health endpoints
```bash
# Check backend health
curl http://localhost:8000/health

# View container logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Resource limits**: Add to docker-compose.yml
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

**Development mode**: Use volume mounts for live reload
```yaml
volumes:
  - ./backend:/app  # Backend code changes reload automatically
```

---

## 🔧 Troubleshooting

### WebSocket Connection Failed

**Symptom**: Frontend can't connect to backend
```
WebSocket connection failed: Error during WebSocket handshake
```

**Solutions**:
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify WebSocket URL in client.js matches backend port
3. Check CORS middleware allows WebSocket upgrades
4. Ensure no firewall blocking port 8000

### Messages Not Streaming

**Symptom**: Messages appear all at once instead of streaming

**Solutions**:
1. Verify AGUIAdapter is created with correct chunk_size
2. Check emit_metadata=False in stream_events() call
3. Ensure frontend handles 'text_message_chunk' events
4. Verify formatter.format_event() is called on each event

### Docker Containers Won't Start

**Symptom**: `docker-compose up` fails

**Solutions**:
```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up

# Check for port conflicts
lsof -i :8000  # Backend port
lsof -i :3000  # Frontend port

# View detailed logs
docker-compose logs --tail=50 backend
```

### Import Errors in Backend

**Symptom**: `ModuleNotFoundError: No module named 'agenkit'`

**Solutions**:
```bash
# Install agenkit in development mode
cd /path/to/agenkit
uv pip install -e .

# Or install from PyPI
uv pip install agenkit>=0.49.0
```

### Frontend Shows Blank Page

**Symptom**: Opening http://localhost:3000 shows nothing

**Solutions**:
1. Check nginx logs: `docker-compose logs frontend`
2. Verify index.html exists in frontend/ directory
3. Check nginx configuration in Dockerfile
4. Try accessing directly: `python -m http.server 3000` from frontend/

---

## 📊 Example Details

### 1. HITL Approval Workflow
**Complexity**: Advanced | **Lines of Code**: ~1,200

Demonstrates bidirectional agent-user interaction where the agent requests approval before taking high-risk actions. Perfect for financial, medical, or legal applications.

**Key Features**:
- Confidence scoring (0-100) for trades
- Automatic approval gates (>80% confidence = auto-approve)
- User approval UI with accept/reject/modify options
- Market data simulation
- Interrupt event handling

**Learn**: How to build agents that pause and wait for human input

---

### 2. Streaming Chat
**Complexity**: Beginner | **Lines of Code**: ~800

Classic chatbot with token-by-token streaming responses. Great starting point for understanding AG-UI protocol basics.

**Key Features**:
- Token-by-token text streaming (chunk_size=10)
- Conversation history with 5-message context
- Typing indicators
- Quick prompt buttons
- Message timestamps

**Learn**: Basic AG-UI event handling and streaming

---

### 3. Tool Visualization Dashboard
**Complexity**: Intermediate | **Lines of Code**: ~1,100

Real-time monitoring of agent tool execution. Essential for debugging and understanding agent behavior.

**Key Features**:
- 4 tools: web_search, calculator, get_weather, query_database
- Real-time tool status (idle → executing → complete/error)
- Execution metrics (time, success rate)
- Animated tool cards with status colors
- Automatic tool selection based on query

**Learn**: Tool instrumentation and real-time status updates

---

### 4. Collaborative Document Editor
**Complexity**: Advanced | **Lines of Code**: ~1,500

AI writing assistant that helps users improve documents with suggestions, expansions, and style improvements.

**Key Features**:
- 6 AI commands: suggest, expand, summarize, grammar, style, complete
- Document state synchronization across clients
- Edit history tracking with undo/redo
- 300ms debounce for network efficiency
- Async locks for concurrent access
- Selection-based operations

**Learn**: State management and multi-client synchronization

---

### 5. Multimodal Agent
**Complexity**: Intermediate | **Lines of Code**: ~1,200

Processes images, documents, code, and data files with intelligent analysis.

**Key Features**:
- Image analysis (object detection, color extraction)
- Document processing (.txt, .pdf, .md)
- Code analysis (.py, .js, .go, .rs, .cpp)
- Data file parsing (.json, .csv, .yaml)
- Drag-and-drop upload
- Base64 file encoding for WebSocket transfer
- File preview with thumbnails

**Learn**: Multimodal content handling and file processing

---

### 6. Multi-Agent Coordination
**Complexity**: Advanced | **Lines of Code**: ~1,400

Orchestrates multiple specialized agents to handle complex queries requiring different expertise.

**Key Features**:
- 4 specialized agents: Research, Calculator, Writer, Analyst
- Intelligent query analysis for agent selection
- Parallel execution using asyncio.gather
- Result aggregation with confidence scores
- Execution planning visualization
- Agent load balancing

**Learn**: Multi-agent systems and parallel processing

---

### 7. Customer Support Bot
**Complexity**: Intermediate | **Lines of Code**: ~1,100

Smart support bot with ticket management and automatic escalation to human operators.

**Key Features**:
- Ticket lifecycle (open → escalated → resolved)
- Conversation history tracking
- Knowledge base with 5 common issues
- Smart escalation logic (complexity, priority, sentiment)
- Issue classification (technical, billing, account, general)
- Priority scoring (low, medium, high, urgent)

**Learn**: Context tracking and escalation workflows

---

### 8. Code Assistant
**Complexity**: Intermediate | **Lines of Code**: ~900

Developer productivity tool for documentation search, code generation, and debugging assistance.

**Key Features**:
- Multi-language support (Python, JavaScript, Go, Rust, TypeScript)
- Code generation with templates
- Documentation search from knowledge base
- Debugging assistance with common solutions
- Best practices recommendations
- Syntax highlighting in responses

**Learn**: Code generation and technical documentation patterns

---

## 🎓 Learning Path

**Beginner**: Start with **Streaming Chat** (#2) to understand basic AG-UI streaming

**Intermediate**: Try **HITL Approval** (#1) to learn bidirectional agent control

**Advanced**: Explore **Multi-Agent** (#6) to see complex coordination patterns

**Full Stack**: Build **Collaborative Editor** (#4) for complete state management

## 🎨 Customizing Examples

All examples are designed to be easily customized for your use case.

### Adding New Agent Capabilities

**Example**: Add sentiment analysis to Support Bot

```python
# In backend/agent.py
async def _analyze_sentiment(self, content: str) -> str:
    """Detect customer sentiment from message."""
    negative_words = ["angry", "frustrated", "terrible", "awful", "hate"]
    positive_words = ["great", "excellent", "love", "perfect", "amazing"]

    neg_count = sum(1 for word in negative_words if word in content.lower())
    pos_count = sum(1 for word in positive_words if word in content.lower())

    if neg_count > pos_count:
        return "negative"
    elif pos_count > neg_count:
        return "positive"
    return "neutral"

# Use in process() method
sentiment = await self._analyze_sentiment(content)
if sentiment == "negative":
    # Auto-escalate frustrated customers
    ticket.escalated = True
```

### Changing Frontend Styling

All examples use inline CSS for simplicity. To customize:

```html
<!-- In frontend/index.html -->
<style>
/* Change color scheme */
body {
    background: linear-gradient(135deg, #667eea, #764ba2);  /* Purple */
    background: linear-gradient(135deg, #56CCF2, #2F80ED);  /* Blue */
    background: linear-gradient(135deg, #11998e, #38ef7d);  /* Green */
}

/* Change message bubble colors */
.message.agent .message-content {
    background: #667eea;  /* Purple */
    color: #fff;
}

/* Adjust fonts */
body {
    font-family: 'Inter', system-ui;  /* Modern */
    font-family: 'Roboto Mono', monospace;  /* Code */
}
</style>
```

### Connecting Real APIs

Replace mock data with real API calls:

```python
# In backend/agent.py

# Before: Mock weather data
def _get_weather_mock(self, location: str) -> dict:
    return {"temp": 72, "condition": "sunny"}

# After: Real weather API
async def _get_weather_real(self, location: str) -> dict:
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.openweathermap.org/data/2.5/weather",
            params={"q": location, "appid": os.getenv("WEATHER_API_KEY")}
        ) as response:
            data = await response.json()
            return {
                "temp": data["main"]["temp"],
                "condition": data["weather"][0]["description"]
            }
```

### Adding Authentication

Secure your WebSocket endpoints:

```python
# In backend/main.py
from fastapi import WebSocket, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token."""
    token = credentials.credentials
    # Add your JWT verification logic here
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

@app.websocket("/ws")
async def ws(websocket: WebSocket, token: str = Depends(verify_token)):
    await websocket.accept()
    # ... rest of WebSocket logic
```

### Scaling to Production

**Database**: Add persistent storage

```python
# Install: uv pip install sqlalchemy asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Use in agent
async def save_ticket(self, ticket: SupportTicket):
    async with AsyncSessionLocal() as session:
        session.add(ticket)
        await session.commit()
```

**Redis**: Add caching layer

```python
# Install: uv pip install redis
import redis.asyncio as redis

redis_client = redis.from_url("redis://localhost:6379")

# Cache agent responses
async def get_cached_response(self, query: str) -> str | None:
    return await redis_client.get(f"response:{query}")

async def cache_response(self, query: str, response: str):
    await redis_client.setex(f"response:{query}", 3600, response)  # 1 hour TTL
```

**Message Queue**: Add async task processing

```python
# Install: uv pip install celery redis
from celery import Celery

celery_app = Celery("tasks", broker="redis://localhost:6379/0")

@celery_app.task
def process_heavy_task(data: dict):
    """Long-running task executed in background."""
    # Your processing logic here
    return result

# Trigger from agent
async def process(self, message: Message):
    task = process_heavy_task.delay({"content": message.content})
    return Message(role="assistant", content=f"Processing... (task_id: {task.id})")
```

---

## 🧪 Testing Your Modifications

After customizing an example:

```bash
# 1. Lint your changes
cd backend
uv run ruff check .
uv run black --check .

# 2. Test locally
docker-compose down
docker-compose up --build

# 3. Verify health
curl http://localhost:8000/health

# 4. Test WebSocket connection
# Open browser console at http://localhost:3000
# Check for: "Connected" message

# 5. Load test (optional)
# Install: npm install -g wscat
wscat -c ws://localhost:8000/ws
> {"type": "message", "message": "Hello"}
```

---

## 🚀 Deployment Options

### Docker Compose (Simplest)

Already configured in all examples:

```bash
# Production mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Kubernetes (Scalable)

**Example deployment** (adapt for your example):

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agui-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agui-backend
  template:
    metadata:
      labels:
        app: agui-backend
    spec:
      containers:
      - name: backend
        image: your-registry/agui-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: WORKERS
          value: "4"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: agui-backend
spec:
  selector:
    app: agui-backend
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

**Deploy**:
```bash
kubectl apply -f k8s/
kubectl get pods
kubectl logs -f deployment/agui-backend
```

### Cloud Platforms

#### Railway (Easiest)

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Deploy:
   ```bash
   cd examples/agui/streaming-chat
   railway init
   railway up
   ```

#### Render

1. Connect GitHub repo
2. Create new Web Service
3. Settings:
   - Build Command: `docker-compose build backend`
   - Start Command: `docker-compose up backend`
   - Port: 8000
4. Deploy

#### Heroku

```bash
# Install Heroku CLI
heroku login
heroku create my-agui-app
heroku stack:set container

# Add Procfile
echo "web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT" > Procfile

# Deploy
git push heroku main
```

#### AWS ECS (Most Control)

1. **Build and push image**:
   ```bash
   aws ecr create-repository --repository-name agui-backend
   docker build -t agui-backend backend/
   docker tag agui-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/agui-backend:latest
   docker push <account>.dkr.ecr.<region>.amazonaws.com/agui-backend:latest
   ```

2. **Create ECS task definition** (JSON):
   ```json
   {
     "family": "agui-backend",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "256",
     "memory": "512",
     "containerDefinitions": [{
       "name": "backend",
       "image": "<account>.dkr.ecr.<region>.amazonaws.com/agui-backend:latest",
       "portMappings": [{"containerPort": 8000}],
       "healthCheck": {
         "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
       }
     }]
   }
   ```

3. **Create service**:
   ```bash
   aws ecs create-service \
     --cluster my-cluster \
     --service-name agui-backend \
     --task-definition agui-backend \
     --desired-count 2 \
     --launch-type FARGATE
   ```

### Monitoring & Observability

**Prometheus + Grafana** (recommended for production):

```python
# Install: uv pip install prometheus-fastapi-instrumentator
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)

# Metrics available at /metrics
# - Request count, latency, errors
# - WebSocket connections
# - Custom agent metrics
```

**Custom metrics**:

```python
from prometheus_client import Counter, Histogram

websocket_connections = Counter(
    "websocket_connections_total",
    "Total WebSocket connections"
)

message_processing_time = Histogram(
    "message_processing_seconds",
    "Time to process messages"
)

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    websocket_connections.inc()
    # ... rest of logic

async def process(self, message: Message):
    with message_processing_time.time():
        # ... processing logic
```

**Logging** (structured JSON logs for cloud platforms):

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": record.created,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
```

### Environment Variables

Create `.env` file (don't commit to git):

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0

# API Keys
OPENAI_API_KEY=sk-...
WEATHER_API_KEY=...

# CORS
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Load in app:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    environment: str = "development"
    debug: bool = False
    database_url: str
    redis_url: str
    openai_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 🔗 Resources

- [AG-UI Protocol Specification](../../docs/agui-protocol.md)
- [Agenkit Documentation](https://docs.agenkit.dev)
- [API Reference](https://docs.agenkit.dev/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [WebSocket API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Community Discord](https://discord.gg/agenkit)

## 📄 License

Apache 2.0 - See [LICENSE](../../LICENSE) for details

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

---

**Built with ❤️ by the Agenkit community**
