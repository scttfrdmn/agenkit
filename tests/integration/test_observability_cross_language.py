"""Cross-language integration tests for observability.

Tests trace propagation and distributed tracing across Python ↔ Go boundaries
using OpenTelemetry.
"""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agenkit.adapters.python.remote_agent import RemoteAgent
from agenkit.interfaces import Agent, Message
from agenkit.observability.tracing import (
    TracingMiddleware,
    init_tracing,
    inject_trace_context,
)

from .helpers import go_http_server, python_http_server, go_grpc_server, python_grpc_server


@pytest.fixture(scope="module")
def tracing_setup():
    """Set up OpenTelemetry tracing with in-memory exporter for testing."""
    # Create in-memory span exporter to capture spans
    span_exporter = InMemorySpanExporter()

    # Create tracer provider
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    # Set as global provider
    trace.set_tracer_provider(provider)

    yield provider, span_exporter

    # Cleanup - force flush and shutdown provider
    provider.force_flush()
    provider.shutdown()


@pytest.fixture(autouse=True)
def clear_spans(tracing_setup):
    """Clear spans before each test."""
    _, span_exporter = tracing_setup
    span_exporter.clear()
    yield
    # Clear again after test
    span_exporter.clear()


# HTTP Transport Trace Propagation Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_trace_propagation_python_to_go_http(tracing_setup):
    """Test trace context propagates from Python → Go over HTTP."""
    provider, span_exporter = tracing_setup

    async with go_http_server() as (port, process):
        # Create remote agent
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"http://localhost:{port}"
        )

        # Create a parent span
        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("test-parent-span") as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id

            # Send message with trace context
            message = Message(role="user", content="Test trace propagation")

            # Inject trace context into message
            message_metadata = inject_trace_context({})
            message = Message(
                role="user",
                content="Test trace propagation",
                metadata=message_metadata
            )

            response = await agent.process(message)

            # Verify response received
            assert response.role == "agent"
            assert "Echo: Test trace propagation" in response.content

            # Verify trace context is in response metadata
            assert "trace_context" in response.metadata

        # Get captured spans (after span context exits)
        provider.force_flush()  # Ensure all spans are exported
        spans = span_exporter.get_finished_spans()

        # Verify parent span was created
        assert len(spans) >= 1
        assert any(span.name == "test-parent-span" for span in spans)

        # Verify trace ID consistency
        parent_span_obj = next(span for span in spans if span.name == "test-parent-span")
        assert parent_span_obj.context.trace_id == parent_trace_id


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_trace_propagation_python_to_go_http_with_metadata(tracing_setup):
    """Test trace propagation preserves message metadata: Python → Go HTTP."""
    provider, span_exporter = tracing_setup

    async with go_http_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"http://localhost:{port}"
        )

        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("test-span"):
            # Create message with both custom metadata and trace context
            message_metadata = {
                "request_id": "trace-test-123",
                "custom_field": "test-value"
            }
            message_metadata = inject_trace_context(message_metadata)

            message = Message(
                role="user",
                content="Test with metadata",
                metadata=message_metadata
            )

            response = await agent.process(message)

            # Verify response
            assert response.role == "agent"

            # Verify both trace context and original metadata are preserved
            assert "trace_context" in response.metadata


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_go_to_python_http_trace_propagation(tracing_setup):
    """Test trace context from Go → Python server over HTTP."""
    provider, span_exporter = tracing_setup

    # Create test agent with tracing
    class TracedTestAgent(Agent):
        @property
        def name(self) -> str:
            return "traced-test-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            # Agent will be wrapped with TracingMiddleware
            return Message(
                role="agent",
                content=f"Echo: {message.content}",
                metadata={
                    "original": message.content,
                    "language": "python",
                }
            )

    base_agent = TracedTestAgent()
    traced_agent = TracingMiddleware(base_agent)

    # Start Python HTTP server with traced agent
    from agenkit.adapters.python.http_server import HTTPAgentServer
    from .helpers import find_free_port

    port = find_free_port()
    server = HTTPAgentServer(traced_agent, host="localhost", port=port)

    try:
        await server.start()

        # Create client with trace context
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"http://localhost:{port}"
        )

        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("client-span") as client_span:
            client_trace_id = client_span.get_span_context().trace_id

            # Send message with trace context
            message_metadata = inject_trace_context({})
            message = Message(
                role="user",
                content="Test Go to Python",
                metadata=message_metadata
            )

            response = await agent.process(message)

            # Verify response
            assert response.role == "agent"
            assert "Echo: Test Go to Python" in response.content

            # Verify trace context propagated
            assert "trace_context" in response.metadata

        # Get spans (after span context exits)
        provider.force_flush()  # Ensure all spans are exported
        spans = span_exporter.get_finished_spans()

        # Verify spans were created
        assert len(spans) >= 1

        # Look for our client span
        client_spans = [s for s in spans if s.name == "client-span"]
        assert len(client_spans) == 1
        assert client_spans[0].context.trace_id == client_trace_id

    finally:
        await server.stop()


