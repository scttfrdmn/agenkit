# AG-UI Protocol Examples (Go)

Examples demonstrating the AG-UI (Agent-User Interaction) protocol in Go.

The AG-UI protocol provides structured, streaming communication between agents and user interfaces, with support for human-in-the-loop workflows, interrupts, and rich event types.

## Examples

### 1. Basic HITL (`01_basic_hitl.go`)

Basic Human-in-the-Loop integration demonstrating:
- AGUIHumanInLoopAdapter wrapping HumanInLoopAgent
- Interrupt events for approval decisions
- HITL capabilities in metadata
- Confidence-based approval thresholds

**Run:**
```bash
cd agenkit-go/examples/protocols/agui
go run 01_basic_hitl.go
```

**Scenarios:**
1. **High Confidence** - Agent bypasses approval (no interrupt)
2. **Low Confidence** - Approval required, interrupt emitted
3. **Rejection** - Approval rejected, rejection interrupt
4. **Disabled Interrupts** - HITL works without interrupt events

**Key Concepts:**
- Interrupt events signal approval decisions
- Metadata includes approval_status, confidence, threshold
- Interrupts can be disabled while maintaining approval logic

### 2. SSE Transport HITL (`02_sse_transport_hitl.go`)

HTTP Server-Sent Events transport with HITL support:
- AGUISSEHandler for HTTP/SSE streaming
- Browser-friendly unidirectional streaming
- CORS support for web frontends
- Interrupt events over SSE
- Real-world deployment patterns

**Run:**
```bash
cd agenkit-go/examples/protocols/agui
go run 02_sse_transport_hitl.go
```

**Test:**
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Should I proceed?"}' \
  -N
```

### 3. WebSocket HITL (`03_websocket_hitl.go`)

WebSocket transport with bidirectional HITL:
- AGUIWebSocketHandler for WebSocket connections
- Bidirectional message flow
- Real-time approval requests and responses
- Heartbeat support
- Custom HITL adapter integration

**Run:**
```bash
cd agenkit-go/examples/protocols/agui
go run 03_websocket_hitl.go
```

**Test with websocat:**
```bash
echo '{"type": "message", "content": "Make a critical decision"}' | websocat ws://localhost:8765
```

### 4. Advanced Approval (`04_advanced_approval.go`)

Advanced approval workflows:
- Tiered approval (4 levels based on amount)
- Contextual approval (risk, timing, transaction type)
- Approval with modifications
- Audit trail and statistics
- Multi-stage approval workflow

**Run:**
```bash
cd agenkit-go/examples/protocols/agui
go run 04_advanced_approval.go
```

**Features:**
- Tier 0: < $1,000 (Auto-approve)
- Tier 1: $1K-$10K (Manager)
- Tier 2: $10K-$50K (Director)
- Tier 3: > $50K (Executive + modifications)

## Quick Start

### Basic AG-UI Streaming

```go
import (
    "context"
    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
)

// Create adapter
adapter := agui.NewAGUIAdapter(myAgent)

// Stream events
message := agenkit.NewMessage("user", "Hello")
for event := range adapter.StreamEvents(context.Background(), message) {
    switch e := event.(type) {
    case *agui.TextMessageChunk:
        fmt.Print(e.Content)
    case *agui.TextMessageComplete:
        fmt.Println("\nDone!")
    }
}
```

### Human-in-the-Loop

```go
import (
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
    "github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
)

// Create approval function
approvalFunc := func(ctx context.Context, request *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
    // Implement approval logic (console, UI, API, etc.)
    return &patterns.ApprovalResponse{Approved: true}, nil
}

// Create HumanInLoopAgent
hilAgent, _ := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
    Agent:             myAgent,
    ApprovalFunc:      approvalFunc,
    ApprovalThreshold: 0.8,
})

// Wrap with AG-UI adapter
adapter := agui.NewAGUIHumanInLoopAdapter(hilAgent, "MyAgent", true)

// Stream events (includes Interrupt events)
for event := range adapter.StreamEvents(ctx, message) {
    if interrupt, ok := event.(*agui.Interrupt); ok {
        fmt.Printf("Approval: %v\n", interrupt.Context["approval_status"])
    }
}
```

### HTTP/SSE Transport

```go
import (
    "net/http"
    "github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui/transports"
)

// Create SSE handler
handler := transports.CreateSSEHandler(myAgent)

// Start server
http.Handle("/chat", handler)
http.ListenAndServe(":8080", nil)
```

### WebSocket Transport

```go
import (
    "net/http"
    "github.com/gorilla/websocket"
    "github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui/transports"
)

// Create WebSocket handler
upgrader := websocket.Upgrader{
    CheckOrigin: func(r *http.Request) bool { return true },
}
handler := transports.CreateWebSocketHandler(myAgent, upgrader)

// Start server
http.Handle("/chat", handler)
http.ListenAndServe(":8080", nil)
```

## Event Types

The AG-UI protocol defines structured events for agent-user communication:

### Core Events

- **MetadataEvent** - Agent capabilities and configuration
- **TextMessageStart** - Begin text message
- **TextMessageChunk** - Streaming text content
- **TextMessageComplete** - End text message with finish reason

### Tool Events

- **ToolCallStart** - Begin tool execution
- **ToolCallResult** - Tool execution result
- **ToolCallComplete** - End tool execution

### Interaction Events

- **Interrupt** - Request human intervention
  - Reasons: approval_required, clarification_needed, tool_confirmation
  - Actions: approve, reject, edit, cancel, continue
- **InterruptResponse** - Human response to interrupt
- **StateDelta** - Incremental state updates
- **Attachment** - File/media attachments

### System Events

- **ErrorEvent** - Error information
- **HeartbeatEvent** - Keep-alive signal

## Architecture

```
┌─────────────────┐
│  Agent          │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ AGUIAdapter     │  Converts agent responses to events
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Transport       │  HTTP/SSE or WebSocket
│ (SSE/WS)        │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Frontend        │  Browser/CLI/UI
└─────────────────┘
```

## Testing

All examples are tested and production-ready:

```bash
# Run all tests
cd agenkit-go/protocols/agui
go test -v

# Run specific example
cd agenkit-go/examples/protocols/agui
go run 01_basic_hitl.go
```

## Next Steps

1. **Read the examples** - Start with `01_basic_hitl.go`
2. **Explore transports** - See HTTP/SSE and WebSocket implementations
3. **Build a frontend** - Connect to transports from browser/CLI
4. **Advanced patterns** - Custom approval workflows, state management

## Related Documentation

- [AG-UI Protocol Specification](../../../docs/protocols/agui.md)
- [HumanInLoopAgent Pattern](../../../docs/patterns/human_in_loop.md)
- [Transport Layer Guide](../../../docs/protocols/agui_transports.md)
- [Python AG-UI Examples](../../../../examples/protocols/agui/)

## License

MIT License - See [LICENSE](../../../../LICENSE) for details.
