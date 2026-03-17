namespace Agenkit.Budget;

/// <summary>
/// Cost per 1,000 tokens for known models.
/// </summary>
public static class ModelPricing
{
    /// <summary>Pricing table: model name -> (input $/1k tokens, output $/1k tokens).</summary>
    private static readonly Dictionary<string, (decimal input, decimal output)> Table = new(StringComparer.OrdinalIgnoreCase)
    {
        ["gpt-4o"] = (0.005m, 0.015m),
        ["gpt-4o-mini"] = (0.00015m, 0.0006m),
        ["gpt-4-turbo"] = (0.01m, 0.03m),
        ["gpt-3.5-turbo"] = (0.0005m, 0.0015m),
        ["claude-3-5-sonnet-20241022"] = (0.003m, 0.015m),
        ["claude-3-5-haiku-20241022"] = (0.001m, 0.005m),
        ["claude-3-opus-20240229"] = (0.015m, 0.075m),
    };

    /// <summary>
    /// Returns the cost in USD for the given number of tokens.
    /// Returns 0 if the model is unknown.
    /// </summary>
    public static decimal CalculateCost(string model, long inputTokens, long outputTokens)
    {
        if (!Table.TryGetValue(model, out var pricing)) return 0m;
        return pricing.input * inputTokens / 1000m + pricing.output * outputTokens / 1000m;
    }

    /// <summary>Returns all known model names.</summary>
    public static IReadOnlyList<string> KnownModels => Table.Keys.ToList();
}
