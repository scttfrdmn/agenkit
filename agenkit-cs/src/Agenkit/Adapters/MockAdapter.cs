using Agenkit.Core;

namespace Agenkit.Adapters;

/// <summary>
/// Deterministic mock LLM client for testing.
/// </summary>
public class MockAdapter : ILlmClient
{
    private readonly string _response;
    private readonly Queue<string>? _responses;
    private int _callCount;

    /// <summary>Number of times ChatAsync has been called.</summary>
    public int CallCount => _callCount;

    /// <summary>Creates a mock adapter that always returns the given response.</summary>
    public MockAdapter(string response = "mock response")
    {
        _response = response;
    }

    /// <summary>Creates a mock adapter that returns responses in sequence, cycling at end.</summary>
    public MockAdapter(IEnumerable<string> responses)
    {
        _responses = new Queue<string>(responses);
        _response = "";
    }

    /// <inheritdoc />
    public Task<Message> ChatAsync(IList<Message> messages, CancellationToken ct = default)
    {
        Interlocked.Increment(ref _callCount);
        ct.ThrowIfCancellationRequested();

        string content;
        if (_responses is not null && _responses.Count > 0)
        {
            content = _responses.Dequeue();
        }
        else
        {
            content = _response;
        }

        return Task.FromResult(Message.NewMessage("assistant", content));
    }
}
