# AG-UI Protocol Examples

Examples demonstrating the AG-UI (Agent-User Interaction) protocol with Human-in-the-Loop (HITL) support.

## Overview

These examples show how to integrate agents with AG-UI protocol for streaming communication with human approval workflows. The AG-UI protocol uses event-driven streaming to enable real-time interaction between agents and frontends.

## Core Concepts

### AG-UI Protocol
- **Event-based streaming**: Structured events for agent-to-frontend communication
- **Multiple transports**: HTTP/SSE and WebSocket support
- **Interrupt events**: Request human intervention during agent execution
- **Metadata events**: Agent capabilities and configuration

### Human-in-the-Loop (HITL)
- **Confidence-based approval**: Requests approval when agent confidence is below threshold
- **Interrupt notifications**: Emits Interrupt events when approval is involved
- **Approval decisions**: Approved, rejected, or approved with modifications
- **Audit trail**: Comprehensive logging of approval decisions

## Examples

### 1. Basic HITL (`01_basic_hitl.py`)

**Focus**: Core HITL concepts with AG-UI events

**What it demonstrates**:
- `AGUIHumanInLoopAdapter` wrapping agents
- Interrupt events for approval notifications
- High vs low confidence handling
- Enabling/disabling interrupt events

**Run**:
```bash
uv run python examples/protocols/agui/01_basic_hitl.py
```

**Key concepts**:
- Confidence threshold (default: 0.8)
- Interrupt event structure
- MetadataEvent with HITL capabilities
- Approval status in event context

**Output**: Console-based demonstration showing event flow


### 2. SSE Transport HITL (`02_sse_transport_hitl.py`)

**Focus**: HTTP Server-Sent Events with HITL

**What it demonstrates**:
- HTTP server with SSE streaming endpoint
- Interrupt events sent via SSE
- Web-based client interface
- Real-world deployment pattern

**Run**:
```bash
# Start server
uv run python examples/protocols/agui/02_sse_transport_hitl.py

# In browser: http://localhost:8080/

# Or test with curl:
curl "http://localhost:8080/chat/stream?message=Should%20I%20do%20this?"
```

**Requirements**:
```bash
pip install aiohttp
```

**Endpoints**:
- `/` - Web UI for interactive testing
- `/chat/stream` - SSE streaming endpoint
- `/health` - Health check

**Use cases**:
- Web applications with real-time agent responses
- Dashboard integrations
- Progressive enhancement (works without WebSocket)


### 3. WebSocket HITL (`03_websocket_hitl.py`)

**Focus**: WebSocket bidirectional communication with HITL

**What it demonstrates**:
- WebSocket server for full-duplex communication
- Interrupt events sent to clients
- JSON message protocol
- Test client included

**Run**:
```bash
# Start server
uv run python examples/protocols/agui/03_websocket_hitl.py

# Run test client (separate terminal)
uv run python examples/protocols/agui/03_websocket_hitl.py test

# Or test with websocat:
echo '{"type": "message", "content": "Should I proceed?"}' | websocat ws://localhost:8765
```

**Requirements**:
```bash
pip install websockets
```

**Message format**:
```json
{
  "type": "message",
  "content": "your message here"
}
```

**Use cases**:
- Real-time chat applications
- Interactive agent interfaces
- Mobile applications
- Low-latency communication


### 4. Advanced Approval Patterns (`04_advanced_approval.py`)

**Focus**: Complex approval logic and workflows

**What it demonstrates**:
- Multi-tiered approval (auto, manager, director, executive)
- Contextual approval based on transaction type
- Approval with content modifications
- Rejection scenarios with detailed feedback
- Approval audit trail for compliance

**Run**:
```bash
uv run python examples/protocols/agui/04_advanced_approval.py
```

**Key patterns**:
- **Tiered approval**: Different approval levels based on risk/amount
- **Contextual decisions**: Transaction type, history, and patterns
- **Modifications**: Approve with additional safeguards
- **Audit logging**: Comprehensive compliance trail

