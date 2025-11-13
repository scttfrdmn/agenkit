# Python Observability API Reference

Complete API reference for Agenkit's Python observability module.

## Module: `agenkit.observability`

### Functions

#### `init_tracing()`

Initialize OpenTelemetry distributed tracing.

```python
def init_tracing(
    service_name: str = "agenkit",
    otlp_endpoint: str | None = None,
    console_export: bool = False,
) -> TracerProvider
```

**Parameters:**
- `service_name` (str): Name to identify this service in traces. Default: `"agenkit"`.
- `otlp_endpoint` (str | None): OTLP collector endpoint (e.g., `"localhost:4317"`). If None, OTLP export is disabled. Default: `None`.
- `console_export` (bool): Whether to export traces to console for debugging. Default: `False`.

**Returns:**
- `TracerProvider`: The configured OpenTelemetry tracer provider.

**Example:**
```python
from agenkit.observability import init_tracing

# Development: console export
provider = init_tracing(
    service_name="my-agent",
    console_export=True,
)

# Production: OTLP export to Jaeger/Tempo
provider = init_tracing(
    service_name="my-agent",
    otlp_endpoint="localhost:4317",
)
```

---

#### `init_metrics()`

Initialize OpenTelemetry metrics with Prometheus export.

```python
def init_metrics(
    service_name: str = "agenkit",
    port: int = 8000,
) -> MeterProvider
```

**Parameters:**
- `service_name` (str): Name to identify this service in metrics. Default: `"agenkit"`.
- `port` (int): Port for Prometheus metrics HTTP endpoint. Default: `8000`. Note: Currently unused as Prometheus exporter uses default configuration.

**Returns:**
- `MeterProvider`: The configured OpenTelemetry meter provider.

**Example:**
```python
from agenkit.observability import init_metrics

provider = init_metrics(
    service_name="my-agent",
    port=8001,
)

# Metrics available at http://localhost:8001/metrics
```

---

#### `configure_logging()`

Configure structured logging with optional trace correlation.

```python
def configure_logging(
    level: int = logging.INFO,
    structured: bool = True,
    include_trace_context: bool = True,
) -> None
```

**Parameters:**
- `level` (int): Python logging level (e.g., `logging.INFO`, `logging.DEBUG`). Default: `logging.INFO`.
- `structured` (bool): Whether to use JSON structured logging format. Default: `True`.
- `include_trace_context` (bool): Whether to include trace_id and span_id in logs. Default: `True`.

**Example:**
```python
import logging
from agenkit.observability import configure_logging

# JSON logs with trace correlation
configure_logging(
    level=logging.INFO,
    structured=True,
    include_trace_context=True,
)

# Plain text logs without trace correlation
configure_logging(
    level=logging.DEBUG,
    structured=False,
    include_trace_context=False,
)
```

---

#### `get_logger_with_trace()`

Get a logger instance that includes trace context in log records.

```python
def get_logger_with_trace(name: str) -> logging.Logger
```

**Parameters:**
- `name` (str): Logger name, typically `__name__`.

**Returns:**
- `logging.Logger`: Logger instance with trace context filter applied.

**Example:**
```python
from agenkit.observability import get_logger_with_trace

logger = get_logger_with_trace(__name__)

# Logs will automatically include trace_id and span_id when in a span
logger.info("Processing request", extra={"user_id": "123"})
```

---

#### `get_tracer()`

Get a tracer instance for manual instrumentation.

```python
def get_tracer(name: str = "agenkit.observability") -> trace.Tracer
```

**Parameters:**
- `name` (str): Tracer name for grouping spans. Default: `"agenkit.observability"`.

**Returns:**
- `trace.Tracer`: OpenTelemetry tracer instance.

**Example:**
```python
from agenkit.observability import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("custom-operation") as span:
    span.set_attribute("key", "value")
    # Do work...
```

---

#### `get_meter()`

