# Python Protocol Adapter Design

**Version:** 0.1.0
**Status:** Draft
**Author:** agenkit team
**Date:** 2025-11-08

---

## Executive Summary

The Python protocol adapter enables cross-process and cross-language communication for agenkit agents. It provides a reference implementation that can be used as-is, forked, or replaced with custom implementations.

**Key Design Principles:**
- **Simple wire protocol**: JSON-based for transparency and debugging
- **Multiple transports**: Unix sockets, TCP, and in-memory for testing
- **Agent discovery**: Registry-based with heartbeat monitoring
- **Type-safe**: Full type hints and validation
- **Performance-aware**: Efficient serialization, connection pooling
- **Reference quality**: Production-ready code that can be forked

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Application Layer                   │
│         (Uses standard Agent interface)              │
└─────────────────┬──────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────┐
│              Protocol Adapter Layer                  │
│  ┌──────────────┬──────────────┬─────────────────┐ │
│  │ RemoteAgent  │ LocalAgent   │  AgentRegistry  │ │
│  │ (Client)     │ (Server)     │  (Discovery)    │ │
│  └──────────────┴──────────────┴─────────────────┘ │
└─────────────────┬──────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────┐
│              Serialization Layer                     │
│  ┌──────────────┬──────────────┬─────────────────┐ │
│  │ Message      │ ToolResult   │  Error          │ │
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

### 2.1 Protocol Format

**Choice: JSON over MessagePack for v0.1.0**

Rationale:
- ✅ Human-readable for debugging
- ✅ Excellent tooling support
- ✅ Easy to inspect with standard tools (netcat, curl)
- ✅ Language-agnostic (works across Python, Go, Rust)
- ⚠️ Slightly slower than MessagePack (~10-20%)
- 📝 Can add MessagePack in v0.2.0 as optimization

**Future consideration:** MessagePack codec as optional high-performance alternative.

### 2.2 Message Types

All messages follow this envelope structure:

```json
{
  "version": "1.0",
  "type": "request|response|error|heartbeat|register|unregister",
  "id": "unique-message-id",
  "timestamp": "2025-11-08T12:34:56.789Z",
  "payload": { ... }
}
```

#### Agent Process Request

```json
{
  "version": "1.0",
  "type": "request",
  "id": "req-001",
  "timestamp": "2025-11-08T12:34:56.789Z",
  "payload": {
    "method": "process",
    "agent_name": "my_agent",
    "message": {
      "role": "user",
      "content": "Hello, agent!",
      "metadata": {},
      "timestamp": "2025-11-08T12:34:56.000Z"
    }
  }
}
```

#### Agent Process Response

```json
{
  "version": "1.0",
  "type": "response",
  "id": "req-001",
  "timestamp": "2025-11-08T12:34:57.123Z",
  "payload": {
    "message": {
      "role": "agent",
      "content": "Hello, user!",
      "metadata": {},
      "timestamp": "2025-11-08T12:34:57.000Z"
    }
  }
}
```

#### Tool Execute Request

```json
{
  "version": "1.0",
  "type": "request",
  "id": "req-002",
  "timestamp": "2025-11-08T12:34:58.000Z",
  "payload": {
    "method": "execute",
    "tool_name": "calculator",
    "kwargs": {
      "operation": "add",
      "a": 5,
      "b": 3
    }
  }
}
```

#### Tool Execute Response

```json
{
  "version": "1.0",
  "type": "response",
  "id": "req-002",
  "timestamp": "2025-11-08T12:34:58.100Z",
  "payload": {
    "result": {
      "success": true,
      "data": 8,
      "error": null,
      "metadata": {}
    }
  }
}
```

#### Error Response

```json
{
  "version": "1.0",
  "type": "error",
  "id": "req-003",
  "timestamp": "2025-11-08T12:34:59.000Z",
  "payload": {
    "error_code": "AGENT_NOT_FOUND",
    "error_message": "Agent 'unknown_agent' not found in registry",
    "error_details": {
      "agent_name": "unknown_agent",
      "available_agents": ["agent1", "agent2"]
    }
  }
}
```

#### Agent Registration

