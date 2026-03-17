using Agenkit.Core;

namespace Agenkit.Middleware;

/// <summary>Configuration for RateLimiterMiddleware.</summary>
public record RateLimiterConfig(
    int RequestsPerSecond,
    int BurstSize = 0);

/// <summary>
/// Token-bucket rate limiter. Throws when the bucket is empty.
/// </summary>
public class RateLimiterMiddleware : IAgent
{
    private readonly IAgent _inner;
    private readonly int _requestsPerSecond;
    private readonly int _burstSize;
    private double _tokens;
    private DateTimeOffset _lastRefill;
    private readonly SemaphoreSlim _lock = new(1, 1);

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Creates a new RateLimiterMiddleware.</summary>
    public RateLimiterMiddleware(IAgent inner, RateLimiterConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        if (config.RequestsPerSecond <= 0)
            throw new ArgumentOutOfRangeException(nameof(config), "requests per second must be positive");
        _inner = inner;
        _requestsPerSecond = config.RequestsPerSecond;
        _burstSize = config.BurstSize > 0 ? config.BurstSize : config.RequestsPerSecond;
        _tokens = _burstSize;
        _lastRefill = DateTimeOffset.UtcNow;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        await _lock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            Refill();
            if (_tokens < 1.0)
                throw new InvalidOperationException(
                    $"rate limit exceeded for agent '{_inner.Name}' ({_requestsPerSecond} req/s)");
            _tokens -= 1.0;
        }
        finally
        {
            _lock.Release();
        }

        return await _inner.ProcessAsync(message, ct).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => _inner.Introspect();

    private void Refill()
    {
        var now = DateTimeOffset.UtcNow;
        var elapsed = (now - _lastRefill).TotalSeconds;
        _tokens = Math.Min(_burstSize, _tokens + elapsed * _requestsPerSecond);
        _lastRefill = now;
    }
}
