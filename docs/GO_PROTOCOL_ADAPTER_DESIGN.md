# Go Protocol Adapter Design

**Version:** 0.1.0
**Status:** Draft
**Author:** agenkit team
**Date:** 2025-11-09

---

## Executive Summary

The Go protocol adapter enables cross-process and cross-language communication for agenkit agents, implementing the same wire protocol as the Python adapter for full interoperability. It provides idiomatic Go interfaces and leverages Go's concurrency primitives for high-performance agent communication.

**Key Design Principles:**
- **Protocol compatibility**: 100% compatible with Python adapter wire protocol
- **Idiomatic Go**: Follows Go conventions (interfaces, error handling, naming)
- **High performance**: Leverages goroutines and channels for concurrency
- **Type-safe**: Strong static typing with interfaces
- **Production-ready**: Robust error handling, resource management, observability
- **Zero dependencies**: Uses only Go standard library (optional modules for extensions)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Application Layer                   │
│            (Uses Agent interface)                    │
└─────────────────┬──────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────┐
│              Protocol Adapter Layer                  │
│  ┌──────────────┬──────────────┬─────────────────┐ │
│  │ RemoteAgent  │ LocalAgent   │  Registry       │ │
│  │ (Client)     │ (Server)     │  (Discovery)    │ │
│  └──────────────┴──────────────┴─────────────────┘ │
└─────────────────┬──────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────┐
│              Serialization Layer                     │
│  ┌──────────────┬──────────────┬─────────────────┐ │
│  │ Message      │ ToolResult   │  Envelope       │ │
│  │ Codec        │ Codec        │  Codec          │ │
│  └──────────────┴──────────────┴─────────────────┘ │
└─────────────────┬──────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────┐
│               Transport Layer                        │
│  ┌──────────────┬──────────────┬─────────────────┐ │
│  │ Unix Socket  │ TCP Socket   │  In-Memory      │ │
│  └──────────────┴──────────────┴─────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 2. Wire Protocol Specification

### 2.1 Protocol Compatibility

The Go adapter implements the **exact same wire protocol** as the Python adapter, ensuring full interoperability:
- JSON-based message format
- Length-prefixed framing (4-byte big-endian length header)
- Same envelope structure and message types
- Compatible error codes and response formats

**Key benefit:** Go agents can communicate with Python agents seamlessly.

### 2.2 Message Format Reference

