package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeoutException;

import static org.assertj.core.api.Assertions.*;

class TimeoutMiddlewareTest {

    @Test
    void passesWhenWithinTimeout() throws Exception {
        MockAgent inner = new MockAgent("fast", "quick response");
        TimeoutMiddleware timeout = new TimeoutMiddleware(inner, Duration.ofSeconds(5));

        Message response = timeout.process(Message.of("user", "hello")).get();
        assertThat(response.contentString()).isEqualTo("quick response");
    }

    @Test
    void failsWhenTimeoutExceeded() {
        Agent slow = new Agent() {
            public String getName() { return "slow"; }
            public List<String> getCapabilities() { return List.of(); }
            public CompletableFuture<Message> process(Message m) {
                CompletableFuture<Message> future = new CompletableFuture<>();
                // Never completes
                return future;
            }
            public IntrospectionResult introspect() {
                return new IntrospectionResult("slow", List.of(), null, null, null);
            }
        };

        TimeoutMiddleware timeout = new TimeoutMiddleware(slow, Duration.ofMillis(100));

        assertThatThrownBy(() -> timeout.process(Message.of("user", "hi")).get())
                .hasCauseInstanceOf(TimeoutException.class);
    }

    @Test
    void nameIncludesTimeoutSuffix() {
        MockAgent inner = new MockAgent("agent");
        TimeoutMiddleware timeout = new TimeoutMiddleware(inner, Duration.ofSeconds(10));
        assertThat(timeout.getName()).contains("timeout");
    }

    @Test
    void introspectCapabilitiesContainsMock() {
        MockAgent inner = new MockAgent("cap-agent");
        TimeoutMiddleware timeout = new TimeoutMiddleware(inner, Duration.ofSeconds(5));
        assertThat(timeout.introspect().getCapabilities()).contains("mock");
    }

    @Test
    void getNameIncludesInnerName() {
        MockAgent inner = new MockAgent("inner-x", "ok");
        TimeoutMiddleware timeout = new TimeoutMiddleware(inner, Duration.ofSeconds(1));
        assertThat(timeout.getName()).contains("inner-x");
    }

    @Test
    void processWithinTimeoutReturnsContent() throws Exception {
        MockAgent inner = new MockAgent("fast-agent", "fast result");
        TimeoutMiddleware timeout = new TimeoutMiddleware(inner, Duration.ofSeconds(5));
        Message response = timeout.process(Message.of("user", "ping")).get();
        assertThat(response.contentString()).isEqualTo("fast result");
    }
}
