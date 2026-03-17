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
}
