using Agenkit.Adapters;
using Agenkit.Core;
using Agenkit.Patterns;

Console.WriteLine("=== Agenkit C# — ReAct Agent Example ===");

// Mock agent that simulates a ReAct-style response
var innerAgent = new MockAdapter(new[]
{
    "Thought: I need to calculate 15 * 7\nAction: calculator\nAction Input: 15 * 7",
    "Thought: The result is 105\nFinal Answer: 15 multiplied by 7 equals 105."
});

// Simple calculator tool
var calculator = new CalculatorTool();

var config = new ReActConfig(
    Agent: new LlmBackedAgent(innerAgent),
    Tools: new ITool[] { calculator },
    MaxSteps: 5,
    Verbose: false);

var agent = new ReActAgent(config);

Console.WriteLine($"Agent: {agent.Name}");
Console.WriteLine($"Tools: {string.Join(", ", new[] { calculator.Name })}");
Console.WriteLine();

var question = "What is 15 multiplied by 7?";
Console.WriteLine($"Question: {question}");
var response = await agent.ProcessAsync(Message.NewMessage("user", question));
Console.WriteLine($"Answer: {response.ContentString()}");

Console.WriteLine($"\nSteps taken: {agent.GetSteps().Count}");

// ---- Helpers ----

class CalculatorTool : ITool
{
    public string Name => "calculator";
    public string Description => "Evaluates simple arithmetic expressions.";

    public Task<ToolResult> ExecuteAsync(IDictionary<string, object> parameters, CancellationToken ct = default)
    {
        var input = parameters.TryGetValue("input", out var val) ? val?.ToString() ?? "" : "";
        // Very simple eval — only handles multiplication for demo
        if (input.Contains('*'))
        {
            var parts = input.Split('*');
            if (parts.Length == 2 &&
                double.TryParse(parts[0].Trim(), out var a) &&
                double.TryParse(parts[1].Trim(), out var b))
            {
                return Task.FromResult(ToolResult.Ok((a * b).ToString()));
            }
        }
        return Task.FromResult(ToolResult.Fail($"cannot evaluate: {input}"));
    }
}

class LlmBackedAgent : IAgent
{
    private readonly MockAdapter _llm;
    public LlmBackedAgent(MockAdapter llm) => _llm = llm;
    public string Name => "LlmAgent";
    public IReadOnlyList<string> Capabilities => new[] { "chat" };
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default) =>
        await _llm.ChatAsync(new[] { message }, ct);
    public IntrospectionResult Introspect() => new(Name, Capabilities);
}
