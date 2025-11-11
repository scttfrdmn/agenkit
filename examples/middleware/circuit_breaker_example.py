"""
Circuit Breaker Middleware Example

This example demonstrates WHY and HOW to use circuit breaker middleware for
preventing cascading failures in distributed systems.

WHY USE CIRCUIT BREAKER MIDDLEWARE?
-----------------------------------
- Prevent cascading failures: Stop calling a failing service before it causes system-wide collapse
- Fail fast: Return errors immediately instead of waiting for timeouts
- Allow recovery: Give failing services time to recover without constant traffic
- Resource protection: Prevent thread/connection pool exhaustion from hanging requests

WHEN TO USE:
- External service calls (databases, APIs, microservices)
- Operations with potential for prolonged outages
- Services that experience load-related failures
- Any dependency where failures could cascade to other systems

WHEN NOT TO USE:
- Single-point operations where retry is sufficient
- Services with guaranteed availability (e.g., localhost)
- Operations where every attempt must be made (critical writes)
- Systems where stale data is unacceptable

TRADE-OFFS:
- Temporary unavailability: Service might recover while circuit is open
- State management: Need to track failure counts and timings across requests
- Configuration tuning: Wrong thresholds can cause premature or delayed trips
- Cold start issues: First requests after recovery may be slower
"""

import asyncio
import time
from agenkit.interfaces import Agent, Message
from agenkit.middleware import (
    CircuitBreakerConfig,
    CircuitBreakerDecorator,
    CircuitBreakerError,
    CircuitState,
    RetryConfig,
    RetryDecorator,
)


# Simulate an external API that experiences outages
class UnstableExternalAPI(Agent):
    """Simulates an external API that goes down after several calls."""

    def __init__(self):
        self.call_count = 0
        self.is_down = False

    @property
    def name(self) -> str:
        return "external-api"

    @property
    def capabilities(self) -> list[str]:
        return ["weather_data"]

    async def process(self, message: Message) -> Message:
        self.call_count += 1

        # Simulate service going down after 3 calls
        if self.call_count > 3:
            self.is_down = True

        if self.is_down:
            # Simulate slow failing service (timeout scenario)
            await asyncio.sleep(0.2)
            raise Exception("ServiceError: API is experiencing an outage")

        return Message(
            role="agent",
            content=f"Weather data: 72°F, Sunny",
            metadata={"call_count": self.call_count}
        )

    def recover(self):
        """Simulate service recovery."""
        self.is_down = False
        self.call_count = 0


async def example_basic_circuit_breaker():
    """Example 1: Basic circuit breaker protecting against repeated failures."""
    print("\n=== Example 1: Basic Circuit Breaker ===")
    print("Use case: External API that experiences an outage\n")

    api = UnstableExternalAPI()

    # Wrap with circuit breaker
    protected_api = CircuitBreakerDecorator(
        api,
        CircuitBreakerConfig(
            failure_threshold=3,    # Open after 3 failures
            recovery_timeout=2.0,   # Try recovery after 2 seconds
            success_threshold=2,    # Need 2 successes to fully recover
            timeout=1.0             # 1 second request timeout
        )
    )

    message = Message(role="user", content="Get weather for San Francisco")

    # Make successful calls
    print("Making successful calls...")
    for i in range(3):
        try:
            response = await protected_api.process(message)
            print(f"✅ Call {i+1}: {response.content}")
        except Exception as e:
            print(f"❌ Call {i+1}: {e}")

    # Now the service goes down
    print("\n💥 Service goes down!")
    print("Making calls that will fail...")

    for i in range(5):
        try:
            response = await protected_api.process(message)
            print(f"✅ Call {i+4}: {response.content}")
        except CircuitBreakerError as e:
            print(f"⚡ Call {i+4}: Circuit breaker OPEN - {e}")
        except Exception as e:
            print(f"❌ Call {i+4}: Failed - {e}")

    print(f"\n📊 Circuit State: {protected_api.state.value.upper()}")
    print(f"   Total requests: {protected_api.metrics.total_requests}")
    print(f"   Failed: {protected_api.metrics.failed_requests}")
    print(f"   Rejected (fast-fail): {protected_api.metrics.rejected_requests}")


