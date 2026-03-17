using Agenkit.Core;

namespace Agenkit.Budget;

/// <summary>
/// Wraps an agent and throws when the cost budget is exceeded.
/// </summary>
public class BudgetLimiter : IAgent
{
    private readonly IAgent _inner;
    private readonly CostTracker _tracker;
    private readonly decimal _budgetUsd;
    private readonly Func<Message, (long input, long output)> _tokenEstimator;

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Remaining budget in USD.</summary>
    public decimal RemainingBudget => _budgetUsd - _tracker.TotalCostUsd;

    /// <summary>Creates a BudgetLimiter.</summary>
    /// <param name="inner">Agent to wrap.</param>
    /// <param name="tracker">Cost tracker instance.</param>
    /// <param name="budgetUsd">Maximum allowed spend in USD.</param>
    /// <param name="tokenEstimator">Optional function to estimate token counts. Defaults to simple word count.</param>
    public BudgetLimiter(
        IAgent inner,
        CostTracker tracker,
        decimal budgetUsd,
        Func<Message, (long input, long output)>? tokenEstimator = null)
    {
        if (budgetUsd <= 0)
            throw new ArgumentOutOfRangeException(nameof(budgetUsd), "budget must be positive");
        _inner = inner;
        _tracker = tracker;
        _budgetUsd = budgetUsd;
        _tokenEstimator = tokenEstimator ?? DefaultEstimator;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        if (_tracker.TotalCostUsd >= _budgetUsd)
            throw new InvalidOperationException(
                $"budget of ${_budgetUsd:F4} USD has been exhausted (spent: ${_tracker.TotalCostUsd:F4})");

        var response = await _inner.ProcessAsync(message, ct).ConfigureAwait(false);
        var (input, output) = _tokenEstimator(message);
        _tracker.Record(input, output);
        return response;
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        _inner.Capabilities,
        State: new Dictionary<string, object>
        {
            ["budget_usd"] = _budgetUsd,
            ["spent_usd"] = _tracker.TotalCostUsd,
            ["remaining_usd"] = RemainingBudget
        });

    private static (long input, long output) DefaultEstimator(Message m)
    {
        // Rough estimate: 1 token ≈ 4 characters
        var inputTokens = Math.Max(1, m.ContentString().Length / 4);
        return (inputTokens, inputTokens / 2);
    }
}
