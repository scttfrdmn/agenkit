namespace Agenkit.Core;

/// <summary>
/// Represents a snapshot of an agent's internal state and capabilities.
/// </summary>
public record IntrospectionResult(
    string AgentName,
    IReadOnlyList<string> Capabilities,
    IReadOnlyDictionary<string, object>? Memory = null,
    IReadOnlyDictionary<string, object>? State = null,
    IReadOnlyList<string>? Tools = null);
