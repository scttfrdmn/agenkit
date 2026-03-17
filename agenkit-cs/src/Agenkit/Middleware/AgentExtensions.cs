using Agenkit.Core;

namespace Agenkit.Middleware;

/// <summary>
/// Fluent extension methods for composing middleware around any IAgent.
/// </summary>
public static class AgentExtensions
{
    /// <summary>Wraps the agent with retry logic.</summary>
    public static IAgent WithRetry(this IAgent agent, RetryConfig? config = null) =>
        new RetryMiddleware(agent, config);

    /// <summary>Wraps the agent with a per-request timeout.</summary>
    public static IAgent WithTimeout(this IAgent agent, TimeSpan timeout) =>
        new TimeoutMiddleware(agent, timeout);

    /// <summary>Wraps the agent with a circuit breaker.</summary>
    public static IAgent WithCircuitBreaker(this IAgent agent, CircuitBreakerConfig? config = null) =>
        new CircuitBreakerMiddleware(agent, config);

    /// <summary>Wraps the agent with an in-memory response cache.</summary>
    public static IAgent WithCaching(this IAgent agent, CachingConfig? config = null) =>
        new CachingMiddleware(agent, config);

    /// <summary>Wraps the agent with a global token-bucket rate limiter.</summary>
    public static IAgent WithRateLimit(this IAgent agent, RateLimiterConfig config) =>
        new RateLimiterMiddleware(agent, config);

    /// <summary>Wraps the agent with latency and error metrics collection.</summary>
    public static MetricsMiddleware WithMetrics(this IAgent agent) =>
        new MetricsMiddleware(agent);
}
