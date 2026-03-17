using Agenkit.Core;

namespace Agenkit.Composition;

/// <summary>
/// Routes to one of two agents based on a predicate applied to the incoming message.
/// </summary>
public class ConditionalAgent : IAgent
{
    private readonly Func<Message, bool> _condition;
    private readonly IAgent _whenTrue;
    private readonly IAgent _whenFalse;

    /// <inheritdoc />
    public string Name => "ConditionalAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "conditional", "branching" };

    /// <summary>Creates a new ConditionalAgent.</summary>
    public ConditionalAgent(Func<Message, bool> condition, IAgent whenTrue, IAgent whenFalse)
    {
        _condition = condition;
        _whenTrue = whenTrue;
        _whenFalse = whenFalse;
    }

    /// <inheritdoc />
    public Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var branch = _condition(message) ? _whenTrue : _whenFalse;
        return branch.ProcessAsync(message, ct);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["true_branch"] = _whenTrue.Name,
            ["false_branch"] = _whenFalse.Name
        });
}
