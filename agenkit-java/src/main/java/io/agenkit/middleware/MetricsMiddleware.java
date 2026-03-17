package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Middleware that collects latency and error metrics.
 */
public final class MetricsMiddleware implements Agent {

    private static final Logger log = LoggerFactory.getLogger(MetricsMiddleware.class);

    private final Agent inner;
    private final AtomicLong requestCount = new AtomicLong(0);
    private final AtomicLong errorCount = new AtomicLong(0);
    private final AtomicLong totalLatencyMs = new AtomicLong(0);

    public MetricsMiddleware(Agent inner) {
        this.inner = inner;
    }

    @Override
    public String getName() { return inner.getName() + "[metrics]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        long start = System.currentTimeMillis();
        requestCount.incrementAndGet();

        return inner.process(message)
                .thenApply(response -> {
                    long latency = System.currentTimeMillis() - start;
                    totalLatencyMs.addAndGet(latency);
                    log.debug("agent={} latency={}ms", inner.getName(), latency);
                    return response.withMetadata("latency_ms", latency);
                })
                .exceptionallyCompose(ex -> {
                    errorCount.incrementAndGet();
                    long latency = System.currentTimeMillis() - start;
                    totalLatencyMs.addAndGet(latency);
                    log.warn("agent={} error={} latency={}ms", inner.getName(), ex.getMessage(), latency);
                    return CompletableFuture.failedFuture(ex);
                });
    }

    public long getRequestCount() { return requestCount.get(); }
    public long getErrorCount() { return errorCount.get(); }
    public double getAverageLatencyMs() {
        long count = requestCount.get();
        return count == 0 ? 0.0 : (double) totalLatencyMs.get() / count;
    }

    public Map<String, Object> getMetrics() {
        Map<String, Object> metrics = new HashMap<>();
        metrics.put("requests", requestCount.get());
        metrics.put("errors", errorCount.get());
        metrics.put("avg_latency_ms", getAverageLatencyMs());
        return metrics;
    }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> state = new HashMap<>(getMetrics());
        return new IntrospectionResult(getName(), getCapabilities(), null, state, null);
    }
}