Get a meter instance for manual metric recording.

```python
def get_meter(name: str = "agenkit.observability") -> metrics.Meter
```

**Parameters:**
- `name` (str): Meter name for grouping metrics. Default: `"agenkit.observability"`.

**Returns:**
- `metrics.Meter`: OpenTelemetry meter instance.

**Example:**
```python
from agenkit.observability import get_meter

meter = get_meter(__name__)
counter = meter.create_counter(
    "my_counter",
    description="Custom counter metric",
)
counter.add(1, {"key": "value"})
```

---

### Classes

#### `TracingMiddleware`

Middleware that adds distributed tracing to agent processing.

```python
class TracingMiddleware:
    def __init__(
        self,
        agent: Agent,
        span_name: str | None = None,
    )
```

**Parameters:**
- `agent` (Agent): The agent to wrap with tracing.
- `span_name` (str | None): Custom span name. If None, uses `"agent.{agent.name}.process"`. Default: `None`.

**Methods:**

##### `process()`

Process a message with distributed tracing.

```python
async def process(self, message: Message) -> Message
```

**Parameters:**
- `message` (Message): Input message to process.

**Returns:**
- `Message`: Response message with trace context injected into metadata.

**Raises:**
- Any exception raised by the wrapped agent.

**Behavior:**
- Extracts parent trace context from `message.metadata["trace_context"]`
- Creates a new span as a child of parent context
- Records span attributes (agent name, message role, content length, metadata)
- Calls wrapped agent's `process()` method
- Records success status or error
- Injects trace context into response metadata

**Example:**
```python
from agenkit.observability import TracingMiddleware

base_agent = MyAgent()
traced_agent = TracingMiddleware(base_agent)

# Process message - span is created automatically
response = await traced_agent.process(message)

# Response includes trace context for propagation
print(response.metadata["trace_context"])
# {'traceparent': '00-...', ...}
```

**Properties:**
- `name` (str): Returns the wrapped agent's name.
- `capabilities` (list[str]): Returns the wrapped agent's capabilities.

---

#### `MetricsMiddleware`

Middleware that adds metrics collection to agent processing.

```python
class MetricsMiddleware:
    def __init__(self, agent: Agent)
```

**Parameters:**
- `agent` (Agent): The agent to wrap with metrics collection.

**Methods:**

##### `process()`

Process a message with metrics collection.

```python
async def process(self, message: Message) -> Message
```

**Parameters:**
- `message` (Message): Input message to process.

**Returns:**
- `Message`: Response message from wrapped agent.

**Raises:**
- Any exception raised by the wrapped agent.

**Metrics Recorded:**
- `agenkit.agent.requests`: Counter of total requests
- `agenkit.agent.errors`: Counter of errors (only on failure)
- `agenkit.agent.latency`: Histogram of processing latency in milliseconds
- `agenkit.agent.message_size`: Histogram of message content size in bytes

**Attributes (Labels):**
- `agent.name`: Name of the agent
- `message.role`: Role of the message
- `status`: "success" or "error"
- `error.type`: Type of exception (only on error)

**Example:**
```python
from agenkit.observability import MetricsMiddleware

base_agent = MyAgent()
monitored_agent = MetricsMiddleware(base_agent)

# Process message - metrics are recorded automatically
response = await monitored_agent.process(message)
```

**Properties:**
- `name` (str): Returns the wrapped agent's name.
- `capabilities` (list[str]): Returns the wrapped agent's capabilities.

---

#### `TraceContextFilter`

Logging filter that adds trace context to log records.

```python
class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool
```

**Behavior:**
- Extracts current span context from OpenTelemetry
- Adds `trace_id`, `span_id`, and `trace_flags` attributes to log record
- Sets attributes to `None` if no active span

