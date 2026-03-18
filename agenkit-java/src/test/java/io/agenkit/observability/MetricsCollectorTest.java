package io.agenkit.observability;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class MetricsCollectorTest {

    @Test
    void incrementCounterStartsFromZero() {
        MetricsCollector collector = new MetricsCollector();
        assertThat(collector.getCount("my.metric")).isEqualTo(0L);
    }

    @Test
    void incrementIncreasesByOne() {
        MetricsCollector collector = new MetricsCollector();
        collector.increment("calls");
        assertThat(collector.getCount("calls")).isEqualTo(1L);
    }

    @Test
    void incrementByAmountAddsCorrectly() {
        MetricsCollector collector = new MetricsCollector();
        collector.increment("tokens", 100L);
        collector.increment("tokens", 50L);
        assertThat(collector.getCount("tokens")).isEqualTo(150L);
    }

    @Test
    void recordHistogramAndGetAverage() {
        MetricsCollector collector = new MetricsCollector();
        collector.record("latency_ms", 10.0);
        collector.record("latency_ms", 20.0);
        collector.record("latency_ms", 30.0);
        assertThat(collector.getAverage("latency_ms")).isEqualTo(20.0);
    }

    @Test
    void averageOfEmptyHistogramIsZero() {
        MetricsCollector collector = new MetricsCollector();
        assertThat(collector.getAverage("empty.hist")).isEqualTo(0.0);
    }

    @Test
    void getAllCountersReturnsAllTracked() {
        MetricsCollector collector = new MetricsCollector();
        collector.increment("a");
        collector.increment("b", 5L);
        assertThat(collector.getAllCounters()).containsKey("a").containsKey("b");
    }

    @Test
    void tracingAgentAddsTraceMetadata() throws Exception {
        MockAgent inner = new MockAgent("traced", "ok");
        TracingAgent tracing = new TracingAgent(inner);

        Message response = tracing.process(Message.of("user", "hi")).get();
        assertThat(response.getMetadata()).containsKey("trace_id");
        assertThat(response.getMetadata()).containsKey("span_id");
        assertThat(response.getMetadata()).containsKey("duration_ms");
    }

    @Test
    void tracingAgentRecordsSpan() throws Exception {
        MockAgent inner = new MockAgent("traced", "result");
        TracingAgent tracing = new TracingAgent(inner);

        tracing.process(Message.of("user", "test")).get();

        assertThat(tracing.getSpans()).hasSize(1);
        assertThat(tracing.getSpans().get(0).agentName()).isEqualTo("traced");
    }

    @Test
    void tracingAgentNameIncludesTracingSuffix() {
        MockAgent inner = new MockAgent("base");
        TracingAgent tracing = new TracingAgent(inner);
        assertThat(tracing.getName()).contains("tracing");
    }

    @Test
    void tracingAgentPropagatesExistingTraceId() throws Exception {
        MockAgent inner = new MockAgent("inner", "ok");
        TracingAgent tracing = new TracingAgent(inner);

        Message input = Message.of("user", "request").withMetadata("trace_id", "my-trace-123");
        Message response = tracing.process(input).get();

        assertThat(response.getMetadata().get("trace_id")).isEqualTo("my-trace-123");
    }
}
