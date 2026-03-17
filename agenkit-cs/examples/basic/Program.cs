using Agenkit.Adapters;
using Agenkit.Core;
using Agenkit.Patterns;

// Basic ConversationalAgent example using MockAdapter
Console.WriteLine("=== Agenkit C# — Basic Example ===");

var llm = new MockAdapter("Hello! How can I help you today?");
var config = new ConversationalAgentConfig(
    LlmClient: llm,
    MaxHistory: 10,
    SystemPrompt: "You are a helpful assistant.");

var agent = new ConversationalAgent(config);

Console.WriteLine($"Agent: {agent.Name}");
Console.WriteLine($"Capabilities: {string.Join(", ", agent.Capabilities)}");
Console.WriteLine();

// Multi-turn conversation
var turns = new[] { "Hello!", "What can you do?", "Thank you!" };
foreach (var input in turns)
{
    Console.WriteLine($"User: {input}");
    var response = await agent.ProcessAsync(Message.NewMessage("user", input));
    Console.WriteLine($"Agent: {response.ContentString()}");
    Console.WriteLine();
}

// Introspection
var state = agent.Introspect();
Console.WriteLine($"History size: {state.State!["history_count"]}");
