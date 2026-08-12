# Human-in-the-Loop (HITL) Approval Workflow Example

Production-ready example demonstrating bidirectional human-in-the-loop approval workflow using AG-UI protocol.

## 🎯 Overview

This example shows a financial trading agent that requires human approval for low-confidence trades. The agent analyzes market conditions, proposes trades, and pauses execution to wait for user approval when confidence is below 80%.

### Key Features

- ✅ **Bidirectional HITL**: Agent pauses and waits for user decision
- ✅ **Real-time Streaming**: Token-by-token response streaming
- ✅ **Confidence-based Gates**: Automatic approval for high-confidence trades
- ✅ **Multiple Actions**: Approve, Reject, or Edit proposed trades
- ✅ **Timeout Handling**: Automatic rejection after 5 minutes of inactivity
- ✅ **Production Ready**: Proper error handling, logging, and monitoring

## 🏗️ Architecture

```
┌─────────────────┐                  ┌──────────────────┐
│                 │   WebSocket/SSE  │                  │
│  React Frontend │◄────────────────►│  FastAPI Backend │
│                 │                  │                  │
│  - Approval UI  │                  │  - TradingAgent  │
│  - Real-time    │                  │  - AG-UI Adapter │
│    Updates      │                  │  - HITL Support  │
└─────────────────┘                  └──────────────────┘
        │                                      │
        │                                      │
        ▼                                      ▼
  User Decision                         Confidence Check
  (Approve/Reject/Edit)                 (<80% = approval)
```

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- uv or pip (Python package manager)
- npm or yarn (Node package manager)

## 🚀 Quick Start

### Option 1: Run with Docker (Recommended)

```bash
# Build and start both backend and frontend
docker-compose up --build

# Access the application
open http://localhost:3000
```

### Option 2: Run Locally

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (including agenkit from parent)
pip install -e ../../../../  # Install agenkit locally
pip install -r requirements.txt

# Start FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`
WebSocket endpoint: `ws://localhost:8000/ws`

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:3000`

## 🎮 Usage

### 1. Start the Application

Open http://localhost:3000 in your browser.

### 2. Try Different Trading Strategies

**Conservative Trade (High Confidence - Auto-Approved)**
```
Execute a conservative trade strategy
```
✅ Agent confidence: 92% - Trade executes automatically

**Moderate Trade (Medium Confidence - Requires Approval)**
```
Analyze this moderate trading opportunity
```
⚠️ Agent confidence: 75% - User approval required

**Aggressive Trade (Low Confidence - Requires Approval)**
```
Execute an aggressive high-risk trade
```
⚠️ Agent confidence: 45% - User approval required

### 3. Approval Workflow

When agent confidence < 80%:

1. **Interrupt Event Emitted**
   - Agent pauses execution
   - Frontend receives Interrupt event
   - Approval UI appears

2. **User Makes Decision**
   - **Approve**: Accept trade as proposed
   - **Reject**: Cancel the trade
   - **Edit**: Modify trade parameters

3. **Agent Resumes**
   - Executes trade if approved
   - Returns rejection message if rejected
   - Executes modified trade if edited

## 🔧 Configuration

### Backend Configuration

Edit `backend/main.py`:

```python
adapter = AGUIHumanInLoopAdapter(
    trading_agent,
    bidirectional=True,
    approval_threshold=0.8,  # Adjust confidence threshold
    timeout=300.0,  # Timeout in seconds
)
```

### Agent Behavior

Edit `backend/agent.py` to customize:
- Trade confidence calculations
- Market analysis logic
- Risk assessment criteria

## 📊 Example Interactions

### High Confidence Trade (No Approval)

**User**: `Execute a conservative trade`

**Agent Response** (auto-approved):
```
📊 Trade Proposal
Action: BUY
Symbol: AAPL
Quantity: 10 shares
Price: $175.50
Confidence: 92.0%
Status: ✅ Approved (high confidence)
```

### Low Confidence Trade (Requires Approval)

**User**: `Execute an aggressive trade`

**Agent Response** (pauses for approval):
```
📊 Trade Proposal
Action: BUY
Symbol: TSLA
Quantity: 100 shares
Price: $850.00
Confidence: 45.0%
Status: ⚠️ Approval Required