async def example_recovery_scenario():
    """Example 2: Recovery scenario showing half-open to closed transition."""
    print("\n=== Example 2: Recovery Scenario ===")
    print("Use case: Service recovers and circuit breaker detects it\n")

    api = UnstableExternalAPI()
    protected_api = CircuitBreakerDecorator(
        api,
        CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1.0,
            success_threshold=2,
            timeout=0.5
        )
    )

    message = Message(role="user", content="Get data")

    # Cause failures to open circuit
    print("Causing failures to open circuit...")
    api.is_down = True

    for i in range(3):
        try:
            await protected_api.process(message)
        except Exception as e:
            print(f"❌ Failure {i+1}: {type(e).__name__}")

    print(f"⚡ Circuit State: {protected_api.state.value.upper()}")

    # Wait for recovery timeout
    print(f"\n⏳ Waiting {protected_api._config.recovery_timeout}s for recovery timeout...")
    await asyncio.sleep(protected_api._config.recovery_timeout + 0.1)

    # Service recovers
    print("🔧 Service recovers!")
    api.recover()

    # Next call will transition to HALF_OPEN
    print("\nMaking test call (circuit will enter HALF_OPEN)...")
    try:
        response = await protected_api.process(message)
        print(f"✅ Success: {response.content}")
        print(f"   Circuit State: {protected_api.state.value.upper()}")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Second success will close the circuit
    print("\nMaking second test call (should close circuit)...")
    try:
        response = await protected_api.process(message)
        print(f"✅ Success: {response.content}")
        print(f"   Circuit State: {protected_api.state.value.upper()} 🎉")
    except Exception as e:
        print(f"❌ Failed: {e}")

    print("\n📊 State Transitions:")
    for transition, count in protected_api.metrics.state_changes.items():
        print(f"   {transition}: {count} time(s)")


async def example_circuit_breaker_with_retry():
    """Example 3: Combining circuit breaker with retry for production resilience."""
    print("\n=== Example 3: Circuit Breaker + Retry ===")
    print("Use case: Retry transient failures, but fail fast if service is down\n")

    class FlakeyDatabase(Agent):
        """Simulates a database with transient failures and occasional outages."""

        def __init__(self):
            self.call_count = 0
            self.failure_pattern = [False, True, False, True, True, True, True]  # T = fail

        @property
        def name(self) -> str:
            return "database"

        @property
        def capabilities(self) -> list[str]:
            return ["query"]

        async def process(self, message: Message) -> Message:
            idx = self.call_count % len(self.failure_pattern)
            self.call_count += 1

            if self.failure_pattern[idx]:
                raise Exception("DatabaseError: Connection pool exhausted")

            return Message(
                role="agent",
                content="Query result: [data]",
                metadata={"call": self.call_count}
            )

    db = FlakeyDatabase()

    # Layer 1: Retry for transient failures (inner)
    retry_db = RetryDecorator(
        db,
        RetryConfig(
            max_attempts=2,
            initial_backoff=0.1,
            backoff_multiplier=2.0
        )
    )

    # Layer 2: Circuit breaker for persistent failures (outer)
    protected_db = CircuitBreakerDecorator(
        retry_db,
        CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.5,
            success_threshold=1,
            timeout=2.0
        )
    )

    message = Message(role="user", content="SELECT * FROM users")

    print("Making calls with layered protection (retry + circuit breaker)...\n")

    for i in range(8):
        try:
            response = await protected_db.process(message)
            print(f"✅ Call {i+1}: Success - {response.content}")
        except CircuitBreakerError as e:
            print(f"⚡ Call {i+1}: Circuit OPEN - failing fast")
        except Exception as e:
            print(f"❌ Call {i+1}: Failed after retries - {type(e).__name__}")

        # Small delay between calls
        await asyncio.sleep(0.1)

    print(f"\n📊 Final State: {protected_db.state.value.upper()}")
    print(f"   This pattern prevents: retry storms on failing services!")


