using System.Diagnostics;
using Agenkit.Core;

namespace Agenkit.Observability;

/// <summary>
/// Wraps an agent to add OpenTelemetry-compatible activity spans.
/// </summary>
public class TracingAgent : IAgent
{
    private static readonly ActivitySource Source = new("Agenkit");
    private readonly IAgent _inner;

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Creates a new TracingAgent.</summary>
    public TracingAgent(IAgent inner) => _inner = inner;

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        using var activity = Source.StartActivity($"agent.process/{_inner.Name}");
        activity?.SetTag("agent.name", _inner.Name);
        activity?.SetTag("message.role", message.Role);

        try
        {
            var result = await _inner.ProcessAsync(message, ct).ConfigureAwait(false);
            activity?.SetTag("response.role", result.Role);
            activity?.SetStatus(ActivityStatusCode.Ok);
            return result;
        }
        catch (Exception ex)
        {
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.AddTag("exception.type", ex.GetType().FullName);
            activity?.AddTag("exception.message", ex.Message);
            throw;
        }
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => _inner.Introspect();
}