[Approve] [Reject] [Edit]
```

**User Approves**:
```
✅ Trade Approved
Executing: BUY 100 shares of TSLA at $850.00
```

**User Rejects**:
```
❌ Trade Rejected
Reason: Exceeds risk tolerance
```

**User Edits**:
```
📝 Trade Modified
Original: BUY 100 shares at $850.00
Modified: BUY 50 shares at $850.00
✅ Executing modified trade
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/
```

### Frontend Tests

```bash
cd frontend
npm test
```

### Integration Tests

```bash
# Start backend
cd backend && uvicorn main:app &

# Run integration tests
cd frontend && npm run test:integration
```

## 📚 Code Walkthrough

### Backend: AG-UI Integration

```python
# Create agent
trading_agent = TradingAgent()

# Wrap with bidirectional HITL adapter
adapter = AGUIHumanInLoopAdapter(
    trading_agent,
    bidirectional=True,
    approval_threshold=0.8,
)

# Stream events
async for event in adapter.stream_events(message):
    if isinstance(event, Interrupt):
        # Agent paused - waiting for user decision
        await websocket.send_text(format_event(event))

    elif isinstance(event, TextMessageChunk):
        # Stream response content
        await websocket.send_text(format_event(event))
```

### Frontend: Handling Interrupts

```typescript
client.on('interrupt', async (interrupt) => {
  // Show approval UI
  const decision = await showApprovalDialog(interrupt);

  // Send response back to agent
  await client.sendInterruptResponse({
    interrupt_id: interrupt.interrupt_id,
    action: decision.action,  // APPROVE, REJECT, or EDIT
    context: { feedback: decision.feedback }
  });
});
```

## 🐛 Troubleshooting

### WebSocket Connection Failed

```bash
# Check if backend is running
curl http://localhost:8000/health

# Check WebSocket endpoint
wscat -c ws://localhost:8000/ws
```

### Agent Not Pausing for Approval

- Verify `bidirectional=True` in adapter configuration
- Check that trade confidence < approval_threshold (0.8)
- Review backend logs for interrupt events

### Timeout Issues

- Increase timeout in adapter configuration
- Check network latency
- Review browser console for errors

## 📖 API Reference

### WebSocket Messages

**Client → Server**:
```json
{
  "type": "message",
  "message": "Execute a trade",
  "message_id": "msg_123"
}
```

**Server → Client** (Interrupt):
```json
{
  "event_type": "interrupt",
  "interrupt_id": "int_456",
  "reason": "approval_required",
  "message": "Agent confidence (45%) below threshold (80%)",
  "actions": ["APPROVE", "REJECT", "EDIT"],
  "context": {
    "confidence": 0.45,
    "proposed_response": "BUY 100 TSLA..."
  }
}
```

**Client → Server** (Interrupt Response):
```json
{
  "type": "interrupt_response",
  "interrupt_id": "int_456",
  "action": "APPROVE",
  "context": {
    "feedback": "Trade approved by risk manager"
  }
}
```

## 🔐 Security Considerations

- ✅ Input validation on all user messages
- ✅ Timeout protection against hung approvals
- ✅ CORS configuration for production
- ✅ Rate limiting (add in production)
- ✅ Authentication (add in production)

## 🚢 Production Deployment

### Environment Variables

```bash
# .env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_URL=https://your-domain.com
APPROVAL_THRESHOLD=0.8
APPROVAL_TIMEOUT=300
```

### Docker Deployment

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests.

## 📈 Monitoring

### Metrics

- Approval request rate
- Approval/rejection ratio
- Average decision time
- Timeout rate

### Logging

Backend logs include:
- WebSocket connections
- Message processing
- Interrupt events
- Approval decisions
- Errors and exceptions

## 🤝 Contributing

Improvements welcome! See [CONTRIBUTING.md](../../../../CONTRIBUTING.md).

## 📄 License

Apache 2.0 - See [LICENSE](../../../../LICENSE).

## 🔗 Resources

- [AG-UI Protocol Specification](../../../../docs/agui-protocol.md)
- [Agenkit Documentation](https://docs.agenkit.dev)
- [AG-UI Example Gallery](../)

---

**Built with ❤️ using Agenkit**
