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

    @Test
    void cacheHitReturnsIdenticalContent() throws Exception {
        MockAgent inner = new MockAgent("inner", "fixed answer");
        CachingMiddleware cache = new CachingMiddleware(inner, 10, Duration.ofMinutes(1));

        Message first = cache.process(Message.of("user", "query")).get();
        Message second = cache.process(Message.of("user", "query")).get();

        assertThat(second.contentString()).isEqualTo(first.contentString());
        assertThat(second.getMetadata()).containsEntry("cache_hit", true);
    }

    @Test
    void cacheMissCallsInnerAgent() throws Exception {
        AtomicInteger callCount = new AtomicInteger(0);
        MockAgent inner = new MockAgent("inner", msg -> {
            callCount.incrementAndGet();
            return "result";
        });
        CachingMiddleware cache = new CachingMiddleware(inner, 10, Duration.ofMinutes(1));

        cache.process(Message.of("user", "alpha")).get();
        cache.process(Message.of("user", "beta")).get();
        cache.process(Message.of("user", "gamma")).get();

        assertThat(callCount.get()).isEqualTo(3);
    }

    @Test
    void keyDifferentiationByContent() throws Exception {
        AtomicInteger callCount = new AtomicInteger(0);
        MockAgent inner = new MockAgent("inner", msg -> {
            callCount.incrementAndGet();
            return "answer-" + msg.contentString();
        });
        CachingMiddleware cache = new CachingMiddleware(inner, 10, Duration.ofMinutes(1));

        Message r1 = cache.process(Message.of("user", "foo")).get();
        Message r2 = cache.process(Message.of("user", "bar")).get();

        assertThat(r1.contentString()).isEqualTo("answer-foo");
        assertThat(r2.contentString()).isEqualTo("answer-bar");
        assertThat(callCount.get()).isEqualTo(2);
    }

    @Test
    void getNameIncludesCache() {
        MockAgent inner = new MockAgent("my-agent");
        CachingMiddleware cache = new CachingMiddleware(inner);
        assertThat(cache.getName()).contains("cache");
    }

    @Test
    void introspectCapabilitiesContainMock() {
        MockAgent inner = new MockAgent("agent-x");
        CachingMiddleware cache = new CachingMiddleware(inner);
        assertThat(cache.introspect().getCapabilities()).contains("mock");
    }
}
