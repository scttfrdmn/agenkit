using Agenkit.Core;
using Agenkit.Middleware;
using Agenkit.Tests.Helpers;

namespace Agenkit.Tests.Middleware;

public class AgentExtensionsTests
{
    [Fact]
    public async Task WithRetry_ReturnsRetryMiddleware()
    {
        var inner = new MockAgent("ok");
        var wrapped = inner.WithRetry();
        var response = await wrapped.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("ok");
    }

    [Fact]
    public async Task WithTimeout_ReturnsTimeoutMiddleware()
    {
        var inner = new MockAgent("ok");
        var wrapped = inner.WithTimeout(TimeSpan.FromSeconds(5));
        var response = await wrapped.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("ok");
    }

    [Fact]
    public async Task WithCircuitBreaker_ReturnsCircuitBreakerMiddleware()
    {
        var inner = new MockAgent("ok");
        var wrapped = inner.WithCircuitBreaker();
        var response = await wrapped.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("ok");
    }

    [Fact]
    public async Task WithCaching_ReturnsCachingMiddleware()
    {
        var inner = new MockAgent("ok");
        var wrapped = inner.WithCaching();
        var response = await wrapped.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("ok");
    }

    [Fact]
    public async Task WithMetrics_ReturnsMetricsMiddleware_WithTracking()
    {
        var inner = new MockAgent("ok");
        var wrapped = inner.WithMetrics();
        await wrapped.ProcessAsync(Message.NewMessage("user", "test"));
        wrapped.TotalRequests.Should().Be(1);
    }

    [Fact]
    public void WithRateLimit_ReturnsRateLimiterMiddleware()
    {
        var inner = new MockAgent("ok");
        var wrapped = inner.WithRateLimit(new RateLimiterConfig(RequestsPerSecond: 100));
        wrapped.Should().BeOfType<RateLimiterMiddleware>();
    }

    [Fact]
    public async Task ChainedMiddleware_WorksInSequence()
    {
        var inner = new MockAgent("ok");
        var response = await inner
            .WithRetry()
            .WithTimeout(TimeSpan.FromSeconds(5))
            .WithMetrics()
            .ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("ok");
    }
}