See [PYTHON_PROTOCOL_ADAPTER_DESIGN.md](./PYTHON_PROTOCOL_ADAPTER_DESIGN.md#2-wire-protocol-specification) for complete wire protocol specification.

Go implementation example:

```go
// Envelope represents the protocol message wrapper
type Envelope struct {
    Version   string                 `json:"version"`
    Type      string                 `json:"type"`
    ID        string                 `json:"id"`
    Timestamp time.Time              `json:"timestamp"`
    Payload   map[string]interface{} `json:"payload"`
}

// Message types
const (
    MessageTypeRequest    = "request"
    MessageTypeResponse   = "response"
    MessageTypeError      = "error"
    MessageTypeHeartbeat  = "heartbeat"
    MessageTypeRegister   = "register"
    MessageTypeUnregister = "unregister"
)
```

---

## 3. Core Interfaces

### 3.1 Agent Interface

The fundamental agent interface matching agenkit's core design:

```go
package agenkit

import (
    "context"
    "time"
)

// Agent is the core interface for all agents
type Agent interface {
    // Name returns the agent's unique identifier
    Name() string

    // Process handles a message and returns a response
    Process(ctx context.Context, message Message) (Message, error)
}

// Message represents a message exchanged between agents
type Message struct {
    Role      string                 `json:"role"`
    Content   string                 `json:"content"`
    Metadata  map[string]interface{} `json:"metadata,omitempty"`
    Timestamp time.Time              `json:"timestamp"`
}
```

### 3.2 Transport Interface

Abstract transport layer for different connection types:

```go
package adapter

import (
    "context"
    "io"
)

// Transport handles low-level message transmission
type Transport interface {
    io.Closer

    // Connect establishes the connection
    Connect(ctx context.Context) error

    // Send transmits data over the transport
    Send(ctx context.Context, data []byte) error

    // Receive reads data from the transport
    Receive(ctx context.Context) ([]byte, error)

    // IsConnected returns connection status
    IsConnected() bool
}
```

### 3.3 Codec Interface

Serialization and deserialization:

```go
package adapter

// Codec handles message encoding/decoding
type Codec interface {
    // EncodeMessage serializes a message to bytes
    EncodeMessage(msg Message) ([]byte, error)

    // DecodeMessage deserializes bytes to a message
    DecodeMessage(data []byte) (Message, error)

    // EncodeEnvelope serializes an envelope to bytes
    EncodeEnvelope(env Envelope) ([]byte, error)

    // DecodeEnvelope deserializes bytes to an envelope
    DecodeEnvelope(data []byte) (Envelope, error)
}
```

---

## 4. API Design

### 4.1 Server-Side API (LocalAgent)

Expose a local agent over the protocol adapter:

```go
package adapter

import (
    "context"
    "fmt"
    "log"
    "net"

    "github.com/scttfrdmn/agenkit"
)

// LocalAgent wraps an agent to serve it over a transport
type LocalAgent struct {
    agent     agenkit.Agent
    transport Transport
    registry  *Registry
    listener  net.Listener
    ctx       context.Context
    cancel    context.CancelFunc
}

// NewLocalAgent creates a server-side agent wrapper
func NewLocalAgent(agent agenkit.Agent, transport Transport, opts ...LocalAgentOption) *LocalAgent {
    ctx, cancel := context.WithCancel(context.Background())

    la := &LocalAgent{
        agent:     agent,
        transport: transport,
        ctx:       ctx,
        cancel:    cancel,
    }

    for _, opt := range opts {
        opt(la)
    }

    return la
}

// LocalAgentOption configures a LocalAgent
type LocalAgentOption func(*LocalAgent)

// WithRegistry configures registry integration
func WithRegistry(registry *Registry) LocalAgentOption {
    return func(la *LocalAgent) {
        la.registry = registry
    }
}

// Start begins serving agent requests
func (la *LocalAgent) Start(ctx context.Context) error {
    // Start listening for connections
    if err := la.transport.Connect(ctx); err != nil {
        return fmt.Errorf("transport connect failed: %w", err)
    }

    // Accept connections in goroutine
    go la.acceptLoop()

    // Register with registry if configured
    if la.registry != nil {
        registration := &Registration{
            Name:     la.agent.Name(),
            Endpoint: la.transport.Endpoint(),
        }
        if err := la.registry.Register(ctx, registration); err != nil {
            return fmt.Errorf("registry registration failed: %w", err)
        }

        // Start heartbeat loop
        go la.heartbeatLoop()
    }

    return nil
}

// Stop gracefully shuts down the server
func (la *LocalAgent) Stop() error {
    la.cancel()

    if la.registry != nil {
        ctx := context.Background()
        _ = la.registry.Unregister(ctx, la.agent.Name())
    }

    return la.transport.Close()
}

// acceptLoop accepts and handles connections
func (la *LocalAgent) acceptLoop() {
    for {
        select {
        case <-la.ctx.Done():
            return
        default:
            // Accept connection
            conn, err := la.listener.Accept()
            if err != nil {
                log.Printf("accept error: %v", err)
                continue
            }

            // Handle in goroutine
            go la.handleConnection(conn)
        }
    }
}

// handleConnection processes requests on a connection
func (la *LocalAgent) handleConnection(conn net.Conn) {
    defer conn.Close()

    codec := NewJSONCodec()

    for {
        select {
        case <-la.ctx.Done():
            return
        default:
            // Read request
            data, err := readFrame(conn)
            if err != nil {
                return
            }

            // Decode envelope
            envelope, err := codec.DecodeEnvelope(data)
            if err != nil {
                la.sendError(conn, "", "INVALID_MESSAGE", err.Error())
                continue
            }

            // Process request
            response := la.processRequest(envelope)

            // Send response
            responseData, _ := codec.EncodeEnvelope(response)
            writeFrame(conn, responseData)
        }
    }
}

// processRequest handles a single request
func (la *LocalAgent) processRequest(req Envelope) Envelope {
    // Extract message from payload
    messageData := req.Payload["message"].(map[string]interface{})
    message := Message{
        Role:      messageData["role"].(string),
        Content:   messageData["content"].(string),
        Metadata:  messageData["metadata"].(map[string]interface{}),
        Timestamp: time.Now(),
    }

    // Call agent
    ctx := context.Background()
    response, err := la.agent.Process(ctx, message)
    if err != nil {
        return la.createErrorEnvelope(req.ID, "AGENT_ERROR", err.Error())
    }

    // Create response envelope
    return Envelope{
        Version:   "1.0",
        Type:      MessageTypeResponse,
        ID:        req.ID,
        Timestamp: time.Now(),
        Payload: map[string]interface{}{
            "message": response,
        },
    }
}
```

### 4.2 Client-Side API (RemoteAgent)

Access a remote agent through the protocol adapter:

```go
package adapter

import (
    "context"
    "fmt"
    "time"

    "github.com/scttfrdmn/agenkit"
)

// RemoteAgent implements Agent interface for remote agents
type RemoteAgent struct {
    name      string
    endpoint  string
    transport Transport
    codec     Codec
    timeout   time.Duration
}

// NewRemoteAgent creates a client-side agent proxy
func NewRemoteAgent(name, endpoint string, opts ...RemoteAgentOption) (*RemoteAgent, error) {
    ra := &RemoteAgent{
        name:     name,
        endpoint: endpoint,
        codec:    NewJSONCodec(),
        timeout:  30 * time.Second,
    }

    for _, opt := range opts {
        opt(ra)
    }

    // Create transport based on endpoint
    transport, err := NewTransportFromEndpoint(endpoint)
    if err != nil {
        return nil, fmt.Errorf("create transport: %w", err)
    }
    ra.transport = transport

    return ra, nil
}

// RemoteAgentOption configures a RemoteAgent
type RemoteAgentOption func(*RemoteAgent)

// WithTimeout sets request timeout
func WithTimeout(timeout time.Duration) RemoteAgentOption {
    return func(ra *RemoteAgent) {
        ra.timeout = timeout
    }
}

// WithCodec sets custom codec
func WithCodec(codec Codec) RemoteAgentOption {
    return func(ra *RemoteAgent) {
        ra.codec = codec
    }
}

// Name returns the agent name (implements Agent interface)
func (ra *RemoteAgent) Name() string {
    return ra.name
}

// Process sends a message to the remote agent (implements Agent interface)
func (ra *RemoteAgent) Process(ctx context.Context, message agenkit.Message) (agenkit.Message, error) {
    // Create request envelope
    request := Envelope{
        Version:   "1.0",
        Type:      MessageTypeRequest,
        ID:        generateID(),
        Timestamp: time.Now(),
        Payload: map[string]interface{}{
            "method":     "process",
            "agent_name": ra.name,
            "message":    message,
        },
    }

    // Encode request
    requestData, err := ra.codec.EncodeEnvelope(request)
    if err != nil {
        return agenkit.Message{}, fmt.Errorf("encode request: %w", err)
    }

    // Connect if needed
    if !ra.transport.IsConnected() {
        if err := ra.transport.Connect(ctx); err != nil {
            return agenkit.Message{}, &ConnectionError{Err: err}
        }
    }

    // Send request
    if err := ra.transport.Send(ctx, requestData); err != nil {
        return agenkit.Message{}, &ConnectionError{Err: err}
    }

    // Receive response with timeout
    responseCtx, cancel := context.WithTimeout(ctx, ra.timeout)
    defer cancel()

    responseData, err := ra.transport.Receive(responseCtx)
    if err != nil {
        return agenkit.Message{}, &ConnectionError{Err: err}
    }

    // Decode response
    response, err := ra.codec.DecodeEnvelope(responseData)
    if err != nil {
        return agenkit.Message{}, &ProtocolError{Code: "MALFORMED_RESPONSE", Message: err.Error()}
    }

    // Handle error response
    if response.Type == MessageTypeError {
        return agenkit.Message{}, ra.parseErrorResponse(response)
    }

    // Extract message from response
    responseMessage := ra.parseMessageResponse(response)
    return responseMessage, nil
}

// Close closes the connection
func (ra *RemoteAgent) Close() error {
    return ra.transport.Close()
}
```

### 4.3 Complete Example

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"

    "github.com/scttfrdmn/agenkit"
    "github.com/scttfrdmn/agenkit/adapter"
)

