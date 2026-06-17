using Agenkit.Core;

namespace Agenkit.Skills;

/// <summary>
/// Agent wrapper that automatically injects relevant skill instructions.
///
/// Before delegating to the wrapped agent, this wrapper queries the registry
/// for skills relevant to the incoming message and prepends their instructions
/// inside an <c>&lt;available_skills&gt;</c> block. The augmented message's
/// metadata contains <c>active_skills</c> listing the injected skill names.
/// </summary>
public sealed class SkillEnabledAgent : IAgent
{
    private readonly IAgent _agent;
    private readonly SkillRegistry _registry;
    private readonly int _maxActiveSkills;

    /// <summary>Creates a skill-enabled agent wrapping <paramref name="agent"/>.</summary>
    /// <param name="agent">Base agent to delegate processing to.</param>
    /// <param name="registry">Registry used to look up relevant skills.</param>
    /// <param name="maxActiveSkills">Maximum number of skills to inject (default 3).</param>
    /// <param name="autoDiscover">Whether to call <see cref="SkillRegistry.DiscoverSkills"/> at construction (default true).</param>
    public SkillEnabledAgent(
        IAgent agent,
        SkillRegistry registry,
        int maxActiveSkills = 3,
        bool autoDiscover = true)
    {
        _agent = agent;
        _registry = registry;
        _maxActiveSkills = maxActiveSkills;
        if (autoDiscover)
            _registry.DiscoverSkills();
    }

    /// <inheritdoc />
    public string Name => _agent.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities
    {
        get
        {
            var caps = new List<string>(_agent.Capabilities);
            if (!caps.Contains("skill_injection"))
                caps.Add("skill_injection");
            return caps;
        }
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => _agent.Introspect();

    /// <inheritdoc />
    public Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var query = message.ContentString();
        var relevant = _registry.FindRelevantSkills(query, _maxActiveSkills);

        if (relevant.Count == 0)
            return _agent.ProcessAsync(message, ct);

        var skillBlocks = string.Join("\n\n", relevant.Select(s => s.ToPrompt()));
        var augmentedContent = $"<available_skills>\n{skillBlocks}\n</available_skills>\n\n{query}";

        var metadata = message.Metadata is not null
            ? new Dictionary<string, object>(message.Metadata)
            : new Dictionary<string, object>();
        metadata["active_skills"] = relevant.Select(s => s.Name).ToList();

        var enhanced = message with { Content = augmentedContent, Metadata = metadata };
        return _agent.ProcessAsync(enhanced, ct);
    }
}