```json
{
  "version": "1.0",
  "type": "register",
  "id": "reg-001",
  "timestamp": "2025-11-08T12:35:00.000Z",
  "payload": {
    "agent_name": "my_agent",
    "capabilities": {
      "streaming": true,
      "tools": ["calculator", "search"]
    },
    "endpoint": "unix:///tmp/agenkit/my_agent.sock",
    "metadata": {
      "version": "1.0.0",
      "description": "My custom agent"
    }
  }
}
```

#### Heartbeat

```json
{
  "version": "1.0",
  "type": "heartbeat",
  "id": "hb-001",
  "timestamp": "2025-11-08T12:35:01.000Z",
  "payload": {
    "agent_name": "my_agent",
    "status": "healthy"
  }
}
```

### 2.3 Error Codes

Standard error codes for protocol-level errors:

```python
class ProtocolError(Enum):
    # Connection errors
    CONNECTION_FAILED = "CONNECTION_FAILED"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    CONNECTION_CLOSED = "CONNECTION_CLOSED"

    # Protocol errors
    INVALID_MESSAGE = "INVALID_MESSAGE"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    MALFORMED_PAYLOAD = "MALFORMED_PAYLOAD"

    # Agent errors
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"

    # Tool errors
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"

    # Registry errors
    REGISTRATION_FAILED = "REGISTRATION_FAILED"
    DUPLICATE_AGENT = "DUPLICATE_AGENT"
```

---

## 3. Transport Layer

### 3.1 Supported Transports

#### Unix Domain Sockets (Primary)

**Use case:** Same-machine communication (lowest latency)

```python
# Server
transport = UnixSocketTransport("/tmp/agenkit/my_agent.sock")

# Client
client = RemoteAgent("my_agent", "unix:///tmp/agenkit/my_agent.sock")
```

**Advantages:**
- Lowest latency (~1-2 μs)
- File system permissions for security
- Automatic cleanup on process exit

**Disadvantages:**
- Same machine only
- Platform-specific (limited Windows support)

#### TCP Sockets (Secondary)

**Use case:** Cross-machine communication

```python
# Server
transport = TCPTransport("localhost", 8080)

# Client
client = RemoteAgent("my_agent", "tcp://localhost:8080")
```

**Advantages:**
- Works across machines
- Cross-platform
- Firewall/proxy friendly

**Disadvantages:**
- Higher latency (~50-100 μs on localhost)
- Security requires TLS setup
- Port management overhead

#### In-Memory (Testing only)

**Use case:** Unit tests without real sockets

```python
# Create in-memory transport pair
server_transport, client_transport = create_memory_transport_pair()
```

**Advantages:**
- No file system/network setup
- Perfect for unit tests
- Deterministic behavior

**Disadvantages:**
- Not for production
- Single-process only

### 3.2 Transport Interface

All transports implement this interface:

```python
class Transport(ABC):
    """Abstract transport layer for agent communication."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""
        pass

    @abstractmethod
    async def send(self, data: bytes) -> None:
        """Send data."""
        pass

    @abstractmethod
    async def receive(self) -> bytes:
        """Receive data."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass
```

### 3.3 Framing Protocol

Messages are length-prefixed for framing:

```
┌────────────┬────────────────────────┐
│  Length    │      JSON Payload      │
│  (4 bytes) │   (Length bytes)       │
└────────────┴────────────────────────┘
```

- **Length**: 32-bit unsigned integer, big-endian
- **Max message size**: 10 MB (configurable)
- **Encoding**: UTF-8 for JSON

Example:
```python
# Sending
payload = json.dumps(message).encode('utf-8')
length = struct.pack('>I', len(payload))
await transport.send(length + payload)

# Receiving
length_bytes = await transport.receive_exactly(4)
length = struct.unpack('>I', length_bytes)[0]
payload_bytes = await transport.receive_exactly(length)
message = json.loads(payload_bytes.decode('utf-8'))
```

---

## 4. Agent Registry

### 4.1 Purpose

The registry provides:
- **Agent discovery**: Find agents by name
- **Health monitoring**: Track agent availability via heartbeats
- **Load balancing**: Route to healthy instances (future)
- **Metadata**: Agent capabilities and versions

### 4.2 Registry Architecture

