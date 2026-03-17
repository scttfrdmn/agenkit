using System.Collections.Concurrent;
using Agenkit.Core;

namespace Agenkit.Middleware;

/// <summary>
/// Per-identity token-bucket rate limiter. The identity is extracted from each message via a key function.
/// </summary>
public class PerUserRateLimiterMiddleware : IAgent
{
    private readonly IAgent _inner;
    private readonly int _requestsPerSecond;
    private readonly int _burstSize;
    private readonly Func<Message, string> _keyFn;
    private readonly ConcurrentDictionary<string, (double tokens, DateTimeOffset lastRefill)> _buckets = new();
    private readonly object _bucketLock = new();

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Creates a new PerUserRateLimiterMiddleware.</summary>
    /// <param name="inner">Agent to wrap.</param>
    /// <param name="requestsPerSecond">Refill rate per identity.</param>
    /// <param name="burstSize">Maximum burst size per identity (defaults to requestsPerSecond).</param>
    /// <param name="keyFn">Function that extracts an identity key from a message (default: checks metadata["user_id"]).</param>
    public PerUserRateLimiterMiddleware(
        IAgent inner,
        int requestsPerSecond,
        int burstSize = 0,
        Func<Message, string>? keyFn = null)
    {
        if (requestsPerSecond <= 0)
            throw new ArgumentOutOfRangeException(nameof(requestsPerSecond), "must be positive");
        _inner = inner;
        _requestsPerSecond = requestsPerSecond;
        _burstSize = burstSize > 0 ? burstSize : requestsPerSecond;
        _keyFn = keyFn ?? DefaultKeyFn;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var key = _keyFn(message);

        lock (_bucketLock)
        {
            var now = DateTimeOffset.UtcNow;
            var (tokens, lastRefill) = _buckets.GetOrAdd(key, _ => ((double)_burstSize, now));
            var elapsed = (now - lastRefill).TotalSeconds;
            tokens = Math.Min(_burstSize, tokens + elapsed * _requestsPerSecond);

            if (tokens < 1.0)
            {
                _buckets[key] = (tokens, now);
                throw new InvalidOperationException(
                    $"rate limit exceeded for identity '{key}' ({_requestsPerSecond} req/s)");
            }

            _buckets[key] = (tokens - 1.0, now);
        }

        return await _inner.ProcessAsync(message, ct).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => _inner.Introspect();

    private static string DefaultKeyFn(Message m)
    {
        if (m.Metadata is not null && m.Metadata.TryGetValue("user_id", out var userId))
            return userId?.ToString() ?? "anonymous";
        return "anonymous";
    }
}
