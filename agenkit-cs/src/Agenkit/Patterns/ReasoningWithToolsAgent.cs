using System.Text;
using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Configuration for ReasoningWithToolsAgent.</summary>
public record ReasoningWithToolsAgentConfig(
    IAgent Inner,
    IReadOnlyList<ITool> Tools,
    int MaxToolCalls = 5,
    string? SystemPrompt = null);

/// <summary>
/// Agent that interleaves reasoning steps with tool calls.
/// </summary>
public class ReasoningWithToolsAgent : IAgent
{
    private readonly IAgent _inner;
    private readonly Dictionary<string, ITool> _tools;
    private readonly int _maxToolCalls;
    private readonly string? _systemPrompt;

    /// <inheritdoc />
    public string Name => "ReasoningWithToolsAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "reasoning", "tool-use", "interleaved" };

    /// <summary>Creates a new ReasoningWithToolsAgent.</summary>
    public ReasoningWithToolsAgent(ReasoningWithToolsAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        _inner = config.Inner;
        _tools = config.Tools.ToDictionary(t => t.Name, t => t);
        _maxToolCalls = config.MaxToolCalls > 0 ? config.MaxToolCalls : 5;
        _systemPrompt = config.SystemPrompt;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var toolNames = string.Join(", ", _tools.Keys);
        var prompt = _systemPrompt is not null
            ? $"{_systemPrompt}\n\nAvailable tools: {toolNames}\n\nQuery: {message.ContentString()}"
            : $"Available tools: {toolNames}\n\nQuery: {message.ContentString()}";

        var current = Message.NewMessage("user", prompt);
        var toolCallCount = 0;
        var history = new StringBuilder();

        for (int i = 0; i <= _maxToolCalls; i++)
        {
            ct.ThrowIfCancellationRequested();
            var response = await _inner.ProcessAsync(current, ct).ConfigureAwait(false);
            var text = response.ContentString();

            // Check if agent wants to use a tool
            var toolCall = ParseToolCall(text);
            if (toolCall is not null && toolCallCount < _maxToolCalls)
            {
                if (_tools.TryGetValue(toolCall.Value.name, out var tool))
                {
                    toolCallCount++;
                    ToolResult result;
                    try
                    {
                        result = await tool.ExecuteAsync(
                            new Dictionary<string, object> { ["input"] = toolCall.Value.input }, ct)
                            .ConfigureAwait(false);
                    }
                    catch (Exception ex)
                    {
                        result = ToolResult.Fail(ex.Message);
                    }

                    var observation = result.Success
                        ? result.Data?.ToString() ?? ""
                        : $"Error: {result.Error}";

                    history.AppendLine(text);
                    history.AppendLine($"Tool Result: {observation}");

                    current = Message.NewMessage("user",
                        $"{history}\nContinue reasoning with the above tool result.");
                    continue;
                }
            }

            // No more tool calls — return final response
            return response.WithMetadata("tool_calls", toolCallCount);
        }

        return Message.NewMessage("assistant", history.ToString()).WithMetadata("tool_calls", toolCallCount);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["tool_count"] = _tools.Count,
            ["max_tool_calls"] = _maxToolCalls
        });

    private static (string name, string input)? ParseToolCall(string text)
    {
        // Simple parsing: look for "USE_TOOL: <name>(<input>)" pattern
        const string prefix = "USE_TOOL:";
        var idx = text.IndexOf(prefix, StringComparison.OrdinalIgnoreCase);
        if (idx < 0) return null;

        var rest = text[(idx + prefix.Length)..].Trim();
        var parenOpen = rest.IndexOf('(');
        var parenClose = rest.LastIndexOf(')');
        if (parenOpen < 0 || parenClose <= parenOpen) return null;

        var name = rest[..parenOpen].Trim();
        var input = rest[(parenOpen + 1)..parenClose].Trim();
        return (name, input);
    }
}
