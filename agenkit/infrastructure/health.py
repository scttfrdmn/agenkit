"""Health checks and monitoring for production deployments.

Provides Kubernetes-style health probes and metrics export:
- Liveness probes: Is the agent process running?
- Readiness probes: Is the agent ready to handle requests?
- Startup probes: Has the agent finished initialization?
- Metrics export: Prometheus-compatible metrics

Supports both HTTP endpoints and programmatic checks for flexible deployment.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agenkit.interfaces import Agent, Message


class HealthStatus(Enum):
    """Health check status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ProbeType(Enum):
    """Types of health probes."""

    LIVENESS = "liveness"  # Is the process alive?
    READINESS = "readiness"  # Ready to accept traffic?
    STARTUP = "startup"  # Has initialization completed?


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    status: HealthStatus
    probe_type: ProbeType
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""

    # Liveness probe settings
    liveness_enabled: bool = True
    liveness_interval: float = 10.0  # seconds
    liveness_timeout: float = 5.0  # seconds
    liveness_failure_threshold: int = 3  # Failures before unhealthy

    # Readiness probe settings
    readiness_enabled: bool = True
    readiness_interval: float = 5.0  # seconds
    readiness_timeout: float = 3.0  # seconds
    readiness_failure_threshold: int = 2

    # Startup probe settings
    startup_enabled: bool = True
    startup_timeout: float = 30.0  # seconds
    startup_failure_threshold: int = 30  # 30 attempts = 5 minutes at 10s intervals

    # Custom health check function
    custom_check: Callable[[Agent], bool] | None = None


@dataclass
class HealthMetrics:
    """Metrics for health checks."""

    total_checks: dict[ProbeType, int] = field(default_factory=dict)
    successful_checks: dict[ProbeType, int] = field(default_factory=dict)
    failed_checks: dict[ProbeType, int] = field(default_factory=dict)
    last_check_time: dict[ProbeType, float] = field(default_factory=dict)
    last_check_duration: dict[ProbeType, float] = field(default_factory=dict)
    consecutive_failures: dict[ProbeType, int] = field(default_factory=dict)
    uptime_start: float = field(default_factory=time.time)

    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self.uptime_start


