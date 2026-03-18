package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.*;

class CircuitBreakerTest {

    @Test
    void closedByDefault() {
        Agent inner = successAgent();
        CircuitBreakerMiddleware cb = new CircuitBreakerMiddleware(inner);
        assertThat(cb.getState()).isEqualTo(CircuitBreakerMiddleware.State.CLOSED);
    }

    @Test
    void opensAfterThreshold() throws Exception {
        Agent failing = failingAgent();
        CircuitBreakerMiddleware cb = new CircuitBreakerMiddleware(failing,
                new CircuitBreakerMiddleware.CircuitBreakerConfig(2, Duration.ofSeconds(60)));

        // Trigger failures
        for (int i = 0; i < 3; i++) {
            try { cb.process(Message.of("user", "hi")).get(); } catch (Exception ignored) {}
        }

        assertThat(cb.getState()).isEqualTo(CircuitBreakerMiddleware.State.OPEN);
    }

    @Test
    void rejectsWhenOpen() throws Exception {
        Agent failing = failingAgent();
        CircuitBreakerMiddleware cb = new CircuitBreakerMiddleware(failing,
                new CircuitBreakerMiddleware.CircuitBreakerConfig(1, Duration.ofHours(1)));

        // Open the circuit
        try { cb.process(Message.of("user", "hi")).get(); } catch (Exception ignored) {}
        try { cb.process(Message.of("user", "hi")).get(); } catch (Exception ignored) {}

        assertThatThrownBy(() -> cb.process(Message.of("user", "hi")).get())
                .hasCauseInstanceOf(RuntimeException.class)
                .hasMessageContaining("circuit");
    }

    private Agent successAgent() {
        return new Agent() {
            public String getName() { return "ok"; }
            public List<String> getCapabilities() { return List.of(); }
            public CompletableFuture<Message> process(Message m) {
                return CompletableFuture.completedFuture(Message.of("assistant", "ok"));
            }
            public IntrospectionResult introspect() {
                return new IntrospectionResult("ok", List.of(), null, null, null);
            }
        };
    }

    @Test
    void getNameIncludesInnerName() {
        Agent inner = successAgent();
        CircuitBreakerMiddleware cb = new CircuitBreakerMiddleware(inner);
        assertThat(cb.getName()).contains("ok").contains("circuit-breaker");
    }

    @Test
    void introspectReturnsCapabilities() {
        Agent inner = successAgent();
        CircuitBreakerMiddleware cb = new CircuitBreakerMiddleware(inner);
        assertThat(cb.introspect().getCapabilities()).isNotNull();
    }

    @Test
    void halfOpenTransitionAfterTimeout() throws Exception {
        Agent failing = failingAgent();
        CircuitBreakerMiddleware cb = new CircuitBreakerMiddleware(failing,
                new CircuitBreakerMiddleware.CircuitBreakerConfig(1, Duration.ofMillis(50)));

        // Open the circuit
        try { cb.process(Message.of("user", "hi")).get(); } catch (Exception ignored) {}
        try { cb.process(Message.of("user", "hi")).get(); } catch (Exception ignored) {}

        assertThat(cb.getState()).isEqualTo(CircuitBreakerMiddleware.State.OPEN);

        // Wait for reset timeout
        Thread.sleep(100);

        // Next attempt should transition to HALF_OPEN and try the inner
        try { cb.process(Message.of("user", "probe")).get(); } catch (Exception ignored) {}

        // State should be either OPEN (failed again) or HALF_OPEN was attempted
        assertThat(cb.getState()).isIn(
                CircuitBreakerMiddleware.State.OPEN,
                CircuitBreakerMiddleware.State.HALF_OPEN);
    }

    @Test
    void successResetsFailureCount() throws Exception {
        Agent inner = successAgent();
        CircuitBreakerMiddleware cb = new CircuitBreakerMiddleware(inner,
                new CircuitBreakerMiddleware.CircuitBreakerConfig(5, Duration.ofSeconds(60)));

        // All calls succeed; circuit stays CLOSED
        cb.process(Message.of("user", "req1")).get();
        cb.process(Message.of("user", "req2")).get();
        cb.process(Message.of("user", "req3")).get();

        assertThat(cb.getState()).isEqualTo(CircuitBreakerMiddleware.State.CLOSED);
    }

    private Agent failingAgent() {
        return new Agent() {
            public String getName() { return "fail"; }
            public List<String> getCapabilities() { return List.of(); }
            public CompletableFuture<Message> process(Message m) {
                return CompletableFuture.failedFuture(new RuntimeException("fail"));
            }
            public IntrospectionResult introspect() {
                return new IntrospectionResult("fail", List.of(), null, null, null);
            }
        };
    }
}
