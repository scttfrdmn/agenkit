"""
Example demonstrating OpenTelemetry observability features in Agenkit.

Shows distributed tracing, metrics collection, and structured logging
with trace correlation across multiple agents.
"""

import asyncio
import logging

from agenkit.interfaces import Agent, Message
from agenkit.observability import (
    TracingMiddleware,
    MetricsMiddleware,
    init_tracing,
    init_metrics,
    configure_logging,
    get_logger_with_trace,
)


class SimpleAgent(Agent):
    """Simple agent for demonstration."""

    def __init__(self, name: str):
        self._name = name
        self._logger = get_logger_with_trace(__name__)

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["process"]

    async def process(self, message: Message) -> Message:
        """Process a message."""
        self._logger.info(
            f"Agent {self._name} processing message",
            extra={"agent": self._name, "content_length": len(message.content)},
        )

        # Simulate some processing
        await asyncio.sleep(0.1)

        response_content = f"Processed by {self._name}: {message.content}"

        self._logger.info(
            f"Agent {self._name} completed processing",
            extra={"agent": self._name, "response_length": len(response_content)},
        )

        return Message(
            role="agent",
            content=response_content,
            metadata={"processed_by": self._name},
        )


async def main():
    """Run observability example."""
    print("=== Agenkit Observability Example ===\n")

    # Initialize OpenTelemetry
    print("1. Initializing OpenTelemetry...")
    init_tracing(
        service_name="agenkit-example",
        console_export=True,  # Export traces to console for demo
    )
    init_metrics(
        service_name="agenkit-example",
        port=8001,  # Prometheus metrics on port 8001
    )

    # Configure structured logging with trace correlation
    configure_logging(
        level=logging.INFO,
        structured=True,
        include_trace_context=True,
    )

    print("✓ Tracing, metrics, and logging initialized\n")

    # Create agents with observability
    print("2. Creating agents with tracing and metrics...")
    base_agent1 = SimpleAgent("agent-1")
    base_agent2 = SimpleAgent("agent-2")

    # Wrap with tracing
    traced_agent1 = TracingMiddleware(base_agent1)
    traced_agent2 = TracingMiddleware(base_agent2)

    # Wrap with metrics
    agent1 = MetricsMiddleware(traced_agent1)
    agent2 = MetricsMiddleware(traced_agent2)

    print("✓ Agents wrapped with observability middleware\n")

    # Process messages through agent chain
    print("3. Processing messages through agents...")
    message = Message(
        role="user",
        content="Hello from the observability example!",
    )

    # Process through agent1
    print(f"   → Sending to {agent1.name}...")
    response1 = await agent1.process(message)

    # Process through agent2 with propagated trace context
    print(f"   → Sending to {agent2.name}...")
    response2 = await agent2.process(response1)

    print(f"\n   ✓ Final response: {response2.content}\n")

    # Show observability features
    print("4. Observability Features:")
    print("   • Distributed traces: Check console output above")
    print("   • Trace context propagated across agents")
    print("   • Structured logs include trace_id and span_id")
    print("   • Metrics collected for requests, errors, and latency")
    print(f"   • Prometheus metrics available at http://localhost:8001/metrics\n")

    print("5. View Traces and Metrics:")
    print("   • Traces exported to console (see above)")
    print("   • Metrics: curl http://localhost:8001/metrics")
    print("   • Logs: Check structured JSON logs above\n")

    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
