package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Circuit breaker middleware that prevents calls to a failing agent.
 */
public final class CircuitBreakerMiddleware implements Agent {

    private static final Logger log = LoggerFactory.getLogger(CircuitBreakerMiddleware.class);

    public enum State { CLOSED, OPEN, HALF_OPEN }

    private final Agent inner;
    private final CircuitBreakerConfig config;
    private final AtomicReference<State> state = new AtomicReference<>(State.CLOSED);
    private final AtomicInteger failureCount = new AtomicInteger(0);
    private volatile Instant openedAt;

    public CircuitBreakerMiddleware(Agent inner, CircuitBreakerConfig config) {
        this.inner = inner;
        this.config = config;
    }

    public CircuitBreakerMiddleware(Agent inner) {
        this(inner, CircuitBreakerConfig.defaults());
    }

    @Override
    public String getName() { return inner.getName() + "[circuit-breaker]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        State current = state.get();

        if (current == State.OPEN) {
            if (Instant.now().isAfter(openedAt.plus(config.getResetTimeout()))) {
                state.compareAndSet(State.OPEN, State.HALF_OPEN);
                log.debug("circuit half-open, trying probe");
            } else {
                return CompletableFuture.failedFuture(
                        new RuntimeException("circuit breaker open"));
            }
        }

        return inner.process(message)
                .thenApply(response -> {
                    failureCount.set(0);
                    state.compareAndSet(State.HALF_OPEN, State.CLOSED);
                    return response;
                })
                .exceptionallyCompose(ex -> {
                    int failures = failureCount.incrementAndGet();
                    if (failures >= config.getFailureThreshold()) {
                        state.set(State.OPEN);
                        openedAt = Instant.now();
                        log.warn("circuit opened after {} failures", failures);
                    }
                    return CompletableFuture.failedFuture(ex);
                });
    }

    public State getState() { return state.get(); }

    @Override
    public IntrospectionResult introspect() { return inner.introspect(); }

    public static final class CircuitBreakerConfig {
        private final int failureThreshold;
        private final Duration resetTimeout;

        public CircuitBreakerConfig(int failureThreshold, Duration resetTimeout) {
            this.failureThreshold = failureThreshold;
            this.resetTimeout = resetTimeout;
        }

        public static CircuitBreakerConfig defaults() {
            return new CircuitBreakerConfig(5, Duration.ofSeconds(60));
        }

        public int getFailureThreshold() { return failureThreshold; }
        public Duration getResetTimeout() { return resetTimeout; }
    }
}
