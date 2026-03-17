using Agenkit.Core;
using Agenkit.Middleware;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Middleware;

public class RateLimiterTests
{
    [Fact]
    public async Task ProcessAsync_WithinLimit_Succeeds()
    {
        var inner = new MockAgent("ok");
        var limiter = new RateLimiterMiddleware(inner, new RateLimiterConfig(RequestsPerSecond: 10, BurstSize: 10));
        var response = await limiter.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("ok");
    }

    [Fact]
    public async Task ProcessAsync_ExceedsLimit_Throws()
    {
        var inner = new MockAgent("ok");
        var limiter = new RateLimiterMiddleware(inner, new RateLimiterConfig(RequestsPerSecond: 1, BurstSize: 1));

        await limiter.ProcessAsync(Message.NewMessage("user", "first")); // Uses the one token

        await limiter.Invoking(l => l.ProcessAsync(Message.NewMessage("user", "second")))
            .Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*rate limit exceeded*");
    }

    [Fact]
    public void Constructor_ZeroRatePerSecond_Throws()
    {
        var act = () => new RateLimiterMiddleware(new MockAgent(), new RateLimiterConfig(RequestsPerSecond: 0));
        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public async Task PerUserRateLimiter_DifferentUsers_IndependentBuckets()
    {
        var inner = new MockAgent("ok");
        var limiter = new PerUserRateLimiterMiddleware(inner, requestsPerSecond: 1, burstSize: 1);

        var msg1 = Message.NewMessage("user", "q1").WithMetadata("user_id", "alice");
        var msg2 = Message.NewMessage("user", "q2").WithMetadata("user_id", "bob");

        // Both users can make one request
        await limiter.ProcessAsync(msg1);
        await limiter.ProcessAsync(msg2); // different user, independent bucket

        // Alice is now rate-limited
        await limiter.Invoking(l => l.ProcessAsync(msg1))
            .Should().ThrowAsync<InvalidOperationException>();
    }

    [Fact]
    public async Task PerUserRateLimiter_AnonymousUser_UsesDefaultKey()
    {
        var inner = new MockAgent("ok");
        var limiter = new PerUserRateLimiterMiddleware(inner, requestsPerSecond: 1, burstSize: 1);
        await limiter.ProcessAsync(Message.NewMessage("user", "test"));

        await limiter.Invoking(l => l.ProcessAsync(Message.NewMessage("user", "test")))
            .Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*anonymous*");
    }
}
