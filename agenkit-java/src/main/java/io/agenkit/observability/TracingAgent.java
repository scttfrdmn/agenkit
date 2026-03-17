package io.agenkit.observability;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/**
 * Agent wrapper that adds distributed tracing spans.
 */
public final class TracingAgent implements Agent {

    private static final Logger log = LoggerFactory.getLogger(TracingAgent.class);

    private final Agent inner;
    private final List<Span> spans = new ArrayList<>();

    public TracingAgent(Agent inner) {
        this.inner = inner;
    }

    @Override
    public String getName() { return inner.getName() + "[tracing]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        String traceId = (String) message.getMetadata().getOrDefault(
                "trace_id", UUID.randomUUID().toString());
        String spanId = UUID.randomUUID().toString().substring(0, 8);
        Instant start = Instant.now();

        log.debug("trace={} span={} agent={} start", traceId, spanId, inner.getName());

        return inner.process(message.withMetadata("trace_id", traceId))
                .thenApply(response -> {
                    long durationMs = Instant.now().toEpochMilli() - start.toEpochMilli();
                    Span span = new Span(traceId, spanId, inner.getName(), start,
                            durationMs, null);
                    synchronized (spans) { spans.add(span); }
                    log.debug("trace={} span={} agent={} duration={}ms",
                            traceId, spanId, inner.getName(), durationMs);
                    return response
                            .withMetadata("trace_id", traceId)
                            .withMetadata("span_id", spanId)
                            .withMetadata("duration_ms", durationMs);
                })
                .exceptionallyCompose(ex -> {
                    long durationMs = Instant.now().toEpochMilli() - start.toEpochMilli();
                    Span span = new Span(traceId, spanId, inner.getName(), start,
                            durationMs, ex.getMessage());
                    synchronized (spans) { spans.add(span); }
                    log.warn("trace={} span={} agent={} error={}",
                            traceId, spanId, inner.getName(), ex.getMessage());
                    return CompletableFuture.failedFuture(ex);
                });
    }

    public synchronized List<Span> getSpans() { return List.copyOf(spans); }

    @Override
    public IntrospectionResult introspect() { return inner.introspect(); }

    public record Span(
            String traceId,
            String spanId,
            String agentName,
            Instant startTime,
            long durationMs,
            String error) {}
}
