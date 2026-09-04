# Getting Started with Agenkit

Welcome to Agenkit! This guide will help you get up and running with the toolkit in minutes.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Your First Agent](#your-first-agent)
4. [Core Concepts](#core-concepts)
5. [Orchestration Patterns](#orchestration-patterns)
6. [Transport & Communication](#transport--communication)
7. [Middleware & Resilience](#middleware--resilience)
8. [Autonomous Agent Features](#autonomous-agent-features)
9. [Observability](#observability)
10. [Next Steps](#next-steps)

## Overview

Agenkit is a production-ready toolkit for building distributed AI agent systems with:

- **Cross-language support** - Nine language implementations (Python, Go, TypeScript,
  Rust, C++, Zig, C#, Java, Scala) sharing the same core patterns, with varying
  completeness for advanced subsystems — see [COMPATIBILITY.md](COMPATIBILITY.md) for
  current per-language details
- **Multiple transports** - HTTP (HTTP/1.1, HTTP/2, HTTP/3), gRPC, WebSocket
- **Production middleware** - Circuit breaker, retry, timeout, rate limiting, caching, batching
- **Autonomous agent building blocks** - Memory, budget tracking, checkpointing, safety, evaluation
- **Full observability** - OpenTelemetry tracing, Prometheus metrics, structured logging
- **Container ready** - Docker and Kubernetes deployment with HPA

**Website:** [https://agenkit.dev](https://agenkit.dev)

## Installation

### Python

```bash
# Install from PyPI
pip install agenkit

# Or install from source with development dependencies
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit
pip install -e ".[dev]"
```

**Requirements:** Python 3.12+ (`requires-python = ">=3.12"` in `pyproject.toml`)

### Go

```bash
# Install the Go module
go get github.com/scttfrdmn/agenkit-go

# Or clone and use locally
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-go
go mod download
```

**Requirements:** Go 1.26.8+

### TypeScript

```bash
# Install from npm
npm install @agenkit/core

# Or with yarn
yarn add @agenkit/core
```

**Requirements:** Node.js 18+ (`"engines": {"node": ">=18.0.0"}` in `agenkit-ts/package.json`)

### C++

```bash
# Clone and build with CMake
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-cpp
mkdir build && cd build
cmake ..
make
```

**Requirements:** C++17 compiler, CMake 3.16+ (`cmake_minimum_required(VERSION 3.16)` in
`agenkit-cpp/CMakeLists.txt`), nlohmann/json, cpp-httplib (fetched automatically via CMake
`FetchContent` if not found)

### Rust

```bash
# Add to Cargo.toml
cargo add agenkit

# Or from source
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-rust
cargo build --release
```

**Requirements:** Rust stable (`agenkit-rust/Cargo.toml` does not pin a `rust-version`/MSRV
field, so "stable at release time" is the only documented floor — see COMPATIBILITY.md);
edition 2021

## Your First Agent

### Python

Create a simple question-answering agent:

```python
from agenkit import Agent, Message
import asyncio

class QAAgent(Agent):
    """A simple Q&A agent."""

    @property
    def name(self) -> str:
        return "qa-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["question-answering"]

    async def process(self, message: Message) -> Message:
        # Simple logic
        if "capital of France" in message.content.lower():
            response = "The capital of France is Paris."
        else:
            response = f"I received: {message.content}"

        return Message(
            role="agent",
            content=response
        )

# Use the agent
async def main():
    agent = QAAgent()

    # Create a message
    msg = Message(
        role="user",
        content="What is the capital of France?"
    )

    # Process it
    response = await agent.process(msg)
    print(f"Agent: {response.content}")

# Run
asyncio.run(main())
```

**Output:**
```
Agent: The capital of France is Paris.
```

### Go

The same agent in Go:

```go
package main

import (
    "context"
    "fmt"
    "strings"

    "github.com/scttfrdmn/agenkit-go/agenkit"
)

// QAAgent is a simple Q&A agent
type QAAgent struct{}

func (a *QAAgent) Name() string {
    return "qa-agent"
}

func (a *QAAgent) Capabilities() []string {
    return []string{"question-answering"}
}

func (a *QAAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    content := strings.ToLower(msg.ContentString())

    var response string
    if strings.Contains(content, "capital of france") {
        response = "The capital of France is Paris."
    } else {
        response = fmt.Sprintf("I received: %s", msg.ContentString())
    }

    return &agenkit.Message{
        Role:    "agent",
        Content: response,
    }, nil
}

func main() {
    agent := &QAAgent{}

    // Create a message
    msg := &agenkit.Message{
        Role:    "user",
        Content: "What is the capital of France?",
    }

    // Process it
    response, err := agent.Process(context.Background(), msg)
    if err != nil {
        panic(err)
    }

    fmt.Printf("Agent: %s\n", response.ContentString())
}
```

**Output:**
```
Agent: The capital of France is Paris.
```

## Core Concepts

### Agent Interface

All agents implement the `Agent` interface:

**Python:**
```python
class Agent(Protocol):
    @property
    def name(self) -> str:
        """Unique agent identifier"""
        ...

    @property
    def capabilities(self) -> list[str]:
        """List of agent capabilities"""
        ...

    async def process(self, message: Message) -> Message:
        """Process a message and return a response"""
        ...
```

**Go:**
```go
type Agent interface {
    Name() string
    Capabilities() []string
    Process(ctx context.Context, msg *Message) (*Message, error)
}
```

### Message Format

Messages are the communication unit:

**Python:**
```python
from agenkit import Message

msg = Message(
    role="user",              # "user", "agent", "system"
    content="Hello!",         # Message content
    metadata={"key": "value"} # Optional metadata
)
```

**Go:**
```go
msg := &agenkit.Message{
    Role:     "user",
    Content:  "Hello!",
    Metadata: map[string]interface{}{"key": "value"},
}
```

### Tools

Tools extend agent capabilities:

**Python:**
```python
from agenkit import Tool

class CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Performs mathematical calculations"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {"type": "string"}
            }
        }

    async def execute(self, **kwargs) -> str:
        expr = kwargs.get("expression", "")
        try:
            result = eval(expr)  # Don't use eval in production!
            return str(result)
        except Exception as e:
            return f"Error: {e}"
```

## Orchestration Patterns

Agenkit provides built-in patterns for complex workflows:

### Sequential Pattern

Execute agents in order:

**Python:**
```python
from agenkit.patterns import SequentialPattern

# Create a pipeline
pipeline = SequentialPattern([
    data_extraction_agent,
    data_validation_agent,
    data_transformation_agent
])

# Process message through pipeline
result = await pipeline.process(input_message)
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit-go/patterns"

// Create pipeline
pipeline := patterns.NewSequential([]agenkit.Agent{
    dataExtractionAgent,
    dataValidationAgent,
    dataTransformationAgent,
})

// Process message
result, err := pipeline.Process(ctx, inputMessage)
```

### Parallel Pattern

Execute agents concurrently:

**Python:**
```python
from agenkit.patterns import ParallelPattern

# Run agents in parallel
parallel = ParallelPattern([
    sentiment_agent,
    entity_extraction_agent,
    classification_agent
])

results = await parallel.process(input_message)
# Returns list of responses from all agents
```

### Router Pattern

Conditionally route to agents:

**Python:**
```python
from agenkit.patterns import RouterPattern

def route_logic(message: Message) -> str:
    """Determine which agent should handle the message."""
    if "technical" in message.content.lower():
        return "technical-agent"
    elif "sales" in message.content.lower():
        return "sales-agent"
    return "general-agent"

router = RouterPattern(
    agents={
        "technical-agent": technical_support_agent,
        "sales-agent": sales_agent,
        "general-agent": general_agent
    },
    route_func=route_logic
)

response = await router.process(input_message)
```

### Fallback Pattern

Try agents until one succeeds:

**Python:**
```python
from agenkit.patterns import FallbackPattern

# Try primary agent, fall back to secondary if it fails
fallback = FallbackPattern([
    primary_llm_agent,
    secondary_llm_agent,
    rule_based_fallback_agent
])

response = await fallback.process(input_message)
```

## Transport & Communication

### HTTP Transport

**Python Server:**
```python
from agenkit.adapters.python.http_server import HTTPServer

# Create agent
agent = QAAgent()

# Start HTTP server
server = HTTPServer(agent, host="0.0.0.0", port=8080)
server.start()
```

**Python Client:**
```python
from agenkit.adapters.python.remote_agent import RemoteAgent

# Connect to remote agent
remote_agent = RemoteAgent("http://localhost:8080")

# Use like a local agent
response = await remote_agent.process(message)
```

**Go Server:**
```go
import "github.com/scttfrdmn/agenkit-go/adapter/transport"

// Start HTTP server
server := transport.NewHTTPServer(agent, ":8080")
server.Start()
```

**Go Client:**
```go
import "github.com/scttfrdmn/agenkit-go/adapter/transport"

// Connect to remote agent
client := transport.NewHTTPClient("http://localhost:8080")
response, err := client.Process(ctx, message)
```

### gRPC Transport

**Python:**
```python
from agenkit.adapters.python.grpc_server import GRPCServer

# Start gRPC server
server = GRPCServer(agent, port=50051)
server.start()
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit-go/adapter/transport"

// Start gRPC server
server := transport.NewGRPCServer(agent, ":50051")
server.Start()
```

### WebSocket Transport

**Python:**
```python
from agenkit.adapters.python.websocket_server import WebSocketServer

# Start WebSocket server for bidirectional streaming
server = WebSocketServer(agent, port=8765)
server.start()
```

## Middleware & Resilience

### Circuit Breaker

Prevent cascading failures:

**Python:**
```python
from agenkit.middleware import CircuitBreakerMiddleware

# Wrap agent with circuit breaker
protected_agent = CircuitBreakerMiddleware(
    agent,
    failure_threshold=5,     # Open after 5 failures
    recovery_timeout=60.0,   # Try again after 60 seconds
    expected_exception=Exception
)

response = await protected_agent.process(message)
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit-go/middleware"

// Wrap agent
protectedAgent := middleware.NewCircuitBreaker(
    agent,
    5,    // failure threshold
    60,   // recovery timeout (seconds)
)

response, err := protectedAgent.Process(ctx, message)
```

### Retry with Exponential Backoff

**Python:**
```python
from agenkit.middleware import RetryMiddleware

# Add retry logic
resilient_agent = RetryMiddleware(
    agent,
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    exponential_base=2
)

response = await resilient_agent.process(message)
```

### Timeout

**Python:**
```python
from agenkit.middleware import TimeoutMiddleware

# Add timeout protection
timed_agent = TimeoutMiddleware(
    agent,
    timeout=30.0  # 30 second timeout
)

response = await timed_agent.process(message)
```

### Rate Limiting

**Python:**
```python
from agenkit.middleware import RateLimiterMiddleware

# Limit requests per second
limited_agent = RateLimiterMiddleware(
    agent,
    rate=10.0,        # 10 requests per second
    burst=20          # Allow bursts up to 20
)

response = await limited_agent.process(message)
```

### Caching

**Python:**
```python
from agenkit.middleware import CachingMiddleware

# Cache responses
cached_agent = CachingMiddleware(
    agent,
    max_size=1000,    # Cache up to 1000 entries
    ttl=300           # 5 minute TTL
)

response = await cached_agent.process(message)
```

### Batching

**Python:**
```python
from agenkit.middleware import BatchingMiddleware

# Batch requests for efficiency
batched_agent = BatchingMiddleware(
    agent,
    max_batch_size=10,
    max_wait_time=0.1  # 100ms max wait
)

response = await batched_agent.process(message)
```

### Composing Middleware

Stack multiple middleware:

**Python:**
```python
# Build a resilient, observable agent
production_agent = TimeoutMiddleware(
    RetryMiddleware(
        CircuitBreakerMiddleware(
            RateLimiterMiddleware(
                CachingMiddleware(
                    TracingMiddleware(agent)
                )
            )
        )
    )
)
```

## Autonomous Agent Features

### Memory Management

Track conversation history with compression:

**Python:**
```python
from agenkit.memory import MemoryManager, SlidingWindowStrategy

# Create memory manager
memory = MemoryManager(
    strategy=SlidingWindowStrategy(window_size=10)
)

# Add messages to memory
memory.add_message(user_message)
memory.add_message(agent_response)

# Get recent history
history = memory.get_recent(limit=5)

# Clear old messages
memory.clear()
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit-go/memory"

// Create memory manager
memoryMgr := memory.NewMemoryManager(
    memory.NewSlidingWindowStrategy(10),
)

// Add messages
memoryMgr.AddMessage(userMessage)
memoryMgr.AddMessage(agentResponse)

// Get history
history := memoryMgr.GetRecent(5)
```

### Budget Tracking

Track token usage and costs:

**Python:**
```python
from agenkit.budget import BudgetTracker

# Create budget tracker
tracker = BudgetTracker(
    max_tokens=100000,
    max_cost=10.0,  # $10 limit
    model="claude-sonnet-4"
)

# Track usage
tracker.add_tokens(prompt_tokens=50, completion_tokens=100)

# Check status
print(f"Tokens used: {tracker.tokens_used}/{tracker.max_tokens}")
print(f"Cost: ${tracker.cost:.2f}/${tracker.max_cost:.2f}")
print(f"Budget remaining: {tracker.budget_remaining_percent():.1f}%")
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit-go/budget"

// Create tracker
tracker := budget.NewBudgetTracker(
    100000,  // max tokens
    10.0,    // max cost
    "claude-sonnet-4",
)

// Track usage
tracker.AddTokens(50, 100)

// Check status
fmt.Printf("Tokens: %d/%d\n", tracker.TokensUsed(), tracker.MaxTokens())
```

### Checkpointing

Save and restore agent state:

**Python:**
```python
from agenkit.checkpointing import CheckpointManager, FileCheckpointStorage

# Create checkpoint manager
checkpoint_mgr = CheckpointManager(
    storage=FileCheckpointStorage(directory="./checkpoints")
)

# Save checkpoint
checkpoint_mgr.save_checkpoint(
    agent_id="qa-agent-1",
    state={
        "conversation_history": history,
        "context": context_data,
        "metadata": metadata
    }
)

# Restore checkpoint
state = checkpoint_mgr.load_checkpoint("qa-agent-1")
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit-go/checkpointing"

// Create manager
storage := checkpointing.NewFileCheckpointStorage("./checkpoints")
manager := checkpointing.NewCheckpointManager(storage)

// Save checkpoint
err := manager.SaveCheckpoint("qa-agent-1", state)

// Restore
state, err := manager.LoadCheckpoint("qa-agent-1")
```

### Safety & Validation

Protect against malicious inputs:

**Python:**
```python
from agenkit.safety import (
    PromptInjectionDetector,
    ContentFilter,
    SchemaValidator,
    SensitiveDataRedactor
)

# Detect prompt injection
detector = PromptInjectionDetector()
is_injection, score, patterns = detector.detect(user_input)

if is_injection:
    print(f"Warning: Potential prompt injection detected (score: {score})")

# Filter inappropriate content
filter = ContentFilter(max_size=10000, banned_words=["spam", "scam"])
is_valid, reason = filter.validate(user_input)

# Validate output schema
validator = SchemaValidator(expected_fields={"answer": "string"})
is_valid = validator.validate(agent_output)

# Redact sensitive data
redactor = SensitiveDataRedactor()
safe_output = redactor.redact(agent_output)
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit-go/safety"

// Detect injection
detector := safety.NewPromptInjectionDetector()
isInjection, score, patterns := detector.Detect(userInput)

// Filter content
filter := safety.NewContentFilter(10000, []string{"spam", "scam"})
isValid, reason := filter.Validate(userInput)

// Validate schema
validator := safety.NewSchemaValidator(map[string]string{
    "answer": "string",
})
isValid := validator.Validate(agentOutput)
```

### Evaluation

Measure agent quality:

**Python:**
```python
from agenkit.evaluation import (
    Evaluator,
    AccuracyMetric,
    QualityMetrics,
    LatencyMetric
)

# Create evaluator
evaluator = Evaluator(
    agent=qa_agent,
    metrics=[
        AccuracyMetric(),
        QualityMetrics(),
        LatencyMetric()
    ]
)

# Define test cases
test_cases = [
    {"input": "What is the capital of France?", "expected": "Paris"},
    {"input": "What is 2+2?", "expected": "4"},
]

# Run evaluation
result = evaluator.evaluate(test_cases)

print(f"Accuracy: {result.accuracy:.2%}")
print(f"Quality: {result.quality_score:.2f}")
print(f"Avg Latency: {result.avg_latency_ms:.0f}ms")
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit-go/evaluation"

// Create evaluator
metrics := []evaluation.Metric{
    evaluation.NewAccuracyMetric(nil, false),
    evaluation.NewQualityMetrics(false, "", nil),
    evaluation.NewLatencyMetric(),
}

evaluator := evaluation.NewEvaluator(qaAgent, metrics, "")

// Test cases
testCases := []map[string]interface{}{
    {"input": "What is the capital of France?", "expected": "Paris"},
    {"input": "What is 2+2?", "expected": "4"},
}

// Evaluate
result, err := evaluator.Evaluate(testCases, "")
fmt.Printf("Accuracy: %.2f%%\n", *result.Accuracy * 100)
```

## Observability

### Distributed Tracing

**Python:**
```python
from agenkit.observability import init_tracing, TracingMiddleware

# Initialize OpenTelemetry tracing
init_tracing(
    service_name="my-agent-service",
    otlp_endpoint="http://localhost:4317"
)

# Wrap agents with tracing
traced_agent = TracingMiddleware(agent, span_name="qa-agent")

# All operations are now traced
response = await traced_agent.process(message)
```

View traces in Jaeger: `http://localhost:16686`

### Metrics

**Python:**
```python
from agenkit.observability import init_metrics, MetricsMiddleware

# Initialize Prometheus metrics
init_metrics(
    service_name="my-agent-service",
    port=8001  # Metrics endpoint
)

# Wrap agents
metered_agent = MetricsMiddleware(agent)

# Metrics are automatically collected
response = await metered_agent.process(message)
```

View metrics: `http://localhost:8001/metrics`

Available metrics:
- `agent_requests_total` - Total requests
- `agent_request_duration_seconds` - Request latency
- `agent_errors_total` - Error count

### Structured Logging

**Python:**
```python
from agenkit.observability import configure_logging

# Configure structured JSON logging with trace context
configure_logging(
    structured=True,
    include_trace_context=True,
    level="INFO"
)

# Now all logs include trace/span IDs for correlation
```

## Next Steps

### Examples

Explore 27+ comprehensive examples in the `examples/` directory:

- **Core Patterns**: Basic agent, sequential, parallel, router
- **Transport**: HTTP, gRPC, WebSocket examples
- **Middleware**: Circuit breaker, retry, timeout, rate limiting
- **Advanced**: Observability, streaming, remote agents

### Documentation

- **[Architecture](ARCHITECTURE.md)** - System design and principles
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Deployment Guide](deploy/README.md)** - Docker and Kubernetes
- **[Observability](docs/observability.md)** - Tracing and metrics setup
- **[Security](docs/SECURITY.md)** - Security best practices

### Package READMEs

Each autonomous agent package has detailed documentation:

- **[Memory Management](agenkit/memory/README.md)** - Context retention strategies
- **[Budget Tracking](agenkit/budget/README.md)** - Token and cost management
- **[Checkpointing](agenkit/checkpointing/README.md)** - State persistence
- **[Safety](agenkit/safety/README.md)** - Input/output validation
- **[Evaluation](agenkit/evaluation/README.md)** - Quality measurement

### Community

- **Website**: [https://agenkit.dev](https://agenkit.dev)
- **GitHub**: https://github.com/scttfrdmn/agenkit
- **Issues**: https://github.com/scttfrdmn/agenkit/issues
- **Examples**: https://github.com/scttfrdmn/agenkit/tree/main/examples

### Quick Start Checklist

- [ ] Install Agenkit (Python and/or Go)
- [ ] Create your first agent
- [ ] Try an orchestration pattern
- [ ] Add middleware for resilience
- [ ] Set up observability
- [ ] Run the test suite
- [ ] Explore the examples
- [ ] Deploy to production (Docker/K8s)

## Support

Having issues? Here's how to get help:

1. Check the [documentation](docs/)
2. Search [existing issues](https://github.com/scttfrdmn/agenkit/issues)
3. Create a [new issue](https://github.com/scttfrdmn/agenkit/issues/new)
4. Review [examples](examples/)

---

**Ready to build production AI agents?** Start with the examples and scale up! 🚀
