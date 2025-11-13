"""
Distributed tracing for Agenkit using OpenTelemetry.

Provides automatic span creation for agent processing with context propagation
across process and language boundaries.
"""

from typing import Any
from contextvars import ContextVar

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from agenkit.interfaces import Agent, Message

# Global tracer instance
_tracer: trace.Tracer | None = None

# Context variable for current span
_current_span: ContextVar[trace.Span | None] = ContextVar("current_span", default=None)


def init_tracing(
    service_name: str = "agenkit",
    otlp_endpoint: str | None = None,
    console_export: bool = False,
) -> TracerProvider:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service for trace identification
        otlp_endpoint: Optional OTLP collector endpoint (e.g., "http://localhost:4317")
        console_export: If True, export spans to console for debugging

    Returns:
        Configured TracerProvider
    """
    global _tracer

    # Create resource with service name
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add exporters
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if console_export:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Set as global provider
    trace.set_tracer_provider(provider)

    # Get tracer
    _tracer = trace.get_tracer(__name__)

    return provider


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        # Initialize with defaults if not already initialized
        init_tracing()
    return _tracer  # type: ignore


def extract_trace_context(metadata: dict[str, Any]) -> dict[str, str]:
    """
    Extract W3C Trace Context from message metadata.

    Args:
        metadata: Message metadata that may contain trace context

    Returns:
        Dictionary with trace context headers
    """
    carrier = {}
    if metadata and "trace_context" in metadata:
        trace_ctx = metadata["trace_context"]
        if isinstance(trace_ctx, dict):
            carrier = trace_ctx
    return carrier


def inject_trace_context(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Inject current W3C Trace Context into message metadata.

    Args:
        metadata: Message metadata to inject trace context into

    Returns:
        Updated metadata with trace context
    """
    carrier: dict[str, str] = {}
    propagator = TraceContextTextMapPropagator()
    propagator.inject(carrier)

    if carrier:
        if metadata is None:
            metadata = {}
        metadata["trace_context"] = carrier

    return metadata


class TracingMiddleware:
    """
    Middleware that adds distributed tracing to agent processing.

    Automatically creates spans for agent operations and propagates
    trace context across agent boundaries.
    """

    def __init__(self, agent: Agent, span_name: str | None = None):
        """
        Initialize tracing middleware.

        Args:
            agent: The agent to wrap with tracing
            span_name: Custom span name (defaults to agent name)
        """
        self._agent = agent
        self._span_name = span_name or f"agent.{agent.name}.process"
        self._tracer = get_tracer()

    @property
    def name(self) -> str:
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    async def process(self, message: Message) -> Message:
        """Process message with distributed tracing."""
        # Extract parent context from message metadata
        parent_context = None
        if message.metadata:
            carrier = extract_trace_context(message.metadata)
            if carrier:
                propagator = TraceContextTextMapPropagator()
                parent_context = propagator.extract(carrier)

        # Create span
        with self._tracer.start_as_current_span(
            self._span_name,
            context=parent_context,
            kind=SpanKind.INTERNAL,
        ) as span:
            # Set span attributes
            span.set_attribute("agent.name", self._agent.name)
            span.set_attribute("message.role", message.role)
            span.set_attribute("message.content_length", len(message.content))

            if message.metadata:
                for key, value in message.metadata.items():
                    if key != "trace_context" and isinstance(value, (str, int, float, bool)):
                        span.set_attribute(f"message.metadata.{key}", value)

            try:
                # Process message
                response = await self._agent.process(message)

                # Set success status
                span.set_status(Status(StatusCode.OK))

                # Inject trace context into response
                if response.metadata is None:
                    response.metadata = {}
                response.metadata = inject_trace_context(response.metadata)

                return response

            except Exception as e:
                # Record exception
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