**Use cases**:
- Financial transaction approval
- Content moderation workflows
- Compliance and regulatory systems
- Multi-level authorization workflows


## Quick Start

### 1. Install dependencies

```bash
# For basic examples
cd agenkit

# For SSE example
pip install aiohttp

# For WebSocket example
pip install websockets
```

### 2. Run basic example

```bash
uv run python examples/protocols/agui/01_basic_hitl.py
```

### 3. Try the web interface

```bash
# Start SSE server
uv run python examples/protocols/agui/02_sse_transport_hitl.py

# Open browser
open http://localhost:8080/
```

## Event Flow

### High Confidence (No Approval)

```
User Message
    ↓
MetadataEvent (agent capabilities)
    ↓
TextMessageStart
    ↓
TextMessageChunk (x N)
    ↓
TextMessageComplete
```

No Interrupt event emitted because confidence >= threshold.

### Low Confidence (Approval Required)

```
User Message
    ↓
MetadataEvent (agent capabilities)
    ↓
[Agent processes - approval happens]
    ↓
Interrupt (approval notification)
    ↓
TextMessageStart
    ↓
TextMessageChunk (x N)
    ↓
TextMessageComplete
```

Interrupt event emitted with approval decision in context.

## Interrupt Event Structure

```python
{
    "interrupt_id": "uuid",
    "reason": "APPROVAL_REQUIRED",
    "message": "Approval approved (confidence: 0.60)",
    "context": {
        "approval_status": "approved",  # or "rejected", "approved_with_modifications"
        "confidence": 0.6,
        "approval_threshold": 0.8,
        "approval_needed": true
    },
    "actions": [],  # Empty - decision already made
    "timeout_seconds": null
}
```

## Customization

### Custom Approval Function

```python
async def my_approval_func(request: ApprovalRequest) -> ApprovalResponse:
    """Custom approval logic."""
    # Access request data
    confidence = request.confidence
    message = request.message
    context = request.context

    # Make approval decision
    approved = your_decision_logic()

    # Optional: Modify message
    if approved and needs_modification:
        modified_msg = Message(
            role="assistant",
            content=f"{message.content} [MODIFIED]",
            metadata={**message.metadata, "modified": True}
        )
        return ApprovalResponse(
            approved=True,
            feedback="Approved with modifications",
            modified_message=modified_msg
        )

    return ApprovalResponse(
        approved=approved,
        feedback="Your feedback here"
    )
```

### Custom Agent

```python
class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "MyAgent"

    @property
    def capabilities(self) -> list[str]:
        return ["my-capability"]

    async def process(self, message: Message) -> Message:
        # Process message
        # Calculate confidence (0.0 to 1.0)
        confidence = calculate_confidence()

        return Message(
            role="assistant",
            content="Response",
            metadata={"confidence": confidence}
        )
```

### Configure HITL

```python
from agenkit.patterns.human_in_loop import HumanInLoopAgent, HumanInLoopConfig
from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter

# Create HumanInLoopAgent
hil_agent = HumanInLoopAgent(
    HumanInLoopConfig(
        agent=my_agent,
        approval_func=my_approval_func,
        approval_threshold=0.8,  # Require approval when confidence < 0.8
    )
)

# Wrap with AG-UI adapter
adapter = AGUIHumanInLoopAdapter(
    hil_agent,
    agent_name="MyAgent",
    emit_interrupts=True  # Set to False to disable Interrupt events
)

# Stream events
async for event in adapter.stream_events(message):
    # Handle events
    if isinstance(event, Interrupt):
        # Handle approval notification
        pass
```

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  (Web UI, Mobile App, CLI)                                  │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ HTTP/SSE or WebSocket
                │
┌───────────────▼─────────────────────────────────────────────┐
│                     Transport Layer                          │
│  • AGUISSEEndpoint (HTTP/SSE)                               │
│  • AGUIWebSocketHandler (WebSocket)                         │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ AG-UI Events
                │
