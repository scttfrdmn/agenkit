package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Middleware that enforces a per-request timeout.
 */
public final class TimeoutMiddleware implements Agent {

    private final Agent inner;
    private final Duration timeout;

    public TimeoutMiddleware(Agent inner, Duration timeout) {
        this.inner = inner;
        this.timeout = timeout;
    }

    @Override
    public String getName() { return inner.getName() + "[timeout]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        return inner.process(message)
                .orTimeout(timeout.toMillis(), TimeUnit.MILLISECONDS)
                .exceptionallyCompose(ex -> {
                    if (ex instanceof TimeoutException) {
                        return CompletableFuture.failedFuture(
                                new TimeoutException("agent timed out after " + timeout));
                    }
                    return CompletableFuture.failedFuture(ex);
                });
    }

    @Override
    public IntrospectionResult introspect() { return inner.introspect(); }
}
