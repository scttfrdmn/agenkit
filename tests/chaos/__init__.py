"""
Chaos Engineering Tests

Tests system resilience under various failure conditions including:
- Network failures (timeouts, drops, intermittent connectivity)
- Service unavailability (crashes, overload, dependencies)
- Slow responses (delays, resource pressure)
- Partial failures (streaming, batching)

These tests validate that resilience middleware (Circuit Breaker, Retry,
Timeout, Rate Limiter) behaves correctly under chaos conditions.
"""