async def example_metrics_tracking():
    """Example 4: Tracking circuit breaker metrics for monitoring."""
    print("\n=== Example 4: Metrics Tracking ===")
    print("Use case: Monitor circuit breaker behavior for alerting and debugging\n")

    class OverloadedService(Agent):
        """Simulates a service that fails under load."""

        def __init__(self):
            self.request_count = 0

        @property
        def name(self) -> str:
            return "overloaded-service"

        @property
        def capabilities(self) -> list[str]:
            return ["process_job"]

        async def process(self, message: Message) -> Message:
            self.request_count += 1

            # Fail every other request to simulate overload
            if self.request_count % 2 == 0:
                raise Exception("ServiceOverload: Too many concurrent requests")

            return Message(role="agent", content="Job processed")

    service = OverloadedService()
    protected_service = CircuitBreakerDecorator(
        service,
        CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            success_threshold=2,
            timeout=1.0
        )
    )

    message = Message(role="user", content="Process job")

    print("Simulating load on overloaded service...\n")

    for i in range(10):
        try:
            await protected_service.process(message)
            print(f"✅ Request {i+1}: Success")
        except CircuitBreakerError:
            print(f"⚡ Request {i+1}: Rejected (circuit open)")
        except Exception:
            print(f"❌ Request {i+1}: Failed")

        await asyncio.sleep(0.05)

    # Display comprehensive metrics
    metrics = protected_service.metrics
    print("\n" + "="*50)
    print("📊 CIRCUIT BREAKER METRICS")
    print("="*50)
    print(f"Total Requests:       {metrics.total_requests}")
    print(f"Successful:           {metrics.successful_requests} ({metrics.successful_requests/metrics.total_requests*100:.1f}%)")
    print(f"Failed:               {metrics.failed_requests} ({metrics.failed_requests/metrics.total_requests*100:.1f}%)")
    print(f"Rejected (Fast-Fail): {metrics.rejected_requests} ({metrics.rejected_requests/metrics.total_requests*100:.1f}%)")
    print(f"\nCurrent State:        {metrics.current_state.value.upper()}")

    if metrics.last_state_change:
        elapsed = time.time() - metrics.last_state_change
        print(f"Time in State:        {elapsed:.2f}s")

    print(f"\nState Transition History:")
    for transition, count in metrics.state_changes.items():
        print(f"  {transition}: {count}")

    print("\n💡 Use these metrics for:")
    print("  - Alerting on circuit state changes")
    print("  - Tracking service health trends")
    print("  - Capacity planning and load testing")
    print("  - Debugging cascading failure scenarios")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("CIRCUIT BREAKER MIDDLEWARE EXAMPLES")
    print("="*60)
    print("\nThese examples show how circuit breakers prevent cascading")
    print("failures and protect your system from unhealthy dependencies.\n")

    await example_basic_circuit_breaker()
    await example_recovery_scenario()
    await example_circuit_breaker_with_retry()
    await example_metrics_tracking()

    print("\n" + "="*60)
    print("KEY TAKEAWAYS")
    print("="*60)
    print("""
1. Circuit breakers protect your system by failing fast when services are down
2. Three states: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)
3. Configure failure_threshold based on your tolerance for errors
4. Set recovery_timeout to give failing services time to recover
5. Combine with retry middleware: retry handles transient failures, circuit
   breaker handles persistent failures
6. Monitor state changes and rejection rates for early warning of issues
7. Adjust thresholds based on your service's failure patterns and SLOs
    """)


if __name__ == "__main__":
    asyncio.run(main())