```python
class AgentRegistry:
    """Central registry for agent discovery and health monitoring."""

    def __init__(self, heartbeat_interval: float = 30.0,
                 heartbeat_timeout: float = 90.0):
        self._agents: dict[str, AgentRegistration] = {}
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_timeout = heartbeat_timeout

    async def register(self, registration: AgentRegistration) -> None:
        """Register an agent."""
        pass

    async def unregister(self, agent_name: str) -> None:
        """Unregister an agent."""
        pass

    async def lookup(self, agent_name: str) -> AgentRegistration | None:
        """Find an agent by name."""
        pass

    async def list_agents(self) -> list[AgentRegistration]:
        """List all registered agents."""
        pass

    async def heartbeat(self, agent_name: str) -> None:
        """Update agent heartbeat."""
        pass

    async def prune_stale_agents(self) -> None:
        """Remove agents with expired heartbeats."""
        pass

@dataclass
class AgentRegistration:
    """Agent registration information."""
    name: str
    endpoint: str  # e.g., "unix:///tmp/agent.sock" or "tcp://localhost:8080"
    capabilities: dict[str, Any]
    metadata: dict[str, Any]
    registered_at: datetime
    last_heartbeat: datetime
```

### 4.3 Registry Implementation Options

#### Option A: In-Process Registry (v0.1.0)

Simple dictionary-based registry within a single process.

**Pros:**
- Simple to implement
- No external dependencies
- Good for testing and single-process scenarios

**Cons:**
- Not shared across processes
- No persistence

**Use case:** Development, testing, simple deployments

#### Option B: Redis Registry (v0.2.0)

Redis-backed registry for production.

**Pros:**
- Shared across processes/machines
- Built-in TTL for automatic cleanup
- Pub/sub for real-time updates

**Cons:**
- External dependency
- Requires Redis setup

**Use case:** Production deployments, distributed systems

#### Option C: etcd/Consul Registry (Future)

Full service discovery with health checks.

**Use case:** Large-scale deployments, Kubernetes

### 4.4 Heartbeat Protocol

Agents send periodic heartbeats to maintain registration:

```python
async def heartbeat_loop(registry: AgentRegistry, agent_name: str):
    """Send periodic heartbeats to registry."""
    while True:
        try:
            await registry.heartbeat(agent_name)
            await asyncio.sleep(30.0)  # Heartbeat interval
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            await asyncio.sleep(5.0)  # Retry quickly
```

Registry prunes stale agents:

```python
async def prune_loop(registry: AgentRegistry):
    """Remove agents with expired heartbeats."""
    while True:
        await asyncio.sleep(60.0)  # Check every minute
        await registry.prune_stale_agents()
```

---

## 5. API Design

### 5.1 Server-Side API (LocalAgent)

Expose a local agent over the protocol adapter:

```python
from agenkit import Agent, Message
from agenkit.adapters.python import LocalAgent, UnixSocketTransport

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my_agent"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")

# Create local agent server
agent = MyAgent()
transport = UnixSocketTransport("/tmp/agenkit/my_agent.sock")
local_agent = LocalAgent(agent, transport)

# Start serving
await local_agent.start()
```

### 5.2 Client-Side API (RemoteAgent)

Access a remote agent through the protocol adapter:

```python
from agenkit import Message
from agenkit.adapters.python import RemoteAgent

# Create remote agent client
remote = RemoteAgent("my_agent", "unix:///tmp/agenkit/my_agent.sock")

# Use like a normal agent
message = Message(role="user", content="Hello")
response = await remote.process(message)
print(response.content)  # "Processed: Hello"
```

**Key feature:** RemoteAgent implements the Agent interface, so it's a drop-in replacement.

### 5.3 Registry API

```python
from agenkit.adapters.python import AgentRegistry

# Create registry
registry = AgentRegistry()

# Register agent
await registry.register(AgentRegistration(
    name="my_agent",
    endpoint="unix:///tmp/agenkit/my_agent.sock",
    capabilities={"streaming": True},
    metadata={"version": "1.0.0"},
    registered_at=datetime.now(timezone.utc),
    last_heartbeat=datetime.now(timezone.utc)
))

# Lookup agent
registration = await registry.lookup("my_agent")
if registration:
    # Connect to agent
    remote = RemoteAgent(registration.name, registration.endpoint)
```