**Example:**
```python
import logging
from agenkit.observability import TraceContextFilter

handler = logging.StreamHandler()
handler.addFilter(TraceContextFilter())

logger = logging.getLogger(__name__)
logger.addHandler(handler)

# Logs will include trace context
logger.info("Processing request")
```

---

#### `StructuredFormatter`

Logging formatter that outputs JSON structured logs.

```python
class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str
```

**Output Format:**
```json
{
  "timestamp": "2025-11-12T20:00:00.000000",
  "level": "INFO",
  "logger": "mymodule",
  "message": "Log message",
  "trace_id": "...",
  "span_id": "...",
  "custom_field": "custom_value"
}
```

**Example:**
```python
import logging
from agenkit.observability import StructuredFormatter, TraceContextFilter

handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
handler.addFilter(TraceContextFilter())

logger = logging.getLogger(__name__)
logger.addHandler(handler)

logger.info("Processing", extra={"user_id": "123"})
# Output: {"timestamp": "...", "level": "INFO", "message": "Processing", "user_id": "123"}
```

---

## Helper Functions

### `extract_trace_context()`

Extract W3C Trace Context from message metadata.

```python
def extract_trace_context(metadata: dict[str, Any]) -> dict[str, str]
```

**Parameters:**
- `metadata` (dict): Message metadata dictionary.

**Returns:**
- `dict[str, str]`: Trace context carrier (e.g., `{"traceparent": "00-..."}`)

**Example:**
```python
from agenkit.observability.tracing import extract_trace_context

carrier = extract_trace_context(message.metadata)
# carrier = {'traceparent': '00-...', ...}
```

---

### `inject_trace_context()`

Inject current trace context into metadata dictionary.

```python
def inject_trace_context(metadata: dict[str, Any] | None) -> dict[str, Any]
```

**Parameters:**
- `metadata` (dict | None): Existing metadata dictionary or None.

**Returns:**
- `dict[str, Any]`: Metadata with trace context added under `"trace_context"` key.

**Example:**
```python
from agenkit.observability.tracing import inject_trace_context

metadata = {"key": "value"}
metadata = inject_trace_context(metadata)
# metadata = {"key": "value", "trace_context": {"traceparent": "00-..."}}
```

---

## Type Definitions

### Message

Agent message type (from `agenkit.interfaces`):

```python
@dataclass(frozen=True)
class Message:
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

### Agent

Agent interface (from `agenkit.interfaces`):

```python
class Agent(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> list[str]: ...

    async def process(self, message: Message) -> Message: ...
```

---

## Usage Patterns

### Complete Setup

```python
import logging
from agenkit.observability import (
    init_tracing,
    init_metrics,
    configure_logging,
    TracingMiddleware,
    MetricsMiddleware,
    get_logger_with_trace,
)

# Initialize observability
init_tracing("my-service", console_export=True)
init_metrics("my-service", port=8001)
configure_logging(logging.INFO, structured=True, include_trace_context=True)

# Get logger
logger = get_logger_with_trace(__name__)

# Wrap agent with middleware
base_agent = MyAgent()
traced_agent = TracingMiddleware(base_agent)
monitored_agent = MetricsMiddleware(traced_agent)

# Use agent
logger.info("Starting request")
response = await monitored_agent.process(message)
logger.info("Request complete")
```

### Custom Instrumentation

```python
from agenkit.observability import get_tracer, get_meter

# Manual tracing
tracer = get_tracer(__name__)
with tracer.start_as_current_span("database-query") as span:
    span.set_attribute("query", "SELECT * FROM users")
    result = await db.query(...)
    span.set_attribute("rows", len(result))

# Manual metrics
meter = get_meter(__name__)
cache_hits = meter.create_counter("cache.hits")
cache_hits.add(1, {"cache_name": "user-cache"})
```

---

## See Also

- [Observability Guide](./observability.md) - Comprehensive usage guide
- [Go API Reference](./observability-go-api.md) - Go observability API
- [Examples](../examples/observability/) - Working examples
