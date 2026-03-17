package io.agenkit.middleware;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;

class CachingMiddlewareTest {

    @Test
    void cachesMissOnFirstCall() throws Exception {
        AtomicInteger callCount = new AtomicInteger(0);
        MockAgent inner = new MockAgent("inner", msg -> {
            callCount.incrementAndGet();
            return "response";
        });
        CachingMiddleware cache = new CachingMiddleware(inner, 10, Duration.ofMinutes(1));

        cache.process(Message.of("user", "question")).get();
        assertThat(callCount.get()).isEqualTo(1);
    }

    @Test
    void returnsCachedOnSecondCall() throws Exception {
        AtomicInteger callCount = new AtomicInteger(0);
        MockAgent inner = new MockAgent("inner", msg -> {
            callCount.incrementAndGet();
            return "response";
        });
        CachingMiddleware cache = new CachingMiddleware(inner, 10, Duration.ofMinutes(1));

        cache.process(Message.of("user", "same question")).get();
        cache.process(Message.of("user", "same question")).get();

        assertThat(callCount.get()).isEqualTo(1);
    }

    @Test
    void differentQuestionsGetDifferentResponses() throws Exception {
        AtomicInteger callCount = new AtomicInteger(0);
        MockAgent inner = new MockAgent("inner", msg -> {
            callCount.incrementAndGet();
            return "response " + callCount.get();
        });
        CachingMiddleware cache = new CachingMiddleware(inner, 10, Duration.ofMinutes(1));

        cache.process(Message.of("user", "question 1")).get();
        cache.process(Message.of("user", "question 2")).get();

        assertThat(callCount.get()).isEqualTo(2);
    }
}
