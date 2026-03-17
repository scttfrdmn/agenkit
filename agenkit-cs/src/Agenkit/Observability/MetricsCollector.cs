using System.Collections.Concurrent;
using Agenkit.Core;

namespace Agenkit.Observability;

/// <summary>
/// Collects latency histograms and error counters across multiple agents.
/// </summary>
public class MetricsCollector
{
    private readonly ConcurrentDictionary<string, AgentMetrics> _metrics = new();

    /// <summary>Records a successful request.</summary>
    public void RecordSuccess(string agentName, TimeSpan latency)
    {
        var m = _metrics.GetOrAdd(agentName, _ => new AgentMetrics());
        m.RecordSuccess(latency);
    }

    /// <summary>Records a failed request.</summary>
    public void RecordError(string agentName)
    {
        var m = _metrics.GetOrAdd(agentName, _ => new AgentMetrics());
        m.RecordError();
    }

    /// <summary>Returns metrics for the given agent.</summary>
    public AgentMetrics? GetMetrics(string agentName) =>
        _metrics.TryGetValue(agentName, out var m) ? m : null;

    /// <summary>Returns metrics for all agents.</summary>
    public IReadOnlyDictionary<string, AgentMetrics> GetAllMetrics() =>
        new Dictionary<string, AgentMetrics>(_metrics);

    /// <summary>Resets all metrics.</summary>
    public void Reset() => _metrics.Clear();
}

/// <summary>Metrics for a single agent.</summary>
public class AgentMetrics
{
    private long _totalRequests;
    private long _totalErrors;
    private long _totalLatencyMs;

    /// <summary>Total successful requests.</summary>
    public long TotalRequests => _totalRequests;

    /// <summary>Total failed requests.</summary>
    public long TotalErrors => _totalErrors;

    /// <summary>Average latency in milliseconds.</summary>
    public double AverageLatencyMs =>
        _totalRequests == 0 ? 0 : (double)_totalLatencyMs / _totalRequests;

    internal void RecordSuccess(TimeSpan latency)
    {
        Interlocked.Increment(ref _totalRequests);
        Interlocked.Add(ref _totalLatencyMs, (long)latency.TotalMilliseconds);
    }

    internal void RecordError() => Interlocked.Increment(ref _totalErrors);
}
