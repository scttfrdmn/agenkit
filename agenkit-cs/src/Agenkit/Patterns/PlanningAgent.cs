using System.Text;
using System.Text.RegularExpressions;
using Agenkit.Adapters;
using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Status of a plan step.</summary>
public enum StepStatus
{
    /// <summary>Step not yet started.</summary>
    Pending,
    /// <summary>Step currently executing.</summary>
    InProgress,
    /// <summary>Step completed successfully.</summary>
    Completed,
    /// <summary>Step failed with an error.</summary>
    Failed,
    /// <summary>Step was skipped.</summary>
    Skipped
}

/// <summary>A single step in a plan.</summary>
public class PlanStep
{
    /// <summary>Description of what this step should accomplish.</summary>
    public required string Description { get; init; }

    /// <summary>Step indices that must complete before this step.</summary>
    public IReadOnlyList<int> Dependencies { get; init; } = Array.Empty<int>();

    /// <summary>Current status of the step.</summary>
    public StepStatus Status { get; set; } = StepStatus.Pending;

    /// <summary>Result from executing the step.</summary>
    public object? Result { get; set; }

    /// <summary>Error message if step failed.</summary>
    public string? Error { get; set; }

    /// <summary>Position in the plan (0-indexed).</summary>
    public int StepNumber { get; init; }
}

/// <summary>A plan consisting of multiple steps to achieve a goal.</summary>
public class Plan
{
    /// <summary>Overall goal the plan aims to achieve.</summary>
    public required string Goal { get; init; }

    /// <summary>Ordered list of steps in the plan.</summary>
    public List<PlanStep> Steps { get; init; } = new();

    /// <summary>Returns true when all steps are completed or skipped.</summary>
    public bool IsComplete => Steps.All(s => s.Status is StepStatus.Completed or StepStatus.Skipped);

    /// <summary>Returns true when any step has failed.</summary>
    public bool HasFailures => Steps.Any(s => s.Status == StepStatus.Failed);

    /// <summary>Returns progress as a percentage (0–100).</summary>
    public double Progress => Steps.Count == 0 ? 0 :
        Steps.Count(s => s.Status is StepStatus.Completed or StepStatus.Skipped) * 100.0 / Steps.Count;
}

/// <summary>Executes individual steps of a plan.</summary>
public interface IStepExecutor
{
    /// <summary>Executes a plan step and returns its result.</summary>
    Task<object> ExecuteAsync(PlanStep step, IDictionary<string, object> context, CancellationToken ct = default);
}

/// <summary>Default step executor — returns a simple completion string.</summary>
public class DefaultStepExecutor : IStepExecutor
{
    /// <inheritdoc />
    public Task<object> ExecuteAsync(PlanStep step, IDictionary<string, object> context, CancellationToken ct = default) =>
        Task.FromResult<object>($"Completed: {step.Description}");
}

/// <summary>Configuration for PlanningAgent.</summary>
public record PlanningAgentConfig(
    int MaxSteps = 10,
    bool AllowReplanning = false,
    string? SystemPrompt = null);

/// <summary>
/// Creates and executes plans for complex multi-step tasks.
/// </summary>
public class PlanningAgent : IAgent
{
    private readonly ILlmClient _llm;
    private readonly IStepExecutor _executor;
    private readonly int _maxSteps;
    private readonly bool _allowReplanning;
    private readonly string _systemPrompt;
    private Plan? _currentPlan;

    /// <inheritdoc />
    public string Name => "PlanningAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "planning", "task_decomposition", "step_execution" };

