package io.agenkit.properties;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import io.agenkit.middleware.CachingMiddleware;
import io.agenkit.middleware.RateLimiterMiddleware;
import io.agenkit.middleware.RetryMiddleware;
import net.jqwik.api.*;
import net.jqwik.api.constraints.IntRange;
import net.jqwik.api.constraints.StringLength;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;

class MiddlewarePropertyTest {

    // --- CachingMiddleware properties ---

    @Property
    void cachingMiddlewareNameContainsInnerAndCache(
            @ForAll @StringLength(min = 1, max = 20) String innerName) {
        MockAgent inner = new MockAgent(innerName, "response");
        CachingMiddleware cache = new CachingMiddleware(inner, 10, Duration.ofMinutes(1));
        assertThat(cache.getName()).contains(innerName).contains("cache");
    }

    @Property
    void cachingMiddlewareSecondCallDoesNotInvokeInner(
            @ForAll @StringLength(min = 1, max = 50) String query) throws Exception {
        AtomicInteger callCount = new AtomicInteger(0);
        MockAgent inner = new MockAgent("inner", msg -> {
            callCount.incrementAndGet();
            return "cached-result";
        });
        CachingMiddleware cache = new CachingMiddleware(inner, 100, Duration.ofMinutes(1));

        cache.process(Message.of("user", query)).get();
        cache.process(Message.of("user", query)).get();

        assertThat(callCount.get()).isEqualTo(1);
    }

    @Property
    void cachingMiddlewareCacheHitHasMetadata(
            @ForAll @StringLength(min = 1, max = 40) String query) throws Exception {
        MockAgent inner = new MockAgent("inner", "answer");
        CachingMiddleware cache = new CachingMiddleware(inner, 100, Duration.ofMinutes(1));

        cache.process(Message.of("user", query)).get();
        Message second = cache.process(Message.of("user", query)).get();

        assertThat(second.getMetadata()).containsEntry("cache_hit", true);
    }

    @Property
    void cachingMiddlewareDistinctInputsAreIndependent(
            @ForAll @StringLength(min = 1, max = 30) String q1,
            @ForAll @StringLength(min = 1, max = 30) String q2) throws Exception {
        Assume.that(!q1.equals(q2));

        AtomicInteger count = new AtomicInteger(0);
        MockAgent inner = new MockAgent("inner", msg -> {
            count.incrementAndGet();
            return "r-" + msg.contentString();
        });
        CachingMiddleware cache = new CachingMiddleware(inner, 100, Duration.ofMinutes(1));

        Message r1 = cache.process(Message.of("user", q1)).get();
        Message r2 = cache.process(Message.of("user", q2)).get();

        assertThat(count.get()).isEqualTo(2);
        assertThat(r1.contentString()).isNotEqualTo(r2.contentString());
    }

    // --- RateLimiterMiddleware properties ---

    @Property
    void rateLimiterNameContainsInnerAndRateLimiter(
            @ForAll @StringLength(min = 1, max = 20) String innerName) {
        MockAgent inner = new MockAgent(innerName, "ok");
        RateLimiterMiddleware rl = new RateLimiterMiddleware(inner, 10);
        assertThat(rl.getName()).contains(innerName).contains("rate");
    }

    @Property
    void rateLimiterCapabilitiesMatchInner(
            @ForAll @StringLength(min = 1, max = 20) String innerName) {
        MockAgent inner = new MockAgent(innerName, "ok");
        RateLimiterMiddleware rl = new RateLimiterMiddleware(inner, 5);
        assertThat(rl.getCapabilities()).containsAll(inner.getCapabilities());
    }

    @Property
    void rateLimiterAllowsSingleCallWithPositiveLimit(
            @ForAll @IntRange(min = 1, max = 100) int limit) throws Exception {
        MockAgent inner = new MockAgent("agent", "response");
        RateLimiterMiddleware rl = new RateLimiterMiddleware(inner, limit);
        Message response = rl.process(Message.of("user", "test")).get();
        assertThat(response.contentString()).isEqualTo("response");
    }

    // --- RetryMiddleware properties ---

    @Property
    void retryMiddlewareNameContainsInnerAndRetry(
            @ForAll @StringLength(min = 1, max = 20) String innerName) {
        MockAgent inner = new MockAgent(innerName, "ok");
        RetryMiddleware retry = new RetryMiddleware(inner, 3);
        assertThat(retry.getName()).contains(innerName).contains("retry");
    }

    @Property
    void retryMiddlewareSuccessOnFirstAttempt(
            @ForAll @StringLength(min = 1, max = 50) String content) throws Exception {
        MockAgent inner = new MockAgent("inner", "success");
        RetryMiddleware retry = new RetryMiddleware(inner, 3);
        Message response = retry.process(Message.of("user", content)).get();
        assertThat(response.contentString()).isEqualTo("success");
    }

    @Property
    void retryMiddlewareCapabilitiesMatchInner(
            @ForAll @StringLength(min = 1, max = 20) String name) {
        MockAgent inner = new MockAgent(name, "ok");
        RetryMiddleware retry = new RetryMiddleware(inner, 2);
        assertThat(retry.getCapabilities()).containsAll(inner.getCapabilities());
    }

    @Property
    void retryMiddlewareIntrospectNotNull(
            @ForAll @StringLength(min = 1, max = 20) String name) {
        MockAgent inner = new MockAgent(name, "ok");
        RetryMiddleware retry = new RetryMiddleware(inner, 3);
        assertThat(retry.introspect()).isNotNull();
        assertThat(retry.introspect().getAgentName()).isEqualTo(name);
    }
}
