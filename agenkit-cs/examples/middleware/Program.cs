using Agenkit.Adapters;
using Agenkit.Core;
using Agenkit.Middleware;

Console.WriteLine("=== Agenkit C# — Middleware Example ===");

// Base agent backed by MockAdapter
IAgent baseAgent = new SimpleAgent(new MockAdapter("Hello from the agent!"));

// --- Retry ---
Console.WriteLine("\n--- Retry Middleware ---");
var withRetry = baseAgent.WithRetry(new RetryConfig(MaxAttempts: 3, InitialDelay: TimeSpan.Zero));
var r1 = await withRetry.ProcessAsync(Message.NewMessage("user", "hi"));
Console.WriteLine($"Response: {r1.ContentString()}");

// --- Timeout ---
Console.WriteLine("\n--- Timeout Middleware ---");
var withTimeout = baseAgent.WithTimeout(TimeSpan.FromSeconds(5));
var r2 = await withTimeout.ProcessAsync(Message.NewMessage("user", "hi"));
Console.WriteLine($"Response: {r2.ContentString()}");

// --- Circuit Breaker ---
Console.WriteLine("\n--- Circuit Breaker Middleware ---");
var withCb = baseAgent.WithCircuitBreaker(new CircuitBreakerConfig(FailureThreshold: 5));
var r3 = await withCb.ProcessAsync(Message.NewMessage("user", "hi"));
Console.WriteLine($"Response: {r3.ContentString()}");

// --- Metrics ---
Console.WriteLine("\n--- Metrics Middleware ---");
var withMetrics = baseAgent.WithMetrics();
await withMetrics.ProcessAsync(Message.NewMessage("user", "req1"));
await withMetrics.ProcessAsync(Message.NewMessage("user", "req2"));
Console.WriteLine($"Total requests: {withMetrics.TotalRequests}");
Console.WriteLine($"Average latency: {withMetrics.AverageLatencyMs:F2}ms");

// --- Caching ---
Console.WriteLine("\n--- Caching Middleware ---");
var withCache = baseAgent.WithCaching(new CachingConfig(Ttl: TimeSpan.FromMinutes(5)));
var rc1 = await withCache.ProcessAsync(Message.NewMessage("user", "cached query"));
var rc2 = await withCache.ProcessAsync(Message.NewMessage("user", "cached query")); // cache hit
Console.WriteLine($"First:  {rc1.ContentString()}");
Console.WriteLine($"Second: {rc2.ContentString()} (cache_hit={rc2.Metadata?.ContainsKey("cache_hit") ?? false})");

// ---- Helper ----
class SimpleAgent : IAgent
{
    private readonly MockAdapter _llm;
    public SimpleAgent(MockAdapter llm) => _llm = llm;
    public string Name => "SimpleAgent";
    public IReadOnlyList<string> Capabilities => new[] { "chat" };
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default) =>
        await _llm.ChatAsync(new[] { message }, ct);
    public IntrospectionResult Introspect() => new(Name, Capabilities);
}
