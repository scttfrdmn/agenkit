package io.agenkit.middleware;

import io.agenkit.core.Agent;

import java.time.Duration;

/**
 * Fluent builder for composing agents with middleware.
 *
 * <pre>{@code
 * Agent agent = AgentBuilder.wrap(new MyAgent())
 *     .withRetry(3)
 *     .withTimeout(Duration.ofSeconds(30))
 *     .withCircuitBreaker()
 *     .withMetrics()
 *     .build();
 * }</pre>
 */
public final class AgentBuilder {

    private Agent current;

    private AgentBuilder(Agent agent) {
        this.current = agent;
    }

    public static AgentBuilder wrap(Agent agent) {
        return new AgentBuilder(agent);
    }

    public AgentBuilder withRetry(int maxAttempts) {
        current = new RetryMiddleware(current, maxAttempts);
        return this;
    }

    public AgentBuilder withRetry(RetryMiddleware.RetryConfig config) {
        current = new RetryMiddleware(current, config);
        return this;
    }

    public AgentBuilder withTimeout(Duration timeout) {
        current = new TimeoutMiddleware(current, timeout);
        return this;
    }

    public AgentBuilder withCircuitBreaker() {
        current = new CircuitBreakerMiddleware(current);
        return this;
    }

    public AgentBuilder withCircuitBreaker(CircuitBreakerMiddleware.CircuitBreakerConfig config) {
        current = new CircuitBreakerMiddleware(current, config);
        return this;
    }

    public AgentBuilder withCaching() {
        current = new CachingMiddleware(current);
        return this;
    }

    public AgentBuilder withCaching(int maxSize, Duration ttl) {
        current = new CachingMiddleware(current, maxSize, ttl);
        return this;
    }

    public AgentBuilder withRateLimit(int requestsPerSecond) {
        current = new RateLimiterMiddleware(current, requestsPerSecond);
        return this;
    }

    public AgentBuilder withPerUserRateLimit(int requestsPerSecond) {
        current = new PerUserRateLimiterMiddleware(current, requestsPerSecond);
        return this;
    }

    public AgentBuilder withMetrics() {
        current = new MetricsMiddleware(current);
        return this;
    }

    public AgentBuilder withBatching(int maxBatchSize, Duration window) {
        current = new BatchingMiddleware(current, maxBatchSize, window);
        return this;
    }

    public Agent build() {
        return current;
    }
}
