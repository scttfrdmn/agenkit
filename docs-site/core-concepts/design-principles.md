# Design Principles

The philosophy behind Agenkit's architecture.

## Core Philosophy

> **"Make the simple things simple, and the complex things possible."**

Agenkit achieves this through careful adherence to five core principles.

---

## 1. Minimal Interfaces

**Principle:** Only what's REQUIRED for interoperability.

### What This Means

- Agent interface: Just `name` + `process()`
- Message type: Just 4 fields
- Tool interface: Just `name` + `description` + `execute()`
- ToolResult: Just `success` + `data` + `error`

### Why This Matters

**For framework builders:**
- Easy to implement - minimal contract to satisfy
- No hidden requirements
- No framework lock-in

**For users:**
- Easy to understand - less to learn
- Easy to test - small surface area
- Maximum flexibility

### Counter-Example

```python
# ❌ What we DON'T do (bloated interface)
class Agent(ABC):
    def name(self) -> str: ...
    def process(self, message: Message) -> Message: ...
    def get_config(self) -> Config: ...
    def set_config(self, config: Config): ...
    def get_metrics(self) -> Metrics: ...
    def health_check(self) -> bool: ...
    def serialize(self) -> bytes: ...
    def deserialize(self, bytes) -> Self: ...

# ✅ What we DO (minimal interface)
class Agent(ABC):
    def name(self) -> str: ...
    def process(self, message: Message) -> Message: ...
```

---

## 2. Everything is an Agent

**Principle:** All layers implement the same Agent interface.

### What This Means

- **Base agents:** Implement Agent interface
- **Middleware:** Wraps Agent, exposes Agent interface
- **Compositions:** Combines Agents, exposes Agent interface
- **Remote agents:** Proxies Agent, exposes Agent interface

### Why This Matters

**Unlimited composability:**

```python
# All of these are agents
base = MyAgent()
cached = CachingDecorator(base)
retried = RetryDecorator(cached)
traced = TracingMiddleware(retried)
pipeline = SequentialAgent([traced, OtherAgent()])
remote = RemoteAgent(endpoint="...")

# They all have the same interface!
response = await any_agent.process(message)
```

**Uniform APIs:**
- Same interface everywhere
- No special cases
- Easy mental model

---

## 3. Decorator Pattern Over Inheritance

**Principle:** Composition over inheritance. Use wrappers, not subclasses.

### What This Means

Instead of inheritance hierarchies:

```python
# ❌ Inheritance approach (rigid)
class RetryableAgent(Agent):
    pass

class RetryableTimeoutAgent(RetryableAgent):
    pass

class RetryableTimeoutCachingAgent(RetryableTimeoutAgent):
    pass

# Need 2^N classes for N features!
```

We use decoration:

```python
# ✅ Decorator approach (flexible)
agent = MyAgent()
agent = RetryDecorator(agent)
agent = TimeoutDecorator(agent)
agent = CachingDecorator(agent)

# Mix and match as needed!
```

### Why This Matters

**Flexibility:**
- Add/remove features at runtime
- Change ordering dynamically
- No class explosion

**Single Responsibility:**
- Each decorator does ONE thing
- Easy to test independently
- Easy to understand

---

## 4. Language Agnostic

**Principle:** Identical APIs across Python and Go.

### What This Means

The same patterns work in both languages:

=== "Python"

    ```python
    from agenkit import Agent, Message
    from agenkit.middleware import RetryDecorator
    from agenkit.composition import SequentialAgent

    agent = SequentialAgent([
        RetryDecorator(Agent1()),
        Agent2()
    ])
    ```

=== "Go"

    ```go
    import (
        "github.com/agenkit/agenkit-go/agenkit"
        "github.com/agenkit/agenkit-go/middleware"
        "github.com/agenkit/agenkit-go/composition"
    )

    agent := composition.NewSequentialAgent([]agenkit.Agent{
        middleware.NewRetryDecorator(&Agent1{}),
        &Agent2{},
    })
    ```

### Why This Matters

**Cross-language systems:**
- Python agent calls Go agent seamlessly
- Same mental model, different languages
- No impedance mismatch

**Polyglot teams:**
- Python devs understand Go code
- Go devs understand Python code
- Shared vocabulary and patterns

---

## 5. Production Ready from Day One

**Principle:** Not a prototype. Not an experiment. Infrastructure.

### What This Means

**Code quality:**
- Type hints (mypy strict)
- Comprehensive tests (137/137 passing)
- Error handling on all paths
- Security by default

**Observable:**
- OpenTelemetry tracing
- Prometheus metrics
- Structured logging
- Health checks

**Deployable:**
- Docker images
- Kubernetes manifests
- Security hardened
- Autoscaling ready

### Why This Matters

**Trust:**
- Frameworks won't build on toy code
- Production systems need production quality
- 40-year veterans can spot shortcuts

**Longevity:**
- Good code compounds over time
- Bad code becomes abandonware
- Quality attracts quality

---

## Design Trade-offs

Every design decision involves trade-offs. Here are ours:

### Simplicity vs Features

**Choice:** Simplicity

- Minimal core interfaces
- Features built on top as optional layers
- You only pay for what you use

**Trade-off:** Need to compose features yourself (but we provide examples!)

### Performance vs Flexibility

**Choice:** Both

- Hot path is direct method calls (<5% overhead)
- No dynamic dispatch
- Single allocation per message
- But still flexible (Any type for content)

**Trade-off:** None! We achieve both through careful design.

### Type Safety vs Dynamism

**Choice:** Type safety

- Full typing in Python and Go
- mypy strict mode compliant
- No `Any` where we can avoid it

**Trade-off:** Slightly more verbose (but saves debugging time!)

---

## Anti-Patterns We Avoid

### 1. Framework Lock-In

❌ **Don't:** Require users to subclass framework classes

```python
# Bad - user must inherit from our base
class MyAgent(AgenkitBaseAgent):
    pass
```

✅ **Do:** Let users implement minimal interface

```python
# Good - user implements interface
class MyAgent(Agent):  # ABC, not concrete class
    pass
```

### 2. Hidden Magic

❌ **Don't:** Auto-register, auto-discover, metaclass magic

```python
# Bad - magic registration
@register_agent  # Where does this go?
class MyAgent(Agent):
    pass
```

✅ **Do:** Explicit is better than implicit

```python
# Good - explicit registration
agent = MyAgent()
registry.register(agent)
```

### 3. Leaky Abstractions

❌ **Don't:** Expose transport details in agent interface

```python
# Bad - HTTP details leak through
agent.process(message, headers={"X-Custom": "value"})
```

✅ **Do:** Keep abstractions clean

```python
# Good - transport details in metadata
message = Message(
    role="user",
    content="...",
    metadata={"http_headers": {"X-Custom": "value"}}
)
agent.process(message)
```

---

## Influences

Agenkit's design is influenced by:

- **UNIX philosophy:** Do one thing well, compose tools
- **Go interfaces:** Small, focused contracts
- **Middleware pattern:** Express, WSGI, Ring
- **Reactive streams:** Backpressure, composition
- **gRPC/Protocol Buffers:** Language-agnostic contracts

---

## Next Steps

- **[Architecture](architecture.md)** - See these principles in action
- **[Interfaces](interfaces.md)** - Study the minimal contracts
- **[Examples](../examples/index.md)** - Learn by example