// EchoAgent is a simple test agent
type EchoAgent struct{}

func (e *EchoAgent) Name() string {
    return "echo"
}

func (e *EchoAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    return agenkit.Message{
        Role:      "agent",
        Content:   fmt.Sprintf("Echo: %s", msg.Content),
        Timestamp: time.Now(),
    }, nil
}

func main() {
    ctx := context.Background()

    // Server side
    agent := &EchoAgent{}
    transport, _ := adapter.NewUnixSocketTransport("/tmp/agenkit/echo.sock")
    localAgent := adapter.NewLocalAgent(agent, transport)

    if err := localAgent.Start(ctx); err != nil {
        log.Fatal(err)
    }
    defer localAgent.Stop()

    // Client side (can be different process)
    remote, err := adapter.NewRemoteAgent("echo", "unix:///tmp/agenkit/echo.sock")
    if err != nil {
        log.Fatal(err)
    }
    defer remote.Close()

    // Use remote agent
    msg := agenkit.Message{
        Role:    "user",
        Content: "Hello",
    }

    response, err := remote.Process(ctx, msg)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(response.Content) // "Echo: Hello"
}
```

---

## 5. Transport Implementation

### 5.1 Unix Socket Transport

```go
package adapter

import (
    "context"
    "fmt"
    "net"
    "os"
    "path/filepath"
)

// UnixSocketTransport implements Transport for Unix domain sockets
type UnixSocketTransport struct {
    socketPath string
    conn       net.Conn
    listener   net.Listener
    isServer   bool
}

// NewUnixSocketTransport creates a Unix socket transport
func NewUnixSocketTransport(socketPath string) (*UnixSocketTransport, error) {
    return &UnixSocketTransport{
        socketPath: socketPath,
    }, nil
}

