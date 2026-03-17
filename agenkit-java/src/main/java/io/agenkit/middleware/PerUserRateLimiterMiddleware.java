package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Middleware that applies per-user rate limiting.
 * Reads user identity from message metadata key "user_id".
 */
public final class PerUserRateLimiterMiddleware implements Agent {

    private final Agent inner;
    private final int maxRequestsPerSecond;
    private final Map<String, UserBucket> buckets = new ConcurrentHashMap<>();

    public PerUserRateLimiterMiddleware(Agent inner, int maxRequestsPerSecond) {
        this.inner = inner;
        this.maxRequestsPerSecond = maxRequestsPerSecond;
    }

    @Override
    public String getName() { return inner.getName() + "[per-user-rate-limiter]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        String userId = (String) message.getMetadata().getOrDefault("user_id", "anonymous");
        UserBucket bucket = buckets.computeIfAbsent(userId,
                k -> new UserBucket(maxRequestsPerSecond));

        if (!bucket.tryConsume()) {
            return CompletableFuture.failedFuture(
                    new RuntimeException("rate limit exceeded for user: " + userId));
        }
        return inner.process(message);
    }

    @Override
    public IntrospectionResult introspect() { return inner.introspect(); }

    private static final class UserBucket {
        private final int maxTokens;
        private final AtomicLong tokens;
        private final AtomicLong lastRefill = new AtomicLong(System.currentTimeMillis());

        UserBucket(int maxTokens) {
            this.maxTokens = maxTokens;
            this.tokens = new AtomicLong(maxTokens);
        }

        boolean tryConsume() {
            refill();
            long available = tokens.get();
            if (available <= 0) return false;
            return tokens.compareAndSet(available, available - 1);
        }

        private void refill() {
            long now = System.currentTimeMillis();
            long last = lastRefill.get();
            if (now - last >= 1000 && lastRefill.compareAndSet(last, now)) {
                tokens.set(maxTokens);
            }
        }
    }
}
