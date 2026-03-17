using System.Collections.Concurrent;
using Agenkit.Core;

namespace Agenkit.Middleware;

/// <summary>
/// Collects latency and error counters for an agent.
/// </summary>
public class MetricsMiddleware : IAgent
{
    private readonly IAgent _inner;
    private long _totalRequests;
    private long _totalErrors;
    private long _totalLatencyMs;

    /// <summary>Total number of requests processed.</summary>
    public long TotalRequests => _totalRequests;

    /// <summary>Total number of failed requests.</summary>
    public long TotalErrors => _totalErrors;

    /// <summary>Average latency in milliseconds.</summary>
    public double AverageLatencyMs =>
        _totalRequests == 0 ? 0 : (double)_totalLatencyMs / _totalRequests;

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Creates a new MetricsMiddleware.</summary>
    public MetricsMiddleware(IAgent inner) => _inner = inner;

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var start = DateTimeOffset.UtcNow;
        Interlocked.Increment(ref _totalRequests);

        try
        {
            var result = await _inner.ProcessAsync(message, ct).ConfigureAwait(false);
            var latency = (long)(DateTimeOffset.UtcNow - start).TotalMilliseconds;
            Interlocked.Add(ref _totalLatencyMs, latency);
            return result;
        }
        catch
        {
            Interlocked.Increment(ref _totalErrors);
            throw;
        }
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        _inner.Capabilities,
        State: new Dictionary<string, object>
        {
            ["total_requests"] = _totalRequests,
            ["total_errors"] = _totalErrors,
            ["avg_latency_ms"] = AverageLatencyMs
        });

    /// <summary>Resets all counters.</summary>
    public void Reset()
    {
        Interlocked.Exchange(ref _totalRequests, 0);
        Interlocked.Exchange(ref _totalErrors, 0);
        Interlocked.Exchange(ref _totalLatencyMs, 0);
    }
}