// Connect establishes Unix socket connection
func (u *UnixSocketTransport) Connect(ctx context.Context) error {
    if u.isServer {
        // Server mode: create listener

        // Clean up existing socket
        os.Remove(u.socketPath)

        // Create directory if needed
        dir := filepath.Dir(u.socketPath)
        if err := os.MkdirAll(dir, 0700); err != nil {
            return fmt.Errorf("create socket directory: %w", err)
        }

        // Create listener
        listener, err := net.Listen("unix", u.socketPath)
        if err != nil {
            return fmt.Errorf("listen on unix socket: %w", err)
        }
        u.listener = listener

        // Set permissions
        if err := os.Chmod(u.socketPath, 0600); err != nil {
            listener.Close()
            return fmt.Errorf("chmod socket: %w", err)
        }

        return nil
    }

    // Client mode: connect to server
    conn, err := net.Dial("unix", u.socketPath)
    if err != nil {
        return fmt.Errorf("connect to unix socket: %w", err)
    }
    u.conn = conn

    return nil
}

// Send transmits data
func (u *UnixSocketTransport) Send(ctx context.Context, data []byte) error {
    if u.conn == nil {
        return fmt.Errorf("not connected")
    }

    // Write length prefix (4 bytes, big-endian)
    length := uint32(len(data))
    lengthBytes := []byte{
        byte(length >> 24),
        byte(length >> 16),
        byte(length >> 8),
        byte(length),
    }

    if _, err := u.conn.Write(lengthBytes); err != nil {
        return fmt.Errorf("write length: %w", err)
    }

    // Write payload
    if _, err := u.conn.Write(data); err != nil {
        return fmt.Errorf("write payload: %w", err)
    }

    return nil
}

// Receive reads data
func (u *UnixSocketTransport) Receive(ctx context.Context) ([]byte, error) {
    if u.conn == nil {
        return nil, fmt.Errorf("not connected")
    }

    // Read length prefix
    lengthBytes := make([]byte, 4)
    if _, err := u.conn.Read(lengthBytes); err != nil {
        return nil, fmt.Errorf("read length: %w", err)
    }

    length := uint32(lengthBytes[0])<<24 |
              uint32(lengthBytes[1])<<16 |
              uint32(lengthBytes[2])<<8 |
              uint32(lengthBytes[3])

    // Validate length
    if length > 10*1024*1024 { // 10 MB max
        return nil, fmt.Errorf("message too large: %d bytes", length)
    }

    // Read payload
    payload := make([]byte, length)
    if _, err := u.conn.Read(payload); err != nil {
        return nil, fmt.Errorf("read payload: %w", err)
    }

    return payload, nil
}

// Close closes the connection
func (u *UnixSocketTransport) Close() error {
    if u.conn != nil {
        u.conn.Close()
    }
    if u.listener != nil {
        u.listener.Close()
    }
    if u.isServer {
        os.Remove(u.socketPath)
    }
    return nil
}

// IsConnected returns connection status
func (u *UnixSocketTransport) IsConnected() bool {
    return u.conn != nil || u.listener != nil
}
```

### 5.2 TCP Socket Transport

```go
package adapter

import (
    "context"
    "fmt"
    "net"
)

// TCPTransport implements Transport for TCP sockets
type TCPTransport struct {
    address  string
    port     int
    conn     net.Conn
    listener net.Listener
    isServer bool
}

// NewTCPTransport creates a TCP transport
func NewTCPTransport(address string, port int) (*TCPTransport, error) {
    return &TCPTransport{
        address: address,
        port:    port,
    }, nil
}

// Connect establishes TCP connection
func (t *TCPTransport) Connect(ctx context.Context) error {
    addr := fmt.Sprintf("%s:%d", t.address, t.port)

    if t.isServer {
        // Server mode: create listener
        listener, err := net.Listen("tcp", addr)
        if err != nil {
            return fmt.Errorf("listen on tcp: %w", err)
        }
        t.listener = listener
        return nil
    }

    // Client mode: connect
    conn, err := net.Dial("tcp", addr)
    if err != nil {
        return fmt.Errorf("connect to tcp: %w", err)
    }
    t.conn = conn

    return nil
}

// Send, Receive, Close, IsConnected similar to UnixSocketTransport
```

---

## 6. Registry Implementation

### 6.1 Registry Interface

```go
package adapter

import (
    "context"
    "sync"
    "time"
)

// Registry manages agent discovery and health monitoring
type Registry struct {
    agents            map[string]*Registration
    mu                sync.RWMutex
    heartbeatInterval time.Duration
    heartbeatTimeout  time.Duration
    ctx               context.Context
    cancel            context.CancelFunc
}

// Registration represents agent registration information
type Registration struct {
    Name          string                 `json:"name"`
    Endpoint      string                 `json:"endpoint"`
    Capabilities  map[string]interface{} `json:"capabilities,omitempty"`
    Metadata      map[string]interface{} `json:"metadata,omitempty"`
    RegisteredAt  time.Time              `json:"registered_at"`
    LastHeartbeat time.Time              `json:"last_heartbeat"`
}

