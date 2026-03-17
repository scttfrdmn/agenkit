using System.Text;
using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Stop reason for the ReAct loop.</summary>
public enum ReActStopReason
{
    /// <summary>Agent provided a final answer.</summary>
    FinalAnswer,
    /// <summary>Maximum number of steps was reached.</summary>
    MaxSteps,
    /// <summary>Agent made an invalid or empty action.</summary>
    InvalidAction,
    /// <summary>Tool execution failed with an error.</summary>
    ToolError
}

/// <summary>
/// A single step in the ReAct reasoning-acting loop.
/// </summary>
public record ReActStep(
    string Thought,
    string Action,
    string ActionInput,
    string Observation,
    bool IsFinal);

/// <summary>
/// Configuration for ReActAgent.
/// </summary>
public record ReActConfig(
    IAgent Agent,
    IReadOnlyList<ITool> Tools,
    int MaxSteps = 10,
    bool Verbose = false,
    string? PromptTemplate = null);

/// <summary>
/// ReAct (Reasoning + Acting) agent that interleaves thought and tool use.
/// </summary>
public class ReActAgent : IAgent
{
    private readonly IAgent _agent;
    private readonly Dictionary<string, ITool> _tools;
    private readonly int _maxSteps;
    private readonly bool _verbose;
    private readonly string _promptTemplate;
    private readonly List<ReActStep> _steps = new();

    /// <inheritdoc />
    public string Name => "ReActAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "reasoning", "tool-use", "react" };

    /// <summary>Creates a new ReActAgent.</summary>
    public ReActAgent(ReActConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        if (config.Tools.Count == 0)
            throw new ArgumentException("at least one tool is required", nameof(config));

        _agent = config.Agent;
        _tools = config.Tools.ToDictionary(t => t.Name, t => t);
        _maxSteps = config.MaxSteps > 0 ? config.MaxSteps : 10;
        _verbose = config.Verbose;
        _promptTemplate = config.PromptTemplate ?? BuildDefaultPrompt(config.Tools);
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        _steps.Clear();
        var history = new List<string>
        {
            _promptTemplate,
            $"\nQuestion: {message.ContentString()}"
        };

        for (int step = 0; step < _maxSteps; step++)
        {
            ct.ThrowIfCancellationRequested();

            var prompt = string.Join("\n", history);
            var response = await _agent.ProcessAsync(
                Message.NewMessage("user", prompt), ct).ConfigureAwait(false);

            var parsed = ParseResponse(response.ContentString());

            if (parsed.IsFinal)
            {
                _steps.Add(parsed);
                return FormatFinalAnswer(parsed, ReActStopReason.FinalAnswer);
            }

            if (string.IsNullOrEmpty(parsed.Action))
            {
                _steps.Add(parsed);
                return FormatFinalAnswer(parsed, ReActStopReason.InvalidAction);
            }

            if (!_tools.TryGetValue(parsed.Action, out var tool))
            {
                var available = string.Join(", ", _tools.Keys);
                var withError = parsed with
                {
                    Observation = $"Error: Tool '{parsed.Action}' not found. Available tools: {available}"
                };
                _steps.Add(withError);
                history.Add(FormatStep(withError));
                continue;
            }

            ToolResult toolResult;
            try
            {
                toolResult = await tool.ExecuteAsync(
                    new Dictionary<string, object> { ["input"] = parsed.ActionInput }, ct)
                    .ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                var withError = parsed with { Observation = $"Error: {ex.Message}" };
                _steps.Add(withError);
                return FormatFinalAnswer(withError, ReActStopReason.ToolError);
            }

            var observation = toolResult.Success
                ? toolResult.Data?.ToString() ?? ""
                : $"Error: {toolResult.Error ?? "tool execution failed"}";

            var completed = parsed with { Observation = observation };
            _steps.Add(completed);
            history.Add(FormatStep(completed));
        }

        // Max steps reached
        var last = _steps.Count > 0 ? _steps[^1] : new ReActStep("reached maximum steps", "", "", "", false);
        return FormatFinalAnswer(last, ReActStopReason.MaxSteps);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["step_count"] = _steps.Count,
            ["tools"] = _tools.Keys.ToList()
        });

    /// <summary>Returns a copy of all reasoning steps taken in the last call.</summary>
    public IReadOnlyList<ReActStep> GetSteps() => _steps.ToList();

    private static string BuildDefaultPrompt(IReadOnlyList<ITool> tools)
    {
        var toolList = string.Join("\n", tools.Select(t => $"- {t.Name}: {t.Description}"));
        return $"""
            You are a helpful assistant that can use tools to answer questions.

            Available tools:
            {toolList}

            Use the following format:

            Thought: Think about what to do next
            Action: [tool name]
            Action Input: [input for the tool]
            Observation: [result will be provided]

            ... (repeat Thought/Action/Observation as needed)

            Thought: I now know the final answer
            Final Answer: [your final answer here]

            Begin!
            """;
    }

    private static ReActStep ParseResponse(string response)
    {
        var thought = "";
        var action = "";
        var actionInput = "";
        var observation = "";
        var isFinal = false;

        foreach (var raw in response.Split('\n'))
        {
            var line = raw.Trim();
            if (line.StartsWith("Thought:", StringComparison.Ordinal))
                thought = line["Thought:".Length..].Trim();
            else if (line.StartsWith("Action:", StringComparison.Ordinal))
                action = line["Action:".Length..].Trim();
            else if (line.StartsWith("Action Input:", StringComparison.Ordinal))
                actionInput = line["Action Input:".Length..].Trim();
            else if (line.StartsWith("Final Answer:", StringComparison.Ordinal))
            {
                if (string.IsNullOrEmpty(thought)) thought = "reached final answer";
                observation = line["Final Answer:".Length..].Trim();
                isFinal = true;
                break;
            }
        }

        return new ReActStep(thought, action, actionInput, observation, isFinal);
    }

    private static string FormatStep(ReActStep step)
    {
        var sb = new StringBuilder();
        sb.Append($"Thought: {step.Thought}");
        if (!string.IsNullOrEmpty(step.Action))
        {
            sb.Append($"\nAction: {step.Action}");
            sb.Append($"\nAction Input: {step.ActionInput}");
        }
        if (!string.IsNullOrEmpty(step.Observation))
            sb.Append($"\nObservation: {step.Observation}");
        return sb.ToString();
    }

    private Message FormatFinalAnswer(ReActStep step, ReActStopReason stopReason)
    {
        var sb = new StringBuilder();

        if (_verbose)
        {
            for (int i = 0; i < _steps.Count; i++)
            {
                if (i > 0) sb.Append("\n\n");
                sb.Append(FormatStep(_steps[i]));
            }
            sb.Append("\n\n---\n\n");
        }

        if (stopReason == ReActStopReason.FinalAnswer)
        {
            sb.Append(string.IsNullOrEmpty(step.Observation) ? "No final answer provided" : step.Observation);
        }
        else
        {
            sb.Append($"Unable to complete task ({stopReason})");
            if (!string.IsNullOrEmpty(step.Thought))
                sb.Append($"\nLast thought: {step.Thought}");
        }

        return new Message(
            "assistant",
            sb.ToString(),
            new Dictionary<string, object>
            {
                ["stop_reason"] = stopReason.ToString(),
                ["steps"] = _steps.Count,
                ["reasoning"] = (object)_steps.ToList()
            },
            DateTimeOffset.UtcNow);
    }
}
