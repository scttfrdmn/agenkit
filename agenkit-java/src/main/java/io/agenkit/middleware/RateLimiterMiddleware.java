package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Middleware that limits agent calls using a token bucket.
 */
public final class RateLimiterMiddleware implements Agent {

    private final Agent inner;
    private final int maxRequestsPerSecond;
    private final Semaphore semaphore;
    private final AtomicLong lastRefill = new AtomicLong(System.currentTimeMillis());
    private final AtomicLong tokens;

    public RateLimiterMiddleware(Agent inner, int maxRequestsPerSecond) {
        this.inner = inner;
        this.maxRequestsPerSecond = maxRequestsPerSecond;
        this.semaphore = new Semaphore(maxRequestsPerSecond, true);
        this.tokens = new AtomicLong(maxRequestsPerSecond);
    }

    @Override
    public String getName() { return inner.getName() + "[rate-limiter]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        refillTokens();
        long available = tokens.get();
        if (available <= 0) {
            return CompletableFuture.failedFuture(
                    new RuntimeException("rate limit exceeded: " + maxRequestsPerSecond + " req/s"));
        }
        tokens.decrementAndGet();
        return inner.process(message);
    }

    private void refillTokens() {
        long now = System.currentTimeMillis();
        long last = lastRefill.get();
        long elapsed = now - last;
        if (elapsed >= 1000 && lastRefill.compareAndSet(last, now)) {
            tokens.set(maxRequestsPerSecond);
        }
    }

    @Override
    public IntrospectionResult introspect() { return inner.introspect(); }
}
