package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;

class RetryMiddlewareTest {

    @Test
    void returnsSuccessOnFirstAttempt() throws Exception {
        MockAgent inner = new MockAgent("test", "success");
        RetryMiddleware retry = new RetryMiddleware(inner, 3);

        Message response = retry.process(Message.of("user", "hi")).get();
        assertThat(response.contentString()).isEqualTo("success");
    }

    @Test
    void retriesOnFailure() throws Exception {
        AtomicInteger attempt = new AtomicInteger(0);
        Agent flaky = new Agent() {
            public String getName() { return "flaky"; }
            public List<String> getCapabilities() { return List.of(); }
            public CompletableFuture<Message> process(Message m) {
                if (attempt.incrementAndGet() < 3) {
                    return CompletableFuture.failedFuture(new RuntimeException("transient"));
                }
                return CompletableFuture.completedFuture(Message.of("assistant", "ok"));
            }
            public IntrospectionResult introspect() {
                return new IntrospectionResult("flaky", List.of(), null, null, null);
            }
        };

        RetryMiddleware retry = new RetryMiddleware(flaky,
                RetryMiddleware.RetryConfig.builder()
                        .maxAttempts(5)
                        .initialDelay(Duration.ofMillis(1))
                        .build());

        Message response = retry.process(Message.of("user", "hi")).get();
        assertThat(response.contentString()).isEqualTo("ok");
        assertThat(attempt.get()).isEqualTo(3);
    }

    @Test
    void failsAfterMaxAttempts() {
        Agent alwaysFail = new Agent() {
            public String getName() { return "failing"; }
            public List<String> getCapabilities() { return List.of(); }
            public CompletableFuture<Message> process(Message m) {
                return CompletableFuture.failedFuture(new RuntimeException("always fail"));
            }
            public IntrospectionResult introspect() {
                return new IntrospectionResult("failing", List.of(), null, null, null);
            }
        };

        RetryMiddleware retry = new RetryMiddleware(alwaysFail,
                RetryMiddleware.RetryConfig.builder()
                        .maxAttempts(2)
                        .initialDelay(Duration.ofMillis(1))
                        .build());

        assertThatThrownBy(() -> retry.process(Message.of("user", "hi")).get())
                .hasCauseInstanceOf(RuntimeException.class);
    }

    @Test
    void getNameIncludesInnerName() {
        MockAgent inner = new MockAgent("my-inner", "ok");
        RetryMiddleware retry = new RetryMiddleware(inner, 3);
        assertThat(retry.getName()).contains("my-inner").contains("retry");
    }

    @Test
    void introspectReturnsRetryCapability() {
        MockAgent inner = new MockAgent("cap-agent");
        RetryMiddleware retry = new RetryMiddleware(inner, 3);
        assertThat(retry.introspect().getCapabilities()).isNotNull();
    }

    @Test
    void zeroRetriesFailsImmediately() {
        Agent alwaysFail = new Agent() {
            public String getName() { return "fail"; }
            public List<String> getCapabilities() { return List.of(); }
            public CompletableFuture<Message> process(Message m) {
                return CompletableFuture.failedFuture(new RuntimeException("immediate fail"));
            }
            public IntrospectionResult introspect() {
                return new IntrospectionResult("fail", List.of(), null, null, null);
            }
        };

        RetryMiddleware retry = new RetryMiddleware(alwaysFail,
                RetryMiddleware.RetryConfig.builder()
                        .maxAttempts(1)
                        .initialDelay(Duration.ofMillis(1))
                        .build());

        assertThatThrownBy(() -> retry.process(Message.of("user", "hi")).get())
                .hasCauseInstanceOf(RuntimeException.class)
                .hasMessageContaining("immediate fail");
    }
}
