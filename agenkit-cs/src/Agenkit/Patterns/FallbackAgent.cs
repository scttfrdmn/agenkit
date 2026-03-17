using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Configuration for FallbackAgent.</summary>
public record FallbackAgentConfig(IReadOnlyList<IAgent> Chain);

/// <summary>
/// Tries each agent in a chain in order, returning the first successful response.
/// </summary>
public class FallbackAgent : IAgent
{
    private readonly IReadOnlyList<IAgent> _chain;

    /// <inheritdoc />
    public string Name => "FallbackAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "fallback", "resilience" };

    /// <summary>Creates a new FallbackAgent.</summary>
    public FallbackAgent(FallbackAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        if (config.Chain.Count == 0)
            throw new ArgumentException("at least one agent is required in the chain", nameof(config));
        _chain = config.Chain;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var errors = new List<string>();

        foreach (var agent in _chain)
        {
            ct.ThrowIfCancellationRequested();
            try
            {
                return await agent.ProcessAsync(message, ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception ex)
            {
                errors.Add($"{agent.Name}: {ex.Message}");
            }
        }

        throw new AggregateException(
            $"all agents in fallback chain failed: {string.Join("; ", errors)}",
            errors.Select(e => new Exception(e)));
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object> { ["chain_length"] = _chain.Count });
}
