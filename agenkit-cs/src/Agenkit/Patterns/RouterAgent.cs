using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>
/// Classifies an input message and routes it to one of the registered agents.
/// </summary>
public class RouterAgent : IAgent
{
    private readonly Func<Message, string> _classifier;
    private readonly IReadOnlyDictionary<string, IAgent> _routes;
    private readonly IAgent? _defaultAgent;

    /// <inheritdoc />
    public string Name => "RouterAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "routing", "classification" };

    /// <summary>Creates a new RouterAgent.</summary>
    /// <param name="classifier">Function that returns a route key for a given message.</param>
    /// <param name="routes">Map of route keys to agents.</param>
    /// <param name="defaultAgent">Agent to use when no route matches. Throws if null and no route found.</param>
    public RouterAgent(
        Func<Message, string> classifier,
        IReadOnlyDictionary<string, IAgent> routes,
        IAgent? defaultAgent = null)
    {
        ArgumentNullException.ThrowIfNull(classifier);
        if (routes.Count == 0)
            throw new ArgumentException("at least one route is required", nameof(routes));

        _classifier = classifier;
        _routes = routes;
        _defaultAgent = defaultAgent;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var key = _classifier(message);

        if (_routes.TryGetValue(key, out var agent))
            return await agent.ProcessAsync(message, ct).ConfigureAwait(false);

        if (_defaultAgent is not null)
            return await _defaultAgent.ProcessAsync(message, ct).ConfigureAwait(false);

        throw new InvalidOperationException(
            $"No route found for key '{key}'. Available routes: {string.Join(", ", _routes.Keys)}");
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["routes"] = _routes.Keys.ToList(),
            ["has_default"] = _defaultAgent is not null
        });
}