┌───────────────▼─────────────────────────────────────────────┐
│              AGUIHumanInLoopAdapter                          │
│  • Wraps HumanInLoopAgent                                   │
│  • Emits Interrupt events for approvals                     │
│  • Streams TextMessage events                               │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ Message Processing
                │
┌───────────────▼─────────────────────────────────────────────┐
│                HumanInLoopAgent                              │
│  • Checks confidence threshold                              │
│  • Calls approval_func when needed                          │
│  • Returns approved/rejected response                       │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ Agent Processing
                │
┌───────────────▼─────────────────────────────────────────────┐
│                    Base Agent                                │
│  • Business logic                                           │
│  • Returns response with confidence                         │
└─────────────────────────────────────────────────────────────┘
```

## Best Practices

### 1. Confidence Calculation

Always include confidence in agent responses:

```python
return Message(
    role="assistant",
    content="Response",
    metadata={"confidence": 0.85}  # Required for HITL
)
```

### 2. Approval Threshold Selection

- **0.9+**: Very high confidence only
- **0.8**: Recommended default (balance of autonomy and oversight)
- **0.7**: More frequent approvals
- **< 0.7**: Mostly manual approval

### 3. Async Approval Functions

Use async approval functions for I/O operations:

```python
async def approval_func(request: ApprovalRequest) -> ApprovalResponse:
    # Async operations (DB queries, API calls)
    await check_approval_database()
    return ApprovalResponse(approved=True)
```

### 4. Error Handling

Handle approval failures gracefully:

```python
try:
    async for event in adapter.stream_events(message):
        # Process event
        pass
except Exception as e:
    # Log error
    # Send error event to client
    pass
```

### 5. Audit Logging

Log all approval decisions for compliance:

```python
approval_log.append({
    "timestamp": datetime.now(),
    "confidence": confidence,
    "decision": "approved",
    "user": user_id,
    "agent": agent_name,
})
```

## Testing

### Unit Tests

See `tests/protocols/agui/test_hitl.py` for comprehensive test examples.

### Integration Testing

```bash
# Test basic HITL
uv run pytest tests/protocols/agui/test_hitl.py -v

# Test SSE transport (requires server running)
curl http://localhost:8080/chat/stream

# Test WebSocket (requires server running)
echo '{"type": "message", "content": "test"}' | websocat ws://localhost:8765
```

## Troubleshooting

### No Interrupt Events

**Problem**: Not seeing Interrupt events when expected

**Check**:
1. Agent confidence is below threshold
2. `emit_interrupts=True` in adapter
3. Agent is a HumanInLoopAgent (not regular agent)
4. Response metadata includes `approval_status`

### Approval Not Triggering

**Problem**: Approval function not being called

**Check**:
1. Confidence < approval_threshold
2. approval_func is properly async
3. HumanInLoopConfig is correct
4. Agent returns confidence in metadata

### SSE Connection Issues

**Problem**: SSE stream not connecting or dropping

**Check**:
1. Server is running on correct port
2. No proxy buffering SSE responses
3. Client properly handles `text/event-stream`
4. Firewall allows connections

## References

- **AG-UI Protocol**: `agenkit/protocols/agui/`
- **HITL Pattern**: `agenkit/patterns/human_in_loop.py`
- **HITL Adapter**: `agenkit/protocols/agui/hitl.py`
- **Tests**: `tests/protocols/agui/test_hitl.py`
- **Core Documentation**: `docs/` directory

## Next Steps

1. **Production Deployment**: See deployment examples in `examples/deployment/`
2. **Security**: Review `SECURITY.md` for authentication patterns
3. **Monitoring**: Add observability with `agenkit.observability`
4. **Scaling**: Implement load balancing and failover

## Support

- **Issues**: https://github.com/anthropics/agenkit/issues
- **Documentation**: `docs/`
- **Contributing**: `.github/CONTRIBUTING.md`