// NewRegistry creates a new agent registry
func NewRegistry(opts ...RegistryOption) *Registry {
    ctx, cancel := context.WithCancel(context.Background())

    r := &Registry{
        agents:            make(map[string]*Registration),
        heartbeatInterval: 30 * time.Second,
        heartbeatTimeout:  90 * time.Second,
        ctx:               ctx,
        cancel:            cancel,
    }

    for _, opt := range opts {
        opt(r)
    }

    return r
}

// RegistryOption configures a Registry
type RegistryOption func(*Registry)

// WithHeartbeatInterval sets the heartbeat interval
func WithHeartbeatInterval(interval time.Duration) RegistryOption {
    return func(r *Registry) {
        r.heartbeatInterval = interval
    }
}

// WithHeartbeatTimeout sets the heartbeat timeout
func WithHeartbeatTimeout(timeout time.Duration) RegistryOption {
    return func(r *Registry) {
        r.heartbeatTimeout = timeout
    }
}

// Start begins registry operations
func (r *Registry) Start(ctx context.Context) error {
    // Start background pruning
    go r.pruneLoop()
    return nil
}

// Stop gracefully shuts down the registry
func (r *Registry) Stop() error {
    r.cancel()
    return nil
}

// Register adds an agent to the registry
func (r *Registry) Register(ctx context.Context, registration *Registration) error {
    if registration.Name == "" {
        return fmt.Errorf("agent name cannot be empty")
    }

    now := time.Now()
    registration.RegisteredAt = now
    registration.LastHeartbeat = now

    r.mu.Lock()
    defer r.mu.Unlock()

    r.agents[registration.Name] = registration
    return nil
}

// Unregister removes an agent from the registry
func (r *Registry) Unregister(ctx context.Context, agentName string) error {
    r.mu.Lock()
    defer r.mu.Unlock()

    delete(r.agents, agentName)
    return nil
}

// Lookup finds an agent by name
func (r *Registry) Lookup(ctx context.Context, agentName string) (*Registration, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    registration, exists := r.agents[agentName]
    if !exists {
        return nil, &AgentNotFoundError{AgentName: agentName}
    }

    return registration, nil
}

// ListAgents returns all registered agents
func (r *Registry) ListAgents(ctx context.Context) ([]*Registration, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    agents := make([]*Registration, 0, len(r.agents))
    for _, agent := range r.agents {
        agents = append(agents, agent)
    }

    return agents, nil
}

// Heartbeat updates agent heartbeat timestamp
func (r *Registry) Heartbeat(ctx context.Context, agentName string) error {
    r.mu.Lock()
    defer r.mu.Unlock()

    registration, exists := r.agents[agentName]
    if !exists {
        return &AgentNotFoundError{AgentName: agentName}
    }

    registration.LastHeartbeat = time.Now()
    return nil
}

// PruneStaleAgents removes agents with expired heartbeats
func (r *Registry) PruneStaleAgents() int {
    r.mu.Lock()
    defer r.mu.Unlock()

    now := time.Now()
    pruned := 0

    for name, agent := range r.agents {
        if now.Sub(agent.LastHeartbeat) > r.heartbeatTimeout {
            delete(r.agents, name)
            pruned++
        }
    }

    return pruned
}

// pruneLoop runs background pruning
func (r *Registry) pruneLoop() {
    ticker := time.NewTicker(60 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-r.ctx.Done():
            return
        case <-ticker.C:
            r.PruneStaleAgents()
        }
    }
}

// HeartbeatLoop sends periodic heartbeats for an agent
func HeartbeatLoop(ctx context.Context, registry *Registry, agentName string, interval time.Duration) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            if err := registry.Heartbeat(ctx, agentName); err != nil {
                // Agent was unregistered, stop heartbeat
                if _, ok := err.(*AgentNotFoundError); ok {
                    return
                }
                // Log error and retry
                time.Sleep(5 * time.Second)
            }
        }
    }
}
```

---

## 7. Error Handling

### 7.1 Error Types

```go
package adapter

import "fmt"

// ProtocolError represents protocol-level errors
type ProtocolError struct {
    Code    string
    Message string
    Details map[string]interface{}
}

func (e *ProtocolError) Error() string {
    return fmt.Sprintf("protocol error [%s]: %s", e.Code, e.Message)
}

// ConnectionError represents transport errors
type ConnectionError struct {
    Err error
}

func (e *ConnectionError) Error() string {
    return fmt.Sprintf("connection error: %v", e.Err)
}

func (e *ConnectionError) Unwrap() error {
    return e.Err
}

// AgentNotFoundError indicates agent doesn't exist in registry
type AgentNotFoundError struct {
    AgentName string
}

func (e *AgentNotFoundError) Error() string {
    return fmt.Sprintf("agent not found: %s", e.AgentName)
}

// RemoteExecutionError indicates remote agent raised an error
type RemoteExecutionError struct {
    AgentName string
    Message   string
}

