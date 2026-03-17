namespace Agenkit.Budget;

/// <summary>
/// Tracks cumulative token usage and cost across requests.
/// </summary>
public class CostTracker
{
    private long _totalInputTokens;
    private long _totalOutputTokens;
    private decimal _totalCostUsd;
    private readonly string _model;

    /// <summary>Total input tokens consumed.</summary>
    public long TotalInputTokens => _totalInputTokens;

    /// <summary>Total output tokens consumed.</summary>
    public long TotalOutputTokens => _totalOutputTokens;

    /// <summary>Total estimated cost in USD.</summary>
    public decimal TotalCostUsd => _totalCostUsd;

    /// <summary>Creates a CostTracker for the given model.</summary>
    public CostTracker(string model) => _model = model;

    /// <summary>Records token usage for a single request.</summary>
    public void Record(long inputTokens, long outputTokens)
    {
        Interlocked.Add(ref _totalInputTokens, inputTokens);
        Interlocked.Add(ref _totalOutputTokens, outputTokens);
        var cost = ModelPricing.CalculateCost(_model, inputTokens, outputTokens);
        lock (this) _totalCostUsd += cost;
    }

    /// <summary>Resets all counters.</summary>
    public void Reset()
    {
        Interlocked.Exchange(ref _totalInputTokens, 0);
        Interlocked.Exchange(ref _totalOutputTokens, 0);
        lock (this) _totalCostUsd = 0m;
    }
}
