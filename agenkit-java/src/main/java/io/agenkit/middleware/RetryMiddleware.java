package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.Predicate;

/**
 * Middleware that retries failed agent calls with exponential backoff.
 */
public final class RetryMiddleware implements Agent {

    private static final Logger log = LoggerFactory.getLogger(RetryMiddleware.class);

    private final Agent inner;
    private final RetryConfig config;

    public RetryMiddleware(Agent inner, RetryConfig config) {
        this.inner = inner;
        this.config = config;
    }

    public RetryMiddleware(Agent inner, int maxAttempts) {
        this(inner, RetryConfig.builder().maxAttempts(maxAttempts).build());
    }

    @Override
    public String getName() { return inner.getName() + "[retry]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        return attempt(message, 1);
    }

    private CompletableFuture<Message> attempt(Message message, int attempt) {
        return inner.process(message).exceptionallyCompose(ex -> {
            if (attempt >= config.getMaxAttempts() || !config.getShouldRetry().test(ex)) {
                return CompletableFuture.failedFuture(ex);
            }
            long delayMs = (long) (config.getInitialDelayMs()
                    * Math.pow(config.getBackoffMultiplier(), attempt - 1));
            delayMs = Math.min(delayMs, config.getMaxDelayMs());
            log.debug("retrying after {}ms (attempt {}/{})", delayMs, attempt, config.getMaxAttempts());
            long finalDelayMs = delayMs;
            return CompletableFuture.supplyAsync(() -> null,
                    CompletableFuture.delayedExecutor(finalDelayMs,
                            java.util.concurrent.TimeUnit.MILLISECONDS))
                    .thenCompose(v -> attempt(message, attempt + 1));
        });
    }

    @Override
    public IntrospectionResult introspect() { return inner.introspect(); }

    public static final class RetryConfig {
        private final int maxAttempts;
        private final long initialDelayMs;
        private final double backoffMultiplier;
        private final long maxDelayMs;
        private final Predicate<Throwable> shouldRetry;

        private RetryConfig(Builder b) {
            this.maxAttempts = b.maxAttempts;
            this.initialDelayMs = b.initialDelayMs;
            this.backoffMultiplier = b.backoffMultiplier;
            this.maxDelayMs = b.maxDelayMs;
            this.shouldRetry = b.shouldRetry;
        }

        public int getMaxAttempts() { return maxAttempts; }
        public long getInitialDelayMs() { return initialDelayMs; }
        public double getBackoffMultiplier() { return backoffMultiplier; }
        public long getMaxDelayMs() { return maxDelayMs; }
        public Predicate<Throwable> getShouldRetry() { return shouldRetry; }

        public static Builder builder() { return new Builder(); }

        public static final class Builder {
            private int maxAttempts = 3;
            private long initialDelayMs = 100;
            private double backoffMultiplier = 2.0;
            private long maxDelayMs = 30_000;
            private Predicate<Throwable> shouldRetry = ex -> true;

            public Builder maxAttempts(int n) { this.maxAttempts = n; return this; }
            public Builder initialDelay(Duration d) { this.initialDelayMs = d.toMillis(); return this; }
            public Builder backoffMultiplier(double m) { this.backoffMultiplier = m; return this; }
            public Builder maxDelay(Duration d) { this.maxDelayMs = d.toMillis(); return this; }
            public Builder shouldRetry(Predicate<Throwable> p) { this.shouldRetry = p; return this; }
            public RetryConfig build() { return new RetryConfig(this); }
        }
    }
}