func (e *RemoteExecutionError) Error() string {
    return fmt.Sprintf("remote agent %s error: %s", e.AgentName, e.Message)
}

// Error codes (matching Python adapter)
const (
    ErrorCodeConnectionFailed     = "CONNECTION_FAILED"
    ErrorCodeConnectionTimeout    = "CONNECTION_TIMEOUT"
    ErrorCodeConnectionClosed     = "CONNECTION_CLOSED"
    ErrorCodeInvalidMessage       = "INVALID_MESSAGE"
    ErrorCodeUnsupportedVersion   = "UNSUPPORTED_VERSION"
    ErrorCodeMalformedPayload     = "MALFORMED_PAYLOAD"
    ErrorCodeAgentNotFound        = "AGENT_NOT_FOUND"
    ErrorCodeAgentUnavailable     = "AGENT_UNAVAILABLE"
    ErrorCodeAgentTimeout         = "AGENT_TIMEOUT"
    ErrorCodeToolNotFound         = "TOOL_NOT_FOUND"
    ErrorCodeToolExecutionFailed  = "TOOL_EXECUTION_FAILED"
    ErrorCodeRegistrationFailed   = "REGISTRATION_FAILED"
    ErrorCodeDuplicateAgent       = "DUPLICATE_AGENT"
)
```

### 7.2 Error Handling Example

```go
response, err := remoteAgent.Process(ctx, message)
if err != nil {
    switch e := err.(type) {
    case *ConnectionError:
        // Transport error - retry with backoff
        log.Printf("Connection failed: %v", e)
    case *ProtocolError:
        // Protocol error - likely a bug
        log.Printf("Protocol error [%s]: %s", e.Code, e.Message)
    case *AgentNotFoundError:
        // Agent not registered
        log.Printf("Agent not found: %s", e.AgentName)
    case *RemoteExecutionError:
        // Agent raised an error
        log.Printf("Remote agent error: %v", e)
    default:
        // Unknown error
        log.Printf("Unexpected error: %v", err)
    }
    return
}
```

---

## 8. Performance Considerations

### 8.1 Concurrency Model

Go's goroutines provide natural parallelism:

```go
// Handle multiple connections concurrently
func (la *LocalAgent) acceptLoop() {
    for {
        conn, err := la.listener.Accept()
        if err != nil {
            continue
        }

        // Each connection in its own goroutine
        go la.handleConnection(conn)
    }
}

// Process multiple requests concurrently
func processMany(remote *RemoteAgent, messages []Message) []Message {
    results := make([]Message, len(messages))
    var wg sync.WaitGroup

    for i, msg := range messages {
        wg.Add(1)
        go func(idx int, m Message) {
            defer wg.Done()
            result, _ := remote.Process(context.Background(), m)
            results[idx] = result
        }(i, msg)
    }

    wg.Wait()
    return results
}
```

### 8.2 Connection Pooling

```go
package adapter

import (
    "context"
    "sync"
)

// ConnectionPool manages reusable connections
type ConnectionPool struct {
    connections map[string]chan Transport
    mu          sync.RWMutex
    maxSize     int
}

// NewConnectionPool creates a connection pool
func NewConnectionPool(maxSize int) *ConnectionPool {
    return &ConnectionPool{
        connections: make(map[string]chan Transport),
        maxSize:     maxSize,
    }
}

// Get retrieves or creates a connection
func (p *ConnectionPool) Get(ctx context.Context, endpoint string) (Transport, error) {
    p.mu.RLock()
    pool, exists := p.connections[endpoint]
    p.mu.RUnlock()

    if !exists {
        p.mu.Lock()
        pool = make(chan Transport, p.maxSize)
        p.connections[endpoint] = pool
        p.mu.Unlock()
    }

    select {
    case transport := <-pool:
        if transport.IsConnected() {
            return transport, nil
        }
        // Connection dead, create new one
        fallthrough
    default:
        // No available connection, create new one
        transport, err := NewTransportFromEndpoint(endpoint)
        if err != nil {
            return nil, err
        }
        if err := transport.Connect(ctx); err != nil {
            return nil, err
        }
        return transport, nil
    }
}

// Put returns a connection to the pool
func (p *ConnectionPool) Put(endpoint string, transport Transport) {
    p.mu.RLock()
    pool, exists := p.connections[endpoint]
    p.mu.RUnlock()

    if !exists {
        transport.Close()
        return
    }

    select {
    case pool <- transport:
        // Successfully returned to pool
    default:
        // Pool full, close connection
        transport.Close()
    }
}
```

### 8.3 Expected Performance

Based on Go's performance characteristics:

| Operation | Expected Latency | Notes |
|-----------|-----------------|-------|
| Goroutine spawn | ~1-2 μs | Much faster than Python coroutine |
| JSON marshal/unmarshal | ~5-10 μs | Similar to Python |
| Unix socket round-trip | ~10-20 μs | Slightly faster than Python |
| TCP localhost round-trip | ~50-100 μs | Similar to Python |

**Production context:**
- Typical LLM call: 100-1000 ms
- Protocol overhead: <0.02% of total latency (better than Python)

---

## 9. Testing Strategy

### 9.1 Unit Tests

```go
package adapter_test

