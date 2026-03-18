package io.agenkit.middleware;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class RateLimiterTest {

    @Test
    void allowsRequestsUnderLimit() throws Exception {
        MockAgent inner = new MockAgent("agent", "ok");
        RateLimiterMiddleware rl = new RateLimiterMiddleware(inner, 10);

        Message response = rl.process(Message.of("user", "hi")).get();
        assertThat(response.contentString()).isEqualTo("ok");
    }

    @Test
    void rejectsWhenLimitExceeded() {
        MockAgent inner = new MockAgent("agent", "ok");
        RateLimiterMiddleware rl = new RateLimiterMiddleware(inner, 1);

        // Consume the token
        try { rl.process(Message.of("user", "first")).get(); } catch (Exception ignored) {}

        // Second request should fail
        assertThatThrownBy(() -> rl.process(Message.of("user", "second")).get())
                .hasCauseInstanceOf(RuntimeException.class)
                .hasMessageContaining("rate limit");
    }

    @Test
    void getNameIncludesRateLimiter() {
        MockAgent inner = new MockAgent("my-agent");
        RateLimiterMiddleware rl = new RateLimiterMiddleware(inner, 5);
        assertThat(rl.getName()).contains("rate");
    }

    @Test
    void introspectReturnsCapabilities() {
        MockAgent inner = new MockAgent("agent-a");
        RateLimiterMiddleware rl = new RateLimiterMiddleware(inner, 5);
        assertThat(rl.introspect().getCapabilities()).isNotNull();
    }

    @Test
    void allowsBurstUpToLimit() throws Exception {
        MockAgent inner = new MockAgent("agent", "response");
        RateLimiterMiddleware rl = new RateLimiterMiddleware(inner, 3);

        // All three should succeed
        rl.process(Message.of("user", "req1")).get();
        rl.process(Message.of("user", "req2")).get();
        Message last = rl.process(Message.of("user", "req3")).get();
        assertThat(last.contentString()).isEqualTo("response");
    }

    @Test
    void multipleCallsWithinLimitWork() throws Exception {
        MockAgent inner = new MockAgent("agent", "result");
        RateLimiterMiddleware rl = new RateLimiterMiddleware(inner, 5);

        for (int i = 0; i < 5; i++) {
            Message response = rl.process(Message.of("user", "msg-" + i)).get();
            assertThat(response.contentString()).isEqualTo("result");
        }
    }
}
