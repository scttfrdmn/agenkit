"""
Property-Based Tests

Uses Hypothesis to automatically generate test cases and validate correctness
properties that should hold across many inputs. These tests discover edge cases
that traditional unit tests might miss.

Properties tested:
- Cache middleware: LRU ordering, TTL expiration, size bounds, idempotency
- Circuit Breaker: State transitions, failure thresholds, recovery
- Retry middleware: Retry counts, backoff monotonicity
- Rate Limiter: Token bucket bounds, rate enforcement
- Message serialization: Round-trip consistency, type preservation
- Composition patterns: Sequential, parallel, fallback

Each property is tested with 100+ automatically generated test cases.
"""