    /// <summary>Creates a new PlanningAgent.</summary>
    public PlanningAgent(ILlmClient llmClient, IStepExecutor? stepExecutor = null, PlanningAgentConfig? config = null)
    {
        _llm = llmClient;
        _executor = stepExecutor ?? new DefaultStepExecutor();
        config ??= new PlanningAgentConfig();
        _maxSteps = config.MaxSteps > 0 ? config.MaxSteps : 10;
        _allowReplanning = config.AllowReplanning;
        _systemPrompt = config.SystemPrompt ?? BuildDefaultSystemPrompt(_maxSteps);
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var plan = await CreatePlanAsync(message.ContentString(), ct).ConfigureAwait(false);
        _currentPlan = plan;

        var summary = await ExecutePlanAsync(plan, ct).ConfigureAwait(false);
        var completed = plan.Steps.Count(s => s.Status == StepStatus.Completed);

        return Message.NewMessage("assistant",
            $"Task completed.\n\nGoal: {plan.Goal}\n\nSteps completed: {completed}/{plan.Steps.Count}\n\nResult: {summary}");
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["has_plan"] = _currentPlan is not null,
            ["plan_progress"] = _currentPlan?.Progress ?? 0.0
        });

    /// <summary>Returns the current plan, if any.</summary>
    public Plan? GetPlan() => _currentPlan;

    /// <summary>Returns progress of the current plan as a percentage.</summary>
    public double GetProgress() => _currentPlan?.Progress ?? 0;

    private async Task<Plan> CreatePlanAsync(string task, CancellationToken ct)
    {
        var messages = new List<Message>
        {
            Message.NewMessage("system", _systemPrompt),
            Message.NewMessage("user", $"Create a plan for: {task}")
        };

        var response = await _llm.ChatAsync(messages, ct).ConfigureAwait(false);
        return ParsePlan(response.ContentString(), task);
    }

    private Plan ParsePlan(string planText, string goal)
    {
        var lines = planText.Split('\n');
        var planGoal = goal;
        var steps = new List<PlanStep>();
        bool inSteps = false;
        int stepNumber = 0;
        var stepRegex = new Regex(@"^(\d+)[.)]");

        foreach (var raw in lines)
        {
            var line = raw.Trim();
            if (line.StartsWith("Goal:", StringComparison.Ordinal))
            {
                planGoal = line["Goal:".Length..].Trim();
                continue;
            }

            if (line.StartsWith("Steps:", StringComparison.Ordinal))
            {
                inSteps = true;
                continue;
            }

            if (inSteps && !string.IsNullOrEmpty(line) && steps.Count < _maxSteps)
            {
                var text = stepRegex.Replace(line, "").Trim();
                if (!string.IsNullOrEmpty(text))
                {
                    steps.Add(new PlanStep
                    {
                        Description = text,
                        StepNumber = stepNumber++
                    });
                }
            }
        }

        return new Plan { Goal = planGoal, Steps = steps };
    }

    private async Task<string> ExecutePlanAsync(Plan plan, CancellationToken ct)
    {
        var context = new Dictionary<string, object>();
        var results = new List<string>();

        while (!plan.IsComplete)
        {
            var nextSteps = GetNextSteps(plan);
            if (nextSteps.Count == 0)
            {
                if (plan.HasFailures && _allowReplanning)
                {
                    await ReplanAsync(plan, ct).ConfigureAwait(false);
                    continue;
                }
                break;
            }

            foreach (var step in nextSteps)
            {
                ct.ThrowIfCancellationRequested();
                step.Status = StepStatus.InProgress;
                try
                {
                    var result = await _executor.ExecuteAsync(step, context, ct).ConfigureAwait(false);
                    step.Result = result;
                    step.Status = StepStatus.Completed;
                    context[$"step_{step.StepNumber}_result"] = result;
                    results.Add($"Step {step.StepNumber + 1}: {step.Description} ✓");
                }
                catch (Exception ex)
                {
                    step.Error = ex.Message;
                    step.Status = StepStatus.Failed;
                    results.Add($"Step {step.StepNumber + 1}: {step.Description} ✗ ({ex.Message})");
                }
            }
        }

        var sb = new StringBuilder(string.Join("\n", results));
        if (plan.IsComplete)
            sb.Append($"\n\nPlan completed successfully ({plan.Progress:F0}%)");
        else if (plan.HasFailures)
            sb.Append($"\n\nPlan failed ({plan.Progress:F0}% complete)");
        else
            sb.Append($"\n\nPlan partially completed ({plan.Progress:F0}%)");

        return sb.ToString();
    }

    private static List<PlanStep> GetNextSteps(Plan plan)
    {
        var completed = plan.Steps
            .Where(s => s.Status is StepStatus.Completed)
            .Select(s => s.StepNumber)
            .ToHashSet();

        return plan.Steps
            .Where(s => s.Status == StepStatus.Pending &&
                        s.Dependencies.All(d => completed.Contains(d)))
            .ToList();
    }

    private async Task ReplanAsync(Plan plan, CancellationToken ct)
    {
        var failed = plan.Steps.Where(s => s.Status == StepStatus.Failed).ToList();
        if (failed.Count == 0) return;

        var failedList = string.Join("\n", failed.Select(s => $"- {s.Description} (Error: {s.Error})"));
        var messages = new List<Message>
        {
            Message.NewMessage("system", _systemPrompt),
            Message.NewMessage("user",
                $"The following steps failed:\n{failedList}\n\nCreate alternative steps to accomplish the goal: {plan.Goal}")
        };

        await _llm.ChatAsync(messages, ct).ConfigureAwait(false);

        foreach (var step in failed)
            step.Status = StepStatus.Skipped;
    }

    private static string BuildDefaultSystemPrompt(int maxSteps) => $"""
        You are a planning agent that breaks down complex tasks into steps.

        For each task, create a plan with specific, actionable steps.

        Format your plan as:
        Goal: [overall goal]
        Steps:
        1. [first step]
        2. [second step]
        ...

        Maximum {maxSteps} steps.

        Guidelines:
        - Make steps concrete and actionable
        - Consider dependencies between steps
        - Keep steps focused and achievable
        - Include verification steps when appropriate
        """;
}
