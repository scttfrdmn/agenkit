using Agenkit.Core;

Console.WriteLine("=== Agenkit C# — Streaming Example ===");
Console.WriteLine();

// Demonstrate IAsyncEnumerable streaming via IStreamingAgent
IStreamingAgent streamingAgent = new WordByWordStreamingAgent();

Console.Write("Streaming response: ");
await foreach (var chunk in streamingAgent.StreamAsync(Message.NewMessage("user", "Tell me about AI.")))
{
    Console.Write(chunk.ContentString());
    Console.Write(" ");
    await Task.Delay(50); // simulate real streaming delay
}
Console.WriteLine();
Console.WriteLine("\nStreaming complete.");

// ---- Streaming agent implementation ----
class WordByWordStreamingAgent : IStreamingAgent
{
    private static readonly string[] Words =
        "Artificial intelligence is the simulation of human intelligence in machines.".Split(' ');

    public string Name => "StreamingAgent";
    public IReadOnlyList<string> Capabilities => new[] { "streaming", "chat" };

    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        // Non-streaming fallback
        return Message.NewMessage("assistant", string.Join(" ", Words));
    }

    public async IAsyncEnumerable<Message> StreamAsync(
        Message message,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct = default)
    {
        foreach (var word in Words)
        {
            ct.ThrowIfCancellationRequested();
            yield return Message.NewMessage("assistant", word);
            await Task.Yield();
        }
    }

    public IntrospectionResult Introspect() => new(Name, Capabilities);
}