import (
    "context"
    "testing"
    "time"

    "github.com/scttfrdmn/agenkit"
    "github.com/scttfrdmn/agenkit/adapter"
)

func TestMessageCodec(t *testing.T) {
    codec := adapter.NewJSONCodec()

    msg := agenkit.Message{
        Role:      "user",
        Content:   "test",
        Timestamp: time.Now(),
    }

    // Encode
    encoded, err := codec.EncodeMessage(msg)
    if err != nil {
        t.Fatalf("encode failed: %v", err)
    }

    // Decode
    decoded, err := codec.DecodeMessage(encoded)
    if err != nil {
        t.Fatalf("decode failed: %v", err)
    }

    // Verify
    if decoded.Content != msg.Content {
        t.Errorf("content mismatch: got %s, want %s", decoded.Content, msg.Content)
    }
}
```

### 9.2 Integration Tests

```go
func TestRemoteAgentCall(t *testing.T) {
    ctx := context.Background()

    // Start server
    agent := &EchoAgent{}
    transport, _ := adapter.NewUnixSocketTransport("/tmp/test.sock")
    server := adapter.NewLocalAgent(agent, transport)
    if err := server.Start(ctx); err != nil {
        t.Fatal(err)
    }
    defer server.Stop()

    // Create client
    remote, err := adapter.NewRemoteAgent("echo", "unix:///tmp/test.sock")
    if err != nil {
        t.Fatal(err)
    }
    defer remote.Close()

    // Test call
    msg := agenkit.Message{
        Role:    "user",
        Content: "test",
    }

    response, err := remote.Process(ctx, msg)
    if err != nil {
        t.Fatalf("process failed: %v", err)
    }

    if !strings.Contains(response.Content, "test") {
        t.Errorf("unexpected response: %s", response.Content)
    }
}
```

### 9.3 Benchmark Tests

```go
func BenchmarkDirectCall(b *testing.B) {
    agent := &EchoAgent{}
    msg := agenkit.Message{Role: "user", Content: "test"}
    ctx := context.Background()

    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        agent.Process(ctx, msg)
    }
}

func BenchmarkRemoteCall(b *testing.B) {
    // Setup
    ctx := context.Background()
    agent := &EchoAgent{}
    transport, _ := adapter.NewUnixSocketTransport("/tmp/bench.sock")
    server := adapter.NewLocalAgent(agent, transport)
    server.Start(ctx)
    defer server.Stop()

    remote, _ := adapter.NewRemoteAgent("echo", "unix:///tmp/bench.sock")
    defer remote.Close()

    msg := agenkit.Message{Role: "user", Content: "test"}

    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        remote.Process(ctx, msg)
    }
}
```

---

## 10. Package Structure

```
github.com/scttfrdmn/agenkit/
├── agent.go              # Core Agent interface
├── message.go            # Message type
├── tool.go               # Tool interface
└── adapter/              # Protocol adapter package
    ├── adapter.go        # Main adapter types
    ├── local_agent.go    # LocalAgent implementation
    ├── remote_agent.go   # RemoteAgent implementation
    ├── registry.go       # Registry implementation
    ├── codec.go          # JSON codec
    ├── transport.go      # Transport interface
    ├── unix_socket.go    # Unix socket transport
    ├── tcp_socket.go     # TCP transport
    ├── errors.go         # Error types
    ├── options.go        # Option functions
    └── internal/         # Internal helpers
        ├── framing.go    # Frame encoding/decoding
        └── utils.go      # Utilities

tests/adapter/            # Test files (mirror structure)
├── adapter_test.go
├── local_agent_test.go
├── remote_agent_test.go
├── registry_test.go
├── codec_test.go
├── transport_test.go
└── integration_test.go

examples/adapter/         # Example programs
├── 01_basic/
│   └── main.go
├── 02_registry/
│   └── main.go
└── 03_production/
    └── main.go
```

---

## 11. Go-Specific Considerations

### 11.1 Context Usage

Go's `context.Context` is used throughout for:
- Request cancellation
- Timeouts
- Request-scoped values

```go
// All operations accept context
func (ra *RemoteAgent) Process(ctx context.Context, msg Message) (Message, error)
func (t *Transport) Connect(ctx context.Context) error
func (r *Registry) Register(ctx context.Context, reg *Registration) error
```

### 11.2 Error Handling

Go's explicit error handling:

```go
// Multiple return values (result, error)
response, err := remote.Process(ctx, message)
if err != nil {
    return fmt.Errorf("process failed: %w", err)
}

// Error wrapping with %w
return fmt.Errorf("connect failed: %w", err)