### 5.4 Complete Example

```python
from agenkit import Agent, Message
from agenkit.adapters.python import (
    LocalAgent,
    RemoteAgent,
    AgentRegistry,
    UnixSocketTransport
)

# Server side
class EchoAgent(Agent):
    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Echo: {message.content}")

# Start server
agent = EchoAgent()
transport = UnixSocketTransport("/tmp/agenkit/echo.sock")
local_agent = LocalAgent(agent, transport, registry=registry)
await local_agent.start()

# Client side (can be different process/machine)
remote = RemoteAgent("echo", "unix:///tmp/agenkit/echo.sock")
msg = Message(role="user", content="Hello")
response = await remote.process(msg)
print(response.content)  # "Echo: Hello"
```

---

## 6. Performance Considerations

### 6.1 Expected Performance

Based on benchmarks from Phase 1:

| Operation | Latency | Overhead |
|-----------|---------|----------|
| Local agent call | ~0.001 ms | 2-3% |
| Unix socket (same machine) | ~0.002 ms | ~0.001 ms added |
| TCP localhost | ~0.050 ms | ~0.049 ms added |
| JSON serialization (1KB msg) | ~0.010 ms | - |

**Total overhead for remote agent call:**
- Unix socket: ~0.013 ms (13 μs)
- TCP localhost: ~0.061 ms (61 μs)

**Production context:**
- Typical LLM call: 100-1000 ms
- Protocol overhead: <0.01% of total latency

### 6.2 Optimization Strategies

#### Connection Pooling

Reuse connections instead of creating new ones:

```python
class ConnectionPool:
    """Pool of reusable connections to remote agents."""

    async def get_connection(self, endpoint: str) -> Transport:
        """Get or create connection."""
        pass

    async def release_connection(self, endpoint: str, transport: Transport):
        """Return connection to pool."""
        pass
```

**Impact:** Eliminates connection setup overhead (~1-2 ms per call)

#### Batch Requests

Send multiple requests in one round-trip:

```python
responses = await remote.process_batch([msg1, msg2, msg3])
```

**Impact:** Amortizes network latency over multiple requests

#### MessagePack (Future)

Optional binary serialization for high-throughput scenarios:

```python
transport = UnixSocketTransport("/tmp/agent.sock", codec="msgpack")
```

**Impact:** 10-20% faster serialization, smaller payloads

### 6.3 Performance Monitoring

Built-in metrics for observability:

```python
@dataclass
class AdapterMetrics:
    """Protocol adapter performance metrics."""
    requests_total: int
    requests_failed: int
    request_duration_ms: list[float]  # Histogram
    serialization_time_ms: list[float]
    transport_time_ms: list[float]
    active_connections: int
```

---

## 7. Error Handling

### 7.1 Error Categories

1. **Transport errors**: Connection failures, timeouts
2. **Protocol errors**: Invalid messages, unsupported versions
3. **Agent errors**: Agent not found, execution failures
4. **Application errors**: Errors from agent.process()

### 7.2 Error Propagation

```python
try:
    response = await remote.process(message)
except ConnectionError as e:
    # Transport error - retry with backoff
    logger.error(f"Connection failed: {e}")
except ProtocolError as e:
    # Protocol error - likely a bug
    logger.error(f"Protocol error: {e}")
except AgentNotFoundError as e:
    # Agent not registered
    logger.error(f"Agent not found: {e}")
except RemoteExecutionError as e:
    # Agent raised an error
    logger.error(f"Remote agent error: {e}")
```

### 7.3 Retry Strategy

Automatic retries with exponential backoff:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(ConnectionError)
)
async def process_with_retry(remote: RemoteAgent, message: Message) -> Message:
    return await remote.process(message)
```

---

## 8. Security Considerations

### 8.1 Unix Socket Security

- **File permissions**: 0600 (owner read/write only)
- **Directory permissions**: 0700 (owner access only)
- **Cleanup**: Remove socket file on exit

```python
import os

