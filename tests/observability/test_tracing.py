"""Tests for distributed tracing functionality."""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import Status, StatusCode

from agenkit.interfaces import Agent, Message
from agenkit.observability import TracingMiddleware, init_tracing


class SimpleAgent(Agent):
    """Simple agent for testing."""

    def __init__(self, name: str = "test-agent", response: str = "response"):
        self._name = name
        self._response = response

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=self._response,
            metadata={"processed_by": self._name},
        )


class ErrorAgent(Agent):
    """Agent that raises an error."""

    @property
    def name(self) -> str:
        return "error-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        raise ValueError("Test error")


@pytest.fixture(scope="module")
def span_exporter():
    """Create an in-memory span exporter for testing (module-scoped)."""
    # Create provider with in-memory exporter
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield exporter

    # Shutdown at end of module
    provider.force_flush()
    provider.shutdown()


@pytest.fixture(autouse=True)
def clear_spans(span_exporter):
    """Clear spans before each test."""
    # Clear any spans from previous tests
    span_exporter.clear()
    yield
    # Spans will be available after test runs


@pytest.mark.asyncio
async def test_tracing_middleware_creates_span(span_exporter):
    """Test that TracingMiddleware creates a span."""
    agent = SimpleAgent(name="agent1")
    traced_agent = TracingMiddleware(agent)

    message = Message(role="user", content="test message")
    await traced_agent.process(message)

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "agent.agent1.process"
    assert spans[0].status.status_code == StatusCode.OK


@pytest.mark.asyncio
async def test_tracing_middleware_sets_attributes(span_exporter):
    """Test that TracingMiddleware sets correct span attributes."""
    agent = SimpleAgent(name="agent1")
    traced_agent = TracingMiddleware(agent)

    message = Message(
        role="user", content="test message", metadata={"key": "value"}
    )
    await traced_agent.process(message)

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1

    attrs = dict(spans[0].attributes)
    assert attrs["agent.name"] == "agent1"
    assert attrs["message.role"] == "user"
    assert attrs["message.content_length"] == len("test message")
    assert attrs["message.metadata.key"] == "value"


@pytest.mark.asyncio
async def test_tracing_middleware_injects_trace_context(span_exporter):
    """Test that TracingMiddleware injects trace context into response."""
    agent = SimpleAgent(name="agent1")
    traced_agent = TracingMiddleware(agent)

    message = Message(role="user", content="test")
    response = await traced_agent.process(message)

    # Check that trace context was injected
    assert response.metadata is not None
    assert "trace_context" in response.metadata
    trace_ctx = response.metadata["trace_context"]
    assert isinstance(trace_ctx, dict)
    assert "traceparent" in trace_ctx


@pytest.mark.asyncio
async def test_tracing_middleware_extracts_trace_context(span_exporter):
    """Test that TracingMiddleware extracts parent trace context."""
    agent = SimpleAgent(name="agent1")
    traced_agent = TracingMiddleware(agent)

    # Create a parent span manually
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("parent-span") as parent_span:
        parent_context = parent_span.get_span_context()

        # Inject context into message
        message = Message(
            role="user",
            content="test",
            metadata={
                "trace_context": {
                    "traceparent": (
                        f"00-{parent_context.trace_id:032x}-"
                        f"{parent_context.span_id:016x}-01"
                    )
                }
            },
        )

        await traced_agent.process(message)

    spans = span_exporter.get_finished_spans()
    # Should have parent span + child span
    assert len(spans) >= 1

    # Find the child span
    child_span = next(
        (s for s in spans if s.name == "agent.agent1.process"), None
    )
    assert child_span is not None

    # Verify parent-child relationship
    assert child_span.parent is not None
    assert child_span.context.trace_id == parent_context.trace_id


@pytest.mark.asyncio
async def test_tracing_middleware_propagates_context_across_agents(
    span_exporter,
):
    """Test trace context propagation across multiple agents."""
    agent1 = SimpleAgent(name="agent1", response="response1")
    agent2 = SimpleAgent(name="agent2", response="response2")

    traced_agent1 = TracingMiddleware(agent1)
    traced_agent2 = TracingMiddleware(agent2)

    # Process through agent1
    message = Message(role="user", content="test")
    response1 = await traced_agent1.process(message)

    # Process through agent2 with response1 (which has trace context)
    response2 = await traced_agent2.process(response1)

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 2

    # Both spans should have the same trace_id
    assert spans[0].context.trace_id == spans[1].context.trace_id

    # Verify span names
    span_names = {s.name for s in spans}
    assert "agent.agent1.process" in span_names
    assert "agent.agent2.process" in span_names


@pytest.mark.asyncio
async def test_tracing_middleware_records_errors(span_exporter):
    """Test that TracingMiddleware records errors in spans."""
    agent = ErrorAgent()
    traced_agent = TracingMiddleware(agent)

    message = Message(role="user", content="test")

    with pytest.raises(ValueError, match="Test error"):
        await traced_agent.process(message)

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    assert span.status.status_code == StatusCode.ERROR
    assert "Test error" in span.status.description

    # Check that error was recorded as an event
    events = span.events
    assert len(events) > 0
    error_event = next((e for e in events if e.name == "exception"), None)
    assert error_event is not None


@pytest.mark.asyncio
async def test_tracing_middleware_custom_span_name(span_exporter):
    """Test that TracingMiddleware accepts custom span name."""
    agent = SimpleAgent(name="agent1")
    traced_agent = TracingMiddleware(agent, span_name="custom.operation")

    message = Message(role="user", content="test")
    await traced_agent.process(message)

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "custom.operation"


@pytest.mark.asyncio
async def test_tracing_init_with_console_export():
    """Test init_tracing with console export."""
    provider = init_tracing(
        service_name="test-service", console_export=True
    )
    assert isinstance(provider, TracerProvider)

    # Verify tracer works
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-span") as span:
        assert span.is_recording()


@pytest.mark.asyncio
async def test_tracing_middleware_preserves_agent_interface(span_exporter):
    """Test that TracingMiddleware preserves Agent interface."""
    agent = SimpleAgent(name="agent1")
    traced_agent = TracingMiddleware(agent)

    # Check that agent interface is preserved
    assert traced_agent.name == "agent1"
    assert traced_agent.capabilities == ["test"]

    # Check that process works
    message = Message(role="user", content="test")
    response = await traced_agent.process(message)
    assert response.content == "response"
