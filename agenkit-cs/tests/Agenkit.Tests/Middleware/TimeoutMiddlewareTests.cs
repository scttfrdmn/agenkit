using Agenkit.Core;
using Agenkit.Middleware;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Middleware;

public class TimeoutMiddlewareTests
{
    [Fact]
    public async Task ProcessAsync_FastAgent_CompletesSuccessfully()
    {
        var inner = new MockAgent("fast");
        var middleware = new TimeoutMiddleware(inner, TimeSpan.FromSeconds(5));
        var response = await middleware.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("fast");
    }

    [Fact]
    public async Task ProcessAsync_SlowAgent_ThrowsTimeoutException()
    {
        var slow = new SlowAgent(TimeSpan.FromSeconds(10));
        var middleware = new TimeoutMiddleware(slow, TimeSpan.FromMilliseconds(50));

        await middleware.Invoking(m => m.ProcessAsync(Message.NewMessage("user", "test")))
            .Should().ThrowAsync<TimeoutException>()
            .WithMessage("*timed out*");
    }

    [Fact]
    public void Constructor_ZeroTimeout_Throws()
    {
        var act = () => new TimeoutMiddleware(new MockAgent(), TimeSpan.Zero);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void Constructor_NegativeTimeout_Throws()
    {
        var act = () => new TimeoutMiddleware(new MockAgent(), TimeSpan.FromSeconds(-1));
        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void Name_DelegatesToInner()
    {
        var inner = new MockAgent();
        var middleware = new TimeoutMiddleware(inner, TimeSpan.FromSeconds(1));
        middleware.Name.Should().Be(inner.Name);
    }

    private class SlowAgent : IAgent
    {
        private readonly TimeSpan _delay;
        public SlowAgent(TimeSpan delay) => _delay = delay;
        public string Name => "SlowAgent";
        public IReadOnlyList<string> Capabilities => Array.Empty<string>();
        public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
        {
            await Task.Delay(_delay, ct);
            return Message.NewMessage("assistant", "done");
        }
        public IntrospectionResult Introspect() => new(Name, Capabilities);
    }
}