socket_path = "/tmp/agenkit/agent.sock"
os.makedirs(os.path.dirname(socket_path), mode=0o700, exist_ok=True)
# Create socket...
os.chmod(socket_path, 0o600)
```

### 8.2 TCP Security

For TCP transports, use TLS:

```python
transport = TCPTransport(
    "agent.example.com",
    8080,
    tls=True,
    cert_path="/path/to/cert.pem",
    key_path="/path/to/key.pem"
)
```

### 8.3 Input Validation

Validate all incoming messages:

```python
def validate_message(data: dict[str, Any]) -> None:
    """Validate incoming protocol message."""
    if "version" not in data:
        raise ProtocolError("Missing version field")

    if data["version"] != "1.0":
        raise ProtocolError(f"Unsupported version: {data['version']}")

    if "type" not in data or data["type"] not in VALID_MESSAGE_TYPES:
        raise ProtocolError(f"Invalid message type: {data.get('type')}")

    # ... more validation
```

### 8.4 Resource Limits

Prevent abuse with resource limits:

```python
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_CONCURRENT_CONNECTIONS = 100
REQUEST_TIMEOUT = 30.0  # seconds
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

Test each component in isolation:

```python
class TestMessageCodec:
    def test_encode_message(self):
        msg = Message(role="user", content="test")
        encoded = encode_message(msg)
        assert isinstance(encoded, bytes)

    def test_decode_message(self):
        data = b'{"role":"user","content":"test",...}'
        msg = decode_message(data)
        assert msg.role == "user"
```

### 9.2 Integration Tests

Test full request/response cycle:

```python
@pytest.mark.asyncio
async def test_remote_agent_call():
    # Start local agent server
    agent = EchoAgent()
    server = LocalAgent(agent, UnixSocketTransport("/tmp/test.sock"))
    await server.start()

    # Create remote client
    remote = RemoteAgent("echo", "unix:///tmp/test.sock")

    # Test call
    msg = Message(role="user", content="test")
    response = await remote.process(msg)
    assert "test" in response.content

    await server.stop()
```

### 9.3 Performance Tests

Benchmark adapter overhead:

```python
@pytest.mark.benchmark
async def test_adapter_overhead(benchmark):
    remote = RemoteAgent("echo", "unix:///tmp/test.sock")
    msg = Message(role="user", content="test")

    result = benchmark(lambda: asyncio.run(remote.process(msg)))

    # Assert <15% overhead vs direct call
    assert result.mean < 0.015  # 15ms for 100ms baseline
```

### 9.4 Fault Injection Tests

Test error handling:

```python
@pytest.mark.asyncio
async def test_connection_failure():
    # Create client pointing to non-existent server
    remote = RemoteAgent("missing", "unix:///tmp/missing.sock")
    msg = Message(role="user", content="test")

    with pytest.raises(ConnectionError):
        await remote.process(msg)
```

---

## 10. Implementation Plan

### 10.1 Phase 1: Core Protocol (Week 1)

- [ ] Message serialization codec (JSON)
- [ ] Transport interface + Unix socket implementation
- [ ] Basic framing protocol
- [ ] Unit tests for codecs and transports

**Deliverables:**
- `agenkit/adapters/python/codec.py`
- `agenkit/adapters/python/transport.py`
- `tests/adapters/test_codec.py`
- `tests/adapters/test_transport.py`

### 10.2 Phase 2: Agent Communication (Week 1)

- [ ] LocalAgent (server)
- [ ] RemoteAgent (client)
- [ ] Request/response handling
- [ ] Error propagation
- [ ] Integration tests

**Deliverables:**
- `agenkit/adapters/python/local_agent.py`
- `agenkit/adapters/python/remote_agent.py`
- `tests/adapters/test_remote_agent.py`
- Working example

### 10.3 Phase 3: Registry & Discovery (Week 2)

- [ ] In-process registry implementation
- [ ] Agent registration/unregistration
- [ ] Heartbeat protocol
- [ ] Stale agent pruning
- [ ] Registry tests

**Deliverables:**
- `agenkit/adapters/python/registry.py`
- `tests/adapters/test_registry.py`
- Documentation

### 10.4 Phase 4: Polish & Documentation (Week 2)

