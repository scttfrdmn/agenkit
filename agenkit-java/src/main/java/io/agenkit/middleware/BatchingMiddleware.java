package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Middleware that coalesces requests within a time window and processes them together.
 */
public final class BatchingMiddleware implements Agent {

    private final Agent inner;
    private final int maxBatchSize;
    private final Duration windowDuration;
    private final List<PendingRequest> pending = new ArrayList<>();
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor(
            r -> {
                Thread t = new Thread(r, "batching-middleware");
                t.setDaemon(true);
                return t;
            });

    public BatchingMiddleware(Agent inner, int maxBatchSize, Duration windowDuration) {
        this.inner = inner;
        this.maxBatchSize = maxBatchSize;
        this.windowDuration = windowDuration;
        // Schedule periodic flush
        scheduler.scheduleAtFixedRate(
                this::flushBatch,
                windowDuration.toMillis(),
                windowDuration.toMillis(),
                TimeUnit.MILLISECONDS);
    }

    public BatchingMiddleware(Agent inner) {
        this(inner, 10, Duration.ofMillis(50));
    }

    @Override
    public String getName() { return inner.getName() + "[batching]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public synchronized CompletableFuture<Message> process(Message message) {
        CompletableFuture<Message> future = new CompletableFuture<>();
        pending.add(new PendingRequest(message, future));

        if (pending.size() >= maxBatchSize) {
            flushBatch();
        }

        return future;
    }

    private synchronized void flushBatch() {
        if (pending.isEmpty()) return;

        List<PendingRequest> batch = new ArrayList<>(pending);
        pending.clear();

        // Process each request in the batch
        for (PendingRequest req : batch) {
            inner.process(req.message())
                    .whenComplete((response, ex) -> {
                        if (ex != null) {
                            req.future().completeExceptionally(ex);
                        } else {
                            req.future().complete(response.withMetadata("batch_size", batch.size()));
                        }
                    });
        }
    }

    public void shutdown() {
        scheduler.shutdown();
    }

    @Override
    public IntrospectionResult introspect() { return inner.introspect(); }

    private record PendingRequest(Message message, CompletableFuture<Message> future) {}
}
