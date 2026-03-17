using Agenkit.Core;
using Agenkit.Middleware;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Middleware;

public class RetryMiddlewareTests
{
    [Fact]
    public async Task ProcessAsync_SuccessOnFirstTry_CallsOnce()
    {
        var inner = new MockAgent("ok");
        var middleware = new RetryMiddleware(inner, new RetryConfig(MaxAttempts: 3, InitialDelay: TimeSpan.Zero));
        await middleware.ProcessAsync(Message.NewMessage("user", "test"));
        inner.CallCount.Should().Be(1);
    }

    [Fact]
    public async Task ProcessAsync_FailsThenSucceeds_RetriesUntilSuccess()
    {
        var attempts = 0;
        var inner = new DynamicAgent(() =>
        {
            attempts++;
            if (attempts < 3) throw new Exception("transient");
            return Message.NewMessage("assistant", "ok");
        });
        var middleware = new RetryMiddleware(inner, new RetryConfig(MaxAttempts: 5, InitialDelay: TimeSpan.Zero));
        var response = await middleware.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("ok");
        attempts.Should().Be(3);
    }

    [Fact]
    public async Task ProcessAsync_AllAttemptsFail_ThrowsLastException()
    {
        var inner = new MockAgent(exception: new InvalidOperationException("permanent failure"));
        var middleware = new RetryMiddleware(inner, new RetryConfig(MaxAttempts: 3, InitialDelay: TimeSpan.Zero));

        await middleware.Invoking(m => m.ProcessAsync(Message.NewMessage("user", "test")))
            .Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("permanent failure");
        inner.CallCount.Should().Be(3);
    }

    [Fact]
    public async Task ProcessAsync_CancellationToken_HonoursCancellation()
    {
        var inner = new MockAgent(exception: new Exception("fail"));
        var middleware = new RetryMiddleware(inner, new RetryConfig(MaxAttempts: 10, InitialDelay: TimeSpan.FromSeconds(1)));
        using var cts = new CancellationTokenSource(50);

        await middleware.Invoking(m => m.ProcessAsync(Message.NewMessage("user", "test"), cts.Token))
            .Should().ThrowAsync<Exception>();
    }

    [Fact]
    public void Name_DelegatesToInner()
    {
        var inner = new MockAgent();
        var middleware = new RetryMiddleware(inner);
        middleware.Name.Should().Be(inner.Name);
    }

    private class DynamicAgent : IAgent
    {
        private readonly Func<Message> _fn;
        public DynamicAgent(Func<Message> fn) => _fn = fn;
        public string Name => "DynamicAgent";
        public IReadOnlyList<string> Capabilities => Array.Empty<string>();
        public Task<Message> ProcessAsync(Message message, CancellationToken ct = default) =>
            Task.FromResult(_fn());
        public IntrospectionResult Introspect() => new(Name, Capabilities);
    }
}
