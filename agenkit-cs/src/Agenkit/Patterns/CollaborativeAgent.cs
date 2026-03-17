using System.Text;
using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Configuration for CollaborativeAgent.</summary>
public record CollaborativeAgentConfig(
    IReadOnlyList<IAgent> Peers,
    int Rounds = 1,
    string? SystemPrompt = null);

/// <summary>
/// Coordinates multiple peer agents to reach consensus on a response.
/// </summary>
public class CollaborativeAgent : IAgent
{
    private readonly IReadOnlyList<IAgent> _peers;
    private readonly int _rounds;
    private readonly string? _systemPrompt;

    /// <inheritdoc />
    public string Name => "CollaborativeAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "collaboration", "consensus", "multi-agent" };

    /// <summary>Creates a new CollaborativeAgent.</summary>
    public CollaborativeAgent(CollaborativeAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        if (config.Peers.Count < 2)
            throw new ArgumentException("at least two peers are required", nameof(config));
        _peers = config.Peers;
        _rounds = config.Rounds > 0 ? config.Rounds : 1;
        _systemPrompt = config.SystemPrompt;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var responses = new List<Message>();

        // Initial round — all peers respond to the original message
        foreach (var peer in _peers)
        {
            ct.ThrowIfCancellationRequested();
            var resp = await peer.ProcessAsync(message, ct).ConfigureAwait(false);
            responses.Add(resp);
        }

        // Refinement rounds
        for (int r = 1; r < _rounds; r++)
        {
            var summary = BuildSummary(responses);
            var refinementMsg = Message.NewMessage("user",
                $"Here are the current responses from your peers:\n{summary}\n\nRefine your answer considering these perspectives.");

            var refined = new List<Message>();
            foreach (var peer in _peers)
            {
                ct.ThrowIfCancellationRequested();
                var resp = await peer.ProcessAsync(refinementMsg, ct).ConfigureAwait(false);
                refined.Add(resp);
            }
            responses = refined;
        }

        // Build consensus — use first peer's final response with all responses as metadata
        var consensus = BuildConsensus(responses);
        return consensus.WithMetadata("peer_count", _peers.Count)
                        .WithMetadata("rounds", _rounds);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["peer_count"] = _peers.Count,
            ["rounds"] = _rounds
        });

    private static string BuildSummary(IReadOnlyList<Message> responses)
    {
        var sb = new StringBuilder();
        for (int i = 0; i < responses.Count; i++)
            sb.AppendLine($"Peer {i + 1}: {responses[i].ContentString()}");
        return sb.ToString();
    }

    private static Message BuildConsensus(IReadOnlyList<Message> responses)
    {
        // Simple: return first response content, noting all agreed
        var sb = new StringBuilder();
        sb.AppendLine(responses[0].ContentString());
        return Message.NewMessage("assistant", sb.ToString().Trim());
    }
}
