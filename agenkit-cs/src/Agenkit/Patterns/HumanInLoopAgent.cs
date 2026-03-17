using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Request sent to the human approver.</summary>
public record ApprovalRequest(
    Message Message,
    string Reason,
    IReadOnlyDictionary<string, object>? Context = null);

/// <summary>Response from the human approver.</summary>
public record ApprovalResponse(bool Approved, string? Feedback = null);

/// <summary>Configuration for HumanInLoopAgent.</summary>
public record HumanInLoopAgentConfig(
    IAgent Inner,
    Func<ApprovalRequest, Task<ApprovalResponse>> ApprovalHandler,
    string? ApprovalReason = null);

/// <summary>
/// Wraps an agent with a human approval gate before forwarding messages.
/// </summary>
public class HumanInLoopAgent : IAgent
{
    private readonly IAgent _inner;
    private readonly Func<ApprovalRequest, Task<ApprovalResponse>> _handler;
    private readonly string _approvalReason;

    /// <inheritdoc />
    public string Name => "HumanInLoopAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities =>
        _inner.Capabilities.Concat(new[] { "human-in-loop", "approval" }).ToList();

    /// <summary>Creates a new HumanInLoopAgent.</summary>
    public HumanInLoopAgent(HumanInLoopAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        _inner = config.Inner;
        _handler = config.ApprovalHandler;
        _approvalReason = config.ApprovalReason ?? "Human approval required before processing this message.";
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var request = new ApprovalRequest(message, _approvalReason);
        var approval = await _handler(request).ConfigureAwait(false);

        if (!approval.Approved)
        {
            var feedback = approval.Feedback ?? "Request was not approved.";
            return Message.NewMessage("assistant", $"Request denied: {feedback}");
        }

        var response = await _inner.ProcessAsync(message, ct).ConfigureAwait(false);

        return response.WithMetadata("human_approved", true)
                       .WithMetadata("approval_feedback", approval.Feedback ?? "");
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(Name, Capabilities);
}