- [ ] TCP transport implementation
- [ ] Connection pooling
- [ ] Performance benchmarks
- [ ] Complete API documentation
- [ ] Usage examples
- [ ] Migration guide from local to remote agents

**Deliverables:**
- Complete API docs
- 5+ examples
- Benchmark results
- v0.2.0 release

---

## 11. Future Enhancements (Post v0.2.0)

### MessagePack Codec

Binary serialization for performance:

```python
from agenkit.adapters.python import RemoteAgent

remote = RemoteAgent("agent", "unix:///tmp/agent.sock", codec="msgpack")
```

**Impact:** 10-20% faster, smaller payloads

### Streaming Support

Support for agent.stream() over protocol:

```python
async for chunk in remote.stream(message):
    print(chunk.content, end="")
```

**Challenge:** Framing for streaming messages

### Redis Registry

Production-grade registry with persistence:

```python
from agenkit.adapters.python import RedisRegistry

registry = RedisRegistry("redis://localhost:6379")
```

### Load Balancing

Route to multiple instances of same agent:

```python
registry.register_many([
    ("agent", "unix:///tmp/agent1.sock"),
    ("agent", "unix:///tmp/agent2.sock"),
])

# Automatically routes to healthy instance
remote = RemoteAgent("agent", registry=registry)
```

### TLS Support

Encrypted TCP connections:

```python
transport = TCPTransport("agent.example.com", 8080, tls=True)
```

### Observability

OpenTelemetry integration:

```python
from agenkit.adapters.python import TracedRemoteAgent

remote = TracedRemoteAgent("agent", endpoint, tracer=tracer)
# Automatically emits spans for requests
```

---

## 12. Success Metrics

### Performance

- [ ] <15% overhead vs local agent calls
- [ ] <1ms latency for Unix socket calls (99th percentile)
- [ ] <100ms latency for TCP localhost calls (99th percentile)

### Reliability

- [ ] Automatic reconnection on connection failure
- [ ] Graceful handling of agent crashes
- [ ] No resource leaks (connections, file descriptors)

### Usability

- [ ] Drop-in replacement for local agents (same interface)
- [ ] <10 lines of code to expose agent remotely
- [ ] Clear error messages with actionable guidance

### Compatibility

- [ ] Works across Python 3.10, 3.11, 3.12
- [ ] Compatible with asyncio and trio
- [ ] Foundation for Go and Rust adapters (same protocol)

---

## 13. Appendix

### A. Example Message Flow

```
Client (RemoteAgent)                        Server (LocalAgent)
     |                                             |
     |--- [1. Connect to Unix socket] ----------->|
     |                                             |
     |--- [2. Send JSON request] ---------------->|
     |    {type: "request", method: "process"}    |
     |                                             |
     |                                             |--- [3. Deserialize]
     |                                             |--- [4. Call agent.process()]
     |                                             |--- [5. Serialize response]
     |                                             |
     |<-- [6. Send JSON response] ----------------|
     |    {type: "response", payload: {...}}      |
     |                                             |
     |--- [7. Deserialize] ----------------------->|
     |                                             |
     |--- [8. Return Message] -------------------->|
```

### B. File Structure

```
agenkit/adapters/python/
├── __init__.py           # Public API
├── codec.py              # Message serialization
├── transport.py          # Transport abstraction
├── unix_socket.py        # Unix socket transport
├── tcp_socket.py         # TCP socket transport
├── local_agent.py        # Server-side agent wrapper
├── remote_agent.py       # Client-side agent proxy
├── registry.py           # Agent discovery
├── errors.py             # Exception types
└── utils.py              # Helper functions

tests/adapters/python/
├── test_codec.py
├── test_transport.py
├── test_local_agent.py
├── test_remote_agent.py
├── test_registry.py
└── test_integration.py

examples/adapters/
├── 01_basic_remote_agent.py
├── 02_agent_registry.py
├── 03_error_handling.py
├── 04_performance_comparison.py
└── 05_production_setup.py
```

### C. References

- [JSON RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [MessagePack Format](https://msgpack.org/)
- [Unix Domain Sockets](https://man7.org/linux/man-pages/man7/unix.7.html)
- [asyncio Protocol Documentation](https://docs.python.org/3/library/asyncio-protocol.html)

---

**End of Design Document**