// Type assertion for custom errors
if connErr, ok := err.(*ConnectionError); ok {
    // Handle connection error
}
```

### 11.3 Interface Design

Small, focused interfaces following Go conventions:

```go
// Transport is composable with io.Closer
type Transport interface {
    io.Closer
    Connect(ctx context.Context) error
    Send(ctx context.Context, data []byte) error
    Receive(ctx context.Context) ([]byte, error)
    IsConnected() bool
}

// Agent interface is minimal
type Agent interface {
    Name() string
    Process(ctx context.Context, message Message) (Message, error)
}
```

### 11.4 Functional Options Pattern

Go-idiomatic configuration:

```go
// Options are functions that modify the struct
type RemoteAgentOption func(*RemoteAgent)

func WithTimeout(timeout time.Duration) RemoteAgentOption {
    return func(ra *RemoteAgent) {
        ra.timeout = timeout
    }
}

// Usage
remote, err := NewRemoteAgent("agent", "endpoint",
    WithTimeout(10*time.Second),
    WithCodec(NewMsgPackCodec()),
)
```

### 11.5 Concurrency Safety

Thread-safe operations using sync primitives:

```go
type Registry struct {
    agents map[string]*Registration
    mu     sync.RWMutex  // Protect shared state
}

func (r *Registry) Lookup(ctx context.Context, name string) (*Registration, error) {
    r.mu.RLock()  // Read lock
    defer r.mu.RUnlock()

    reg, exists := r.agents[name]
    if !exists {
        return nil, &AgentNotFoundError{AgentName: name}
    }
    return reg, nil
}
```

---

## 12. Implementation Plan

### Phase 1: Core Protocol (Week 1)

- [ ] Define core interfaces (Agent, Transport, Codec)
- [ ] Implement JSON codec
- [ ] Implement Unix socket transport
- [ ] Implement framing protocol
- [ ] Unit tests for codec and transport

**Deliverables:**
- `adapter/codec.go`
- `adapter/transport.go`
- `adapter/unix_socket.go`
- `adapter/internal/framing.go`
- Unit tests

### Phase 2: Agent Communication (Week 1-2)

- [ ] Implement LocalAgent (server)
- [ ] Implement RemoteAgent (client)
- [ ] Request/response handling
- [ ] Error types and propagation
- [ ] Integration tests

**Deliverables:**
- `adapter/local_agent.go`
- `adapter/remote_agent.go`
- `adapter/errors.go`
- Integration tests
- Basic example

### Phase 3: Registry & Discovery (Week 2)

- [ ] Implement Registry
- [ ] Registration/unregistration
- [ ] Heartbeat protocol
- [ ] Stale agent pruning
- [ ] Registry tests

**Deliverables:**
- `adapter/registry.go`
- Registry tests
- Registry example

### Phase 4: Polish & Documentation (Week 2-3)

- [ ] TCP transport
- [ ] Connection pooling
- [ ] Performance benchmarks
- [ ] Complete documentation
- [ ] Cross-language interop tests (Go ↔ Python)
- [ ] Examples

**Deliverables:**
- `adapter/tcp_socket.go`
- Benchmarks
- API documentation
- Multiple examples
- v0.1.0 release

---

## 13. Success Metrics

### Performance

- [ ] <5% overhead vs direct agent calls
- [ ] <50μs latency for Unix socket calls (p99)
- [ ] <200μs latency for TCP localhost calls (p99)
- [ ] Support 10,000+ concurrent connections

### Reliability

- [ ] Automatic reconnection with exponential backoff
- [ ] Graceful handling of agent crashes
- [ ] No resource leaks (goroutines, connections, file descriptors)
- [ ] Context cancellation support

### Usability

- [ ] Drop-in replacement for local agents (same interface)
- [ ] <10 lines of code to expose agent remotely
- [ ] Clear error messages with context
- [ ] Idiomatic Go API

### Compatibility

- [ ] 100% wire protocol compatible with Python adapter
- [ ] Go 1.21+ support
- [ ] Works across Linux, macOS, Windows (where applicable)
- [ ] Validated cross-language interop (Go ↔ Python)

---

## 14. Future Enhancements

### MessagePack Codec

Binary serialization for high-performance scenarios:

```go
import "github.com/vmihailenco/msgpack/v5"

type MsgPackCodec struct{}

func (c *MsgPackCodec) EncodeMessage(msg Message) ([]byte, error) {
    return msgpack.Marshal(msg)
}
```

### gRPC Transport

Optional gRPC transport for advanced features:

```go
transport := adapter.NewGRPCTransport("agent.example.com:50051")
```

### Observability

OpenTelemetry integration:

```go
import "go.opentelemetry.io/otel"

remote := adapter.NewRemoteAgent("agent", endpoint,
    WithTracer(otel.Tracer("agenkit")),
)
```

### HTTP/2 Transport

For environments without Unix sockets:

```go
transport := adapter.NewHTTP2Transport("https://agent.example.com")
```

---

**End of Design Document**
