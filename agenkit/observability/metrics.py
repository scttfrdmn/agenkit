"""
Metrics collection for Agenkit using OpenTelemetry.

Provides Prometheus-compatible metrics for agent processing,
including request counts, latencies, and error rates.
"""

import time
from typing import Any

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

from agenkit.interfaces import Agent, Message

# Global meter instance
_meter: metrics.Meter | None = None


def init_metrics(
    service_name: str = "agenkit",
    port: int = 8000,
) -> MeterProvider:
    """
    Initialize OpenTelemetry metrics with Prometheus export.

    Args:
        service_name: Name of the service for metric identification
        port: Port for Prometheus metrics endpoint

    Returns:
        Configured MeterProvider
    """
    global _meter

    # Create resource
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
    })

    # Create Prometheus exporter
    reader = PrometheusMetricReader(port=port)

    # Create meter provider
    provider = MeterProvider(
        resource=resource,
        metric_readers=[reader],
    )

    # Set as global provider
    metrics.set_meter_provider(provider)

    # Get meter
    _meter = metrics.get_meter(__name__)

    return provider


def get_meter() -> metrics.Meter:
    """Get the global meter instance."""
    global _meter
    if _meter is None:
        # Initialize with defaults if not already initialized
        init_metrics()
    return _meter  # type: ignore


class MetricsMiddleware:
    """
    Middleware that collects metrics for agent processing.

    Tracks request counts, latencies, error rates, and message sizes.
    Exports metrics in Prometheus format.
    """

    def __init__(self, agent: Agent):
        """
        Initialize metrics middleware.

        Args:
            agent: The agent to collect metrics for
        """
        self._agent = agent
        self._meter = get_meter()

        # Create metrics
        self._request_counter = self._meter.create_counter(
            name="agenkit.agent.requests",
            description="Total number of agent requests",
            unit="1",
        )

        self._error_counter = self._meter.create_counter(
            name="agenkit.agent.errors",
            description="Total number of agent errors",
            unit="1",
        )

        self._latency_histogram = self._meter.create_histogram(
            name="agenkit.agent.latency",
            description="Agent processing latency",
            unit="ms",
        )

        self._message_size_histogram = self._meter.create_histogram(
            name="agenkit.agent.message_size",
            description="Message content size",
            unit="bytes",
        )

    @property
    def name(self) -> str:
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    async def process(self, message: Message) -> Message:
        """Process message with metrics collection."""
        start_time = time.time()

        # Common attributes
        attributes = {
            "agent.name": self._agent.name,
            "message.role": message.role,
        }

        try:
            # Record message size
            message_size = len(message.content.encode('utf-8'))
            self._message_size_histogram.record(
                message_size,
                attributes=attributes,
            )

            # Process message
            response = await self._agent.process(message)

            # Record success
            success_attributes = {**attributes, "status": "success"}
            self._request_counter.add(1, attributes=success_attributes)

            # Record latency
            latency_ms = (time.time() - start_time) * 1000
            self._latency_histogram.record(latency_ms, attributes=success_attributes)

            return response

        except Exception as e:
            # Record error
            error_attributes = {
                **attributes,
                "status": "error",
                "error.type": type(e).__name__,
            }
            self._request_counter.add(1, attributes=error_attributes)
            self._error_counter.add(1, attributes=error_attributes)

            # Record latency even for errors
            latency_ms = (time.time() - start_time) * 1000
            self._latency_histogram.record(latency_ms, attributes=error_attributes)

            raise
