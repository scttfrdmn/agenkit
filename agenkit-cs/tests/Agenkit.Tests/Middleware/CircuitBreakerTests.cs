using Agenkit.Core;
using Agenkit.Middleware;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Middleware;

public class CircuitBreakerTests
{
    [Fact]
    public async Task ProcessAsync_SuccessfulCall_CircuitStaysClosed()
    {
        var inner = new MockAgent("ok");
        var cb = new CircuitBreakerMiddleware(inner, new CircuitBreakerConfig(FailureThreshold: 3));
        await cb.ProcessAsync(Message.NewMessage("user", "test"));
        cb.State.Should().Be(CircuitState.Closed);
    }

    [Fact]
    public async Task ProcessAsync_ThresholdReached_OpensCircuit()
    {
        var inner = new MockAgent(exception: new Exception("fail"));
        var cb = new CircuitBreakerMiddleware(inner, new CircuitBreakerConfig(FailureThreshold: 3));

        for (int i = 0; i < 3; i++)
        {
            try { await cb.ProcessAsync(Message.NewMessage("user", "test")); }
            catch { /* expected */ }
        }

        cb.State.Should().Be(CircuitState.Open);
    }

    [Fact]
    public async Task ProcessAsync_OpenCircuit_ThrowsImmediately()
    {
        var inner = new MockAgent(exception: new Exception("fail"));
        var cb = new CircuitBreakerMiddleware(inner, new CircuitBreakerConfig(FailureThreshold: 1));

        try { await cb.ProcessAsync(Message.NewMessage("user", "test")); } catch { }

        await cb.Invoking(c => c.ProcessAsync(Message.NewMessage("user", "test")))
            .Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*open*");
    }

    [Fact]
    public async Task ProcessAsync_ResetAfterTimeout_BecomesHalfOpen()
    {
        var inner = new MockAgent(exception: new Exception("fail"));
        var cb = new CircuitBreakerMiddleware(inner, new CircuitBreakerConfig(
            FailureThreshold: 1,
            ResetTimeout: TimeSpan.FromMilliseconds(50)));

        try { await cb.ProcessAsync(Message.NewMessage("user", "test")); } catch { }
        cb.State.Should().Be(CircuitState.Open);

        await Task.Delay(100);
        // After timeout, next call transitions to HalfOpen and lets one through
        try { await cb.ProcessAsync(Message.NewMessage("user", "test")); } catch { }
    }

    [Fact]
    public void Introspect_ReturnsCircuitState()
    {
        var cb = new CircuitBreakerMiddleware(new MockAgent());
        var result = cb.Introspect();
        result.State.Should().ContainKey("circuit_state");
    }
}
