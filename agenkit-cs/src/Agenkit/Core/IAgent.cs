namespace Agenkit.Core;

/// <summary>
/// Core interface that all agents must implement.
/// </summary>
public interface IAgent
{
    /// <summary>Returns the unique name of this agent.</summary>
    string Name { get; }

    /// <summary>Returns the list of capability identifiers this agent supports.</summary>
    IReadOnlyList<string> Capabilities { get; }

    /// <summary>Processes a message and returns a response.</summary>
    Task<Message> ProcessAsync(Message message, CancellationToken ct = default);

    /// <summary>Returns a snapshot of the agent's internal state.</summary>
    IntrospectionResult Introspect();
}

/// <summary>
/// Extends IAgent to support streaming responses via IAsyncEnumerable.
/// </summary>
public interface IStreamingAgent : IAgent
{
    /// <summary>Processes a message and streams partial responses.</summary>
    IAsyncEnumerable<Message> StreamAsync(Message message, CancellationToken ct = default);
}
