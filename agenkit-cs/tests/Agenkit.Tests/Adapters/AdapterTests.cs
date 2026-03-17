using Agenkit.Adapters;
using Agenkit.Core;

namespace Agenkit.Tests.Adapters;

public class MockAdapterTests
{
    [Fact]
    public async Task ChatAsync_ReturnsMockResponse()
    {
        var adapter = new MockAdapter("hello there");
        var response = await adapter.ChatAsync(new[] { Message.NewMessage("user", "hi") });
        response.ContentString().Should().Be("hello there");
        response.Role.Should().Be("assistant");
    }

    [Fact]
    public async Task ChatAsync_SequentialResponses_ReturnsInOrder()
    {
        var adapter = new MockAdapter(new[] { "first", "second", "third" });
        var msg = new[] { Message.NewMessage("user", "test") };

        var r1 = await adapter.ChatAsync(msg);
        var r2 = await adapter.ChatAsync(msg);
        var r3 = await adapter.ChatAsync(msg);

        r1.ContentString().Should().Be("first");
        r2.ContentString().Should().Be("second");
        r3.ContentString().Should().Be("third");
    }

    [Fact]
    public async Task ChatAsync_AfterSequenceExhausted_ReturnsFallback()
    {
        var adapter = new MockAdapter(new[] { "only" });
        var msg = new[] { Message.NewMessage("user", "test") };

        await adapter.ChatAsync(msg); // "only"
        var r2 = await adapter.ChatAsync(msg); // falls back to ""
        r2.ContentString().Should().Be("");
    }

    [Fact]
    public async Task ChatAsync_TracksCallCount()
    {
        var adapter = new MockAdapter("ok");
        var msg = new[] { Message.NewMessage("user", "t") };
        await adapter.ChatAsync(msg);
        await adapter.ChatAsync(msg);
        adapter.CallCount.Should().Be(2);
    }

    [Fact]
    public async Task ChatAsync_CancelledToken_ThrowsOperationCancelled()
    {
        var adapter = new MockAdapter("ok");
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        await adapter.Invoking(a => a.ChatAsync(new[] { Message.NewMessage("user", "t") }, cts.Token))
            .Should().ThrowAsync<OperationCanceledException>();
    }
}