# gRPC Transport Trace Propagation Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_trace_propagation_python_to_go_grpc(tracing_setup):
    """Test trace context propagates from Python → Go over gRPC."""
    provider, span_exporter = tracing_setup

    async with go_grpc_server() as (port, process):
        # Create remote agent
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
        )

        # Create a parent span
        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("grpc-parent-span") as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id

            # Send message with trace context
            message_metadata = inject_trace_context({})
            message = Message(
                role="user",
                content="gRPC trace test",
                metadata=message_metadata
            )

            response = await agent.process(message)

            # Verify response received
            assert response.role == "agent"
            assert "Echo: gRPC trace test" in response.content

            # Verify trace context is in response metadata
            assert "trace_context" in response.metadata

        # Get captured spans (after span context exits)
        provider.force_flush()  # Ensure all spans are exported
        spans = span_exporter.get_finished_spans()

        # Verify parent span was created
        assert len(spans) >= 1
        parent_spans = [s for s in spans if s.name == "grpc-parent-span"]
        assert len(parent_spans) == 1
        assert parent_spans[0].context.trace_id == parent_trace_id


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_trace_propagation_go_to_python_grpc(tracing_setup):
    """Test trace context from Go → Python server over gRPC."""
    provider, span_exporter = tracing_setup

    # Create test agent with tracing
    class TracedTestAgent(Agent):
        @property
        def name(self) -> str:
            return "traced-grpc-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            return Message(
                role="agent",
                content=f"Echo: {message.content}",
                metadata={
                    "original": message.content,
                    "language": "python",
                }
            )

    base_agent = TracedTestAgent()
    traced_agent = TracingMiddleware(base_agent)

    # Start Python gRPC server with traced agent
    from agenkit.adapters.python.grpc_server import GRPCServer
    from .helpers import find_free_port
    import asyncio

    port = find_free_port()
    server = GRPCServer(traced_agent, f"localhost:{port}")

    try:
        await server.start()
        await asyncio.sleep(0.5)  # Wait for server to start

        # Create client with trace context
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
        )

        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("grpc-client-span") as client_span:
            client_trace_id = client_span.get_span_context().trace_id

            # Send message with trace context
            message_metadata = inject_trace_context({})
            message = Message(
                role="user",
                content="gRPC Go to Python",
                metadata=message_metadata
            )

            response = await agent.process(message)

            # Verify response
            assert response.role == "agent"
            assert "Echo: gRPC Go to Python" in response.content

            # Verify trace context propagated
            assert "trace_context" in response.metadata

        # Get spans (after span context exits)
        provider.force_flush()  # Ensure all spans are exported
        spans = span_exporter.get_finished_spans()

        # Verify spans were created
        assert len(spans) >= 1

        # Look for our client span
        client_spans = [s for s in spans if s.name == "grpc-client-span"]
        assert len(client_spans) == 1
        assert client_spans[0].context.trace_id == client_trace_id

    finally:
        await server.stop()


# Trace Context Format Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_w3c_trace_context_format():
    """Test W3C Trace Context format is used for cross-language compatibility."""
    from agenkit.observability.tracing import inject_trace_context, extract_trace_context
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    # Create a span to establish trace context
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("test-span") as span:
        trace_id = span.get_span_context().trace_id
        span_id = span.get_span_context().span_id

        # Inject trace context
        metadata = inject_trace_context({})

        # Verify trace context is present
        assert "trace_context" in metadata
        trace_ctx = metadata["trace_context"]

        # Verify W3C Trace Context fields
        assert "traceparent" in trace_ctx

        # Parse traceparent header
        traceparent = trace_ctx["traceparent"]
        parts = traceparent.split("-")

        # W3C Trace Context format: version-trace_id-span_id-flags
        assert len(parts) == 4
        assert parts[0] == "00"  # Version

        # Verify trace ID matches
        injected_trace_id = int(parts[1], 16)
        assert injected_trace_id == trace_id


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_trace_context_extraction():
    """Test trace context can be extracted from metadata."""
    from agenkit.observability.tracing import inject_trace_context, extract_trace_context

    # Create trace context
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("parent-span") as parent:
        parent_trace_id = parent.get_span_context().trace_id

        # Inject into metadata
        metadata = inject_trace_context({"custom_field": "value"})

        # Extract trace context
        carrier = extract_trace_context(metadata)

        # Verify extraction
        assert "traceparent" in carrier

        # Verify custom field preserved
        assert metadata["custom_field"] == "value"


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_observability_cross_language.py -v -m cross_language
    pytest.main([__file__, "-v", "-m", "cross_language"])
