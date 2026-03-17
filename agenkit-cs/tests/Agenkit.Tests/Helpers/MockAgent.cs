using Agenkit.Adapters;
using Agenkit.Core;

namespace Agenkit.Tests.Helpers;

/// <summary>Mock IAgent for testing.</summary>
public class MockAgent : IAgent
{
    private readonly string _response;
    private readonly Exception? _exception;
    private int _callCount;
    private readonly Queue<string>? _responses;

    /// <summary>Number of times ProcessAsync was called.</summary>
    public int CallCount => _callCount;

    /// <summary>Last message received.</summary>
    public Message? LastMessage { get; private set; }

    public MockAgent(string response = "mock response", Exception? exception = null)
    {
        _response = response;
        _exception = exception;
    }

    public MockAgent(IEnumerable<string> responses)
    {
        _responses = new Queue<string>(responses);
        _response = "";
    }

    public string Name => "MockAgent";
    public IReadOnlyList<string> Capabilities => new[] { "mock" };

    public Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        Interlocked.Increment(ref _callCount);
        LastMessage = message;

        if (_exception is not null) throw _exception;

        string content;
        if (_responses is not null && _responses.Count > 0)
            content = _responses.Dequeue();
        else
            content = _response;

        return Task.FromResult(Message.NewMessage("assistant", content));
    }

    public IntrospectionResult Introspect() => new(Name, Capabilities);
}

/// <summary>Mock ILlmClient for testing.</summary>
public class MockLlmClient : ILlmClient
{
    private readonly string _response;
    private int _callCount;
    private readonly Queue<string>? _responses;

    public int CallCount => _callCount;

    public MockLlmClient(string response = "mock response") => _response = response;

    public MockLlmClient(IEnumerable<string> responses)
    {
        _responses = new Queue<string>(responses);
        _response = "";
    }

    public Task<Message> ChatAsync(IList<Message> messages, CancellationToken ct = default)
    {
        Interlocked.Increment(ref _callCount);
        ct.ThrowIfCancellationRequested();

        string content;
        if (_responses is not null && _responses.Count > 0)
            content = _responses.Dequeue();
        else
            content = _response;

        return Task.FromResult(Message.NewMessage("assistant", content));
    }
}

/// <summary>Mock ITool for testing.</summary>
public class MockTool : ITool
{
    private readonly string _result;
    private int _callCount;

    public int CallCount => _callCount;

    public MockTool(string name, string result = "tool result")
    {
        Name = name;
        _result = result;
    }

    public string Name { get; }
    public string Description => $"Mock tool: {Name}";

    public Task<ToolResult> ExecuteAsync(IDictionary<string, object> parameters, CancellationToken ct = default)
    {
        Interlocked.Increment(ref _callCount);
        return Task.FromResult(ToolResult.Ok(_result));
    }
}

/// <summary>Mock ITool that always fails.</summary>
public class FailingTool : ITool
{
    public FailingTool(string name) => Name = name;
    public string Name { get; }
    public string Description => $"Failing tool: {Name}";

    public Task<ToolResult> ExecuteAsync(IDictionary<string, object> parameters, CancellationToken ct = default) =>
        Task.FromResult(ToolResult.Fail("tool failed"));
}
