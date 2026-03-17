package io.agenkit.middleware;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Middleware that caches agent responses by message content.
 */
public final class CachingMiddleware implements Agent {

    private final Agent inner;
    private final int maxSize;
    private final Duration ttl;
    private final Map<String, CacheEntry> cache = new ConcurrentHashMap<>();

    public CachingMiddleware(Agent inner, int maxSize, Duration ttl) {
        this.inner = inner;
        this.maxSize = maxSize;
        this.ttl = ttl;
    }

    public CachingMiddleware(Agent inner) {
        this(inner, 100, Duration.ofMinutes(5));
    }

    @Override
    public String getName() { return inner.getName() + "[cache]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        String key = message.contentString();
        CacheEntry entry = cache.get(key);
        if (entry != null && !entry.isExpired()) {
            return CompletableFuture.completedFuture(
                    entry.message().withMetadata("cache_hit", true));
        }

        return inner.process(message).thenApply(response -> {
            if (cache.size() >= maxSize) {
                // Evict oldest
                cache.entrySet().stream()
                        .min(Map.Entry.comparingByValue())
                        .ifPresent(e -> cache.remove(e.getKey()));
            }
            cache.put(key, new CacheEntry(response, Instant.now().plus(ttl)));
            return response;
        });
    }

    public int getCacheSize() { return cache.size(); }

    public void clearCache() { cache.clear(); }

    @Override
    public IntrospectionResult introspect() { return inner.introspect(); }

    private record CacheEntry(Message message, Instant expiresAt) implements Comparable<CacheEntry> {
        boolean isExpired() { return Instant.now().isAfter(expiresAt); }

        @Override
        public int compareTo(CacheEntry other) {
            return this.expiresAt.compareTo(other.expiresAt);
        }
    }
}