class HealthChecker:
    """Health checker for monitoring agent health.

    Example:
        ```python
        agent = OpenAILLM("gpt-4", api_key="...")
        health = HealthChecker(agent)

        # Start background health checks
        await health.start()

        # Check health programmatically
        liveness = await health.check_liveness()
        readiness = await health.check_readiness()

        print(f"Liveness: {liveness.status}")
        print(f"Readiness: {readiness.status}")

        # Export Prometheus metrics
        metrics_text = health.export_prometheus_metrics()

        # Stop health checks
        await health.stop()
        ```
    """

    def __init__(self, agent: Agent, config: HealthCheckConfig | None = None):
        """Initialize health checker.

        Args:
            agent: Agent to monitor
            config: Health check configuration
        """
        self._agent = agent
        self._config = config or HealthCheckConfig()
        self._metrics = HealthMetrics()

        # Health check state
        self._is_alive = True
        self._is_ready = False
        self._startup_complete = False
        self._last_successful_request: float | None = None

        # Background tasks
        self._tasks: list[asyncio.Task] = []
        self._should_stop = False

    @property
    def metrics(self) -> HealthMetrics:
        """Return current metrics."""
        return self._metrics

    @property
    def is_healthy(self) -> bool:
        """Return overall health status."""
        return self._is_alive and self._is_ready

    async def start(self) -> None:
        """Start background health check tasks."""
        if self._tasks:
            return  # Already started

        self._should_stop = False

        if self._config.liveness_enabled:
            task = asyncio.create_task(self._liveness_loop())
            self._tasks.append(task)

        if self._config.readiness_enabled:
            task = asyncio.create_task(self._readiness_loop())
            self._tasks.append(task)

        if self._config.startup_enabled and not self._startup_complete:
            task = asyncio.create_task(self._startup_check())
            self._tasks.append(task)

    async def stop(self) -> None:
        """Stop background health check tasks."""
        self._should_stop = True

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def check_liveness(self) -> HealthCheckResult:
        """Perform liveness check.

        Liveness checks if the agent process is alive and responsive.
        Failure indicates the process should be restarted.

        Returns:
            Health check result
        """
        start_time = time.time()
        probe_type = ProbeType.LIVENESS

        self._track_check_started(probe_type)

        try:
            # Basic liveness: Can we call a method?
            _ = self._agent.name
            _ = self._agent.capabilities

            # Custom check if provided
            if self._config.custom_check:
                is_healthy = self._config.custom_check(self._agent)
                if not is_healthy:
                    raise Exception("Custom health check failed")

            # Success
            duration_ms = (time.time() - start_time) * 1000
            self._track_check_success(probe_type, duration_ms)

            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                probe_type=probe_type,
                message="Agent process is alive",
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._track_check_failure(probe_type, duration_ms)

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                probe_type=probe_type,
                message=f"Liveness check failed: {e}",
                duration_ms=duration_ms,
            )

    async def check_readiness(self) -> HealthCheckResult:
        """Perform readiness check.

        Readiness checks if the agent is ready to handle requests.
        Failure indicates traffic should not be routed to this agent.

        Returns:
            Health check result
        """
        start_time = time.time()
        probe_type = ProbeType.READINESS

        self._track_check_started(probe_type)

        try:
            # Check if startup completed
            if self._config.startup_enabled and not self._startup_complete:
                raise Exception("Startup not complete")

            # Test with a simple request
            test_message = Message(role="system", content="readiness_check")

            async with asyncio.timeout(self._config.readiness_timeout):
                response = await self._agent.process(test_message)

            # Check response is valid
            if not response or not response.content:
                raise Exception("Invalid response from agent")

            # Success
            duration_ms = (time.time() - start_time) * 1000
            self._track_check_success(probe_type, duration_ms)
            self._last_successful_request = time.time()

            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                probe_type=probe_type,
                message="Agent is ready to handle requests",
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._track_check_failure(probe_type, duration_ms)

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                probe_type=probe_type,
                message=f"Readiness check failed: {e}",
                duration_ms=duration_ms,
            )

    async def check_startup(self) -> HealthCheckResult:
        """Perform startup check.

        Startup checks if initialization has completed.
        Used to delay liveness/readiness checks during long initialization.

        Returns:
            Health check result
        """
        start_time = time.time()
        probe_type = ProbeType.STARTUP

        self._track_check_started(probe_type)

        try:
            # Perform readiness check as startup test
            readiness_result = await self.check_readiness()

            if readiness_result.status == HealthStatus.HEALTHY:
                self._startup_complete = True
                duration_ms = (time.time() - start_time) * 1000
                self._track_check_success(probe_type, duration_ms)

                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    probe_type=probe_type,
                    message="Startup complete",
                    duration_ms=duration_ms,
                )

            raise Exception("Startup checks not passing yet")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._track_check_failure(probe_type, duration_ms)

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                probe_type=probe_type,
                message=f"Startup check failed: {e}",
                duration_ms=duration_ms,
            )

    async def _liveness_loop(self) -> None:
        """Background task for periodic liveness checks."""
        while not self._should_stop:
            await asyncio.sleep(self._config.liveness_interval)

            result = await self.check_liveness()

            # Update state based on consecutive failures
            if result.status == HealthStatus.UNHEALTHY:
                failures = self._metrics.consecutive_failures.get(ProbeType.LIVENESS, 0)
                if failures >= self._config.liveness_failure_threshold:
                    self._is_alive = False
            else:
                self._is_alive = True

    async def _readiness_loop(self) -> None:
        """Background task for periodic readiness checks."""
        while not self._should_stop:
            await asyncio.sleep(self._config.readiness_interval)

            result = await self.check_readiness()

            # Update state based on consecutive failures
            if result.status == HealthStatus.UNHEALTHY:
                failures = self._metrics.consecutive_failures.get(ProbeType.READINESS, 0)
                if failures >= self._config.readiness_failure_threshold:
                    self._is_ready = False
            else:
                self._is_ready = True

    async def _startup_check(self) -> None:
        """Perform startup check once."""
        start_time = time.time()
        attempts = 0

        while not self._should_stop and not self._startup_complete:
            if time.time() - start_time > self._config.startup_timeout:
                break

            attempts += 1
            if attempts > self._config.startup_failure_threshold:
                break

            result = await self.check_startup()

            if result.status == HealthStatus.HEALTHY:
                break

            await asyncio.sleep(10)  # Wait 10s between startup checks

    def _track_check_started(self, probe_type: ProbeType) -> None:
        """Track that a health check started."""
        self._metrics.total_checks[probe_type] = self._metrics.total_checks.get(probe_type, 0) + 1

    def _track_check_success(self, probe_type: ProbeType, duration_ms: float) -> None:
        """Track successful health check."""
        self._metrics.successful_checks[probe_type] = (
            self._metrics.successful_checks.get(probe_type, 0) + 1
        )
        self._metrics.last_check_time[probe_type] = time.time()
        self._metrics.last_check_duration[probe_type] = duration_ms
        self._metrics.consecutive_failures[probe_type] = 0

    def _track_check_failure(self, probe_type: ProbeType, duration_ms: float) -> None:
        """Track failed health check."""
        self._metrics.failed_checks[probe_type] = self._metrics.failed_checks.get(probe_type, 0) + 1
        self._metrics.last_check_time[probe_type] = time.time()
        self._metrics.last_check_duration[probe_type] = duration_ms
        self._metrics.consecutive_failures[probe_type] = (
            self._metrics.consecutive_failures.get(probe_type, 0) + 1
        )

    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics text
        """
        lines = [
            "# HELP agenkit_health_checks_total Total number of health checks performed",
            "# TYPE agenkit_health_checks_total counter",
        ]

        for probe_type, count in self._metrics.total_checks.items():
            lines.append(f'agenkit_health_checks_total{{probe="{probe_type.value}"}} {count}')

        lines.extend(
            [
                "",
                "# HELP agenkit_health_check_failures_total Total number of failed health checks",
                "# TYPE agenkit_health_check_failures_total counter",
            ]
        )

        for probe_type, count in self._metrics.failed_checks.items():
            lines.append(
                f'agenkit_health_check_failures_total{{probe="{probe_type.value}"}} {count}'
            )

        lines.extend(
            [
                "",
                "# HELP agenkit_health_check_duration_ms Duration of last health check in milliseconds",
                "# TYPE agenkit_health_check_duration_ms gauge",
            ]
        )

        for probe_type, duration in self._metrics.last_check_duration.items():
            lines.append(
                f'agenkit_health_check_duration_ms{{probe="{probe_type.value}"}} {duration}'
            )

        lines.extend(
            [
                "",
                "# HELP agenkit_agent_uptime_seconds Uptime in seconds",
                "# TYPE agenkit_agent_uptime_seconds gauge",
                f"agenkit_agent_uptime_seconds {self._metrics.get_uptime()}",
                "",
                "# HELP agenkit_agent_healthy Agent health status (1=healthy, 0=unhealthy)",
                "# TYPE agenkit_agent_healthy gauge",
                f"agenkit_agent_healthy {1 if self.is_healthy else 0}",
            ]
        )

        return "\n".join(lines) + "\n"
