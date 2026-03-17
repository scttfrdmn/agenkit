using System.Collections.Concurrent;
using Agenkit.Core;

namespace Agenkit.Middleware;

/// <summary>Configuration for CachingMiddleware.</summary>
public record CachingConfig(
    TimeSpan? Ttl = null,
    Func<Message, string>? KeyFn = null,
    int MaxEntries = 1000);

/// <summary>
/// In-memory response cache with optional TTL.
/// </summary>
public class CachingMiddleware : IAgent
{
    private readonly IAgent _inner;
    private readonly CachingConfig _config;
    private readonly ConcurrentDictionary<string, (Message response, DateTimeOffset storedAt)> _cache = new();

    /// <summary>Number of cache entries currently stored.</summary>
    public int CacheSize => _cache.Count;

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Creates a new CachingMiddleware.</summary>
    public CachingMiddleware(IAgent inner, CachingConfig? config = null)
    {
        _inner = inner;
        _config = config ?? new CachingConfig();
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var key = _config.KeyFn?.Invoke(message) ?? message.ContentString();

        if (_cache.TryGetValue(key, out var entry))
        {
            var ttl = _config.Ttl ?? TimeSpan.MaxValue;
            if (DateTimeOffset.UtcNow - entry.storedAt < ttl)
                return entry.response.WithMetadata("cache_hit", true);

            _cache.TryRemove(key, out _);
        }

        var response = await _inner.ProcessAsync(message, ct).ConfigureAwait(false);

        // Evict oldest entry if at capacity
        if (_cache.Count >= _config.MaxEntries)
        {
            var oldest = _cache.OrderBy(kv => kv.Value.storedAt).FirstOrDefault();
            if (oldest.Key is not null)
                _cache.TryRemove(oldest.Key, out _);
        }

        _cache[key] = (response, DateTimeOffset.UtcNow);
        return response;
    }

    /// <summary>Invalidates the entire cache.</summary>
    public void InvalidateAll() => _cache.Clear();

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        _inner.Capabilities,
        State: new Dictionary<string, object> { ["cache_size"] = _cache.Count });
}
