using System.Text;
using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>A decomposed subtask for a specialist agent.</summary>
public record Subtask(string Type, Message Message, IReadOnlyDictionary<string, object>? Metadata = null);

/// <summary>
/// Planner agent responsible for task decomposition and result synthesis.
/// </summary>
public interface IPlannerAgent : IAgent
{
    /// <summary>Decomposes a message into subtasks for specialist agents.</summary>
    Task<IReadOnlyList<Subtask>> PlanAsync(Message message, CancellationToken ct = default);

    /// <summary>Combines specialist results into a final response.</summary>
    Task<Message> SynthesizeAsync(
        Message original,
        IReadOnlyDictionary<string, Message> results,
        CancellationToken ct = default);
}

/// <summary>
/// Hierarchical supervisor that decomposes tasks and delegates to specialists.
/// </summary>
public class SupervisorAgent : IAgent
{
    private readonly IPlannerAgent _planner;
    private readonly IReadOnlyDictionary<string, IAgent> _specialists;

    /// <inheritdoc />
    public string Name => "SupervisorAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities
    {
        get
        {
            var caps = new HashSet<string>(_planner.Capabilities) { "supervisor", "hierarchical", "coordination" };
            foreach (var s in _specialists.Values)
                foreach (var c in s.Capabilities)
                    caps.Add(c);
            return caps.ToList();
        }
    }

    /// <summary>Creates a new SupervisorAgent.</summary>
    public SupervisorAgent(IPlannerAgent planner, IReadOnlyDictionary<string, IAgent> specialists)
    {
        ArgumentNullException.ThrowIfNull(planner);
        if (specialists.Count == 0)
            throw new ArgumentException("at least one specialist is required", nameof(specialists));
        _planner = planner;
        _specialists = specialists;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var subtasks = await _planner.PlanAsync(message, ct).ConfigureAwait(false);

        if (subtasks.Count == 0)
            return await _planner.ProcessAsync(message, ct).ConfigureAwait(false);

        // Validate specialists
        foreach (var subtask in subtasks)
        {
            if (!_specialists.ContainsKey(subtask.Type))
            {
                var available = string.Join(", ", _specialists.Keys);
                throw new InvalidOperationException(
                    $"subtask references unknown specialist type '{subtask.Type}' (available: {available})");
            }
        }

        // Execute subtasks
        var results = new Dictionary<string, Message>();
        for (int i = 0; i < subtasks.Count; i++)
        {
            ct.ThrowIfCancellationRequested();
            var subtask = subtasks[i];
            var specialist = _specialists[subtask.Type];
            var result = await specialist.ProcessAsync(subtask.Message, ct).ConfigureAwait(false);
            results[$"{subtask.Type}_{i}"] = result;
        }

        var final = await _planner.SynthesizeAsync(message, results, ct).ConfigureAwait(false);

        return final
            .WithMetadata("supervisor_subtasks", subtasks.Count)
            .WithMetadata("supervisor_specialists", _specialists.Count);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object> { ["specialist_count"] = _specialists.Count });
}

/// <summary>
/// Simple planner that returns no subtasks (delegates to underlying agent) and concatenates results.
/// </summary>
public class SimplePlanner : IPlannerAgent
{
    private readonly IAgent _agent;

    /// <inheritdoc />
    public string Name => "SimplePlanner";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities =>
        _agent.Capabilities.Concat(new[] { "planning", "synthesis" }).ToList();

    /// <summary>Creates a SimplePlanner backed by the given agent.</summary>
    public SimplePlanner(IAgent agent) => _agent = agent;

    /// <inheritdoc />
    public Task<Message> ProcessAsync(Message message, CancellationToken ct = default) =>
        _agent.ProcessAsync(message, ct);

    /// <inheritdoc />
    public Task<IReadOnlyList<Subtask>> PlanAsync(Message message, CancellationToken ct = default) =>
        Task.FromResult<IReadOnlyList<Subtask>>(Array.Empty<Subtask>());

    /// <inheritdoc />
    public Task<Message> SynthesizeAsync(
        Message original,
        IReadOnlyDictionary<string, Message> results,
        CancellationToken ct = default)
    {
        var sb = new StringBuilder("Synthesis of specialist results:\n\n");
        foreach (var (key, result) in results)
            sb.Append($"Result from {key}:\n{result.ContentString()}\n\n");
        return Task.FromResult(Message.NewMessage("assistant", sb.ToString()));
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(Name, Capabilities);
}
