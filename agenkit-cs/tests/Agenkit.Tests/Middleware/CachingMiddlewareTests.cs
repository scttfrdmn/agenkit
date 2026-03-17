using Agenkit.Core;
using Agenkit.Middleware;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Middleware;

public class CachingMiddlewareTests
{
    [Fact]
    public async Task ProcessAsync_CachesResponse()
    {
        var inner = new MockAgent("original");
        var cache = new CachingMiddleware(inner);

        var r1 = await cache.ProcessAsync(Message.NewMessage("user", "hello"));
        var r2 = await cache.ProcessAsync(Message.NewMessage("user", "hello"));

        r1.ContentString().Should().Be("original");
        r2.ContentString().Should().Be("original");
        inner.CallCount.Should().Be(1); // only called once
    }

    [Fact]
    public async Task ProcessAsync_DifferentMessages_CachedSeparately()
    {
        var inner = new MockAgent(new[] { "resp1", "resp2" });
        var cache = new CachingMiddleware(inner);

        var r1 = await cache.ProcessAsync(Message.NewMessage("user", "msg1"));
        var r2 = await cache.ProcessAsync(Message.NewMessage("user", "msg2"));

        r1.ContentString().Should().Be("resp1");
        r2.ContentString().Should().Be("resp2");
        inner.CallCount.Should().Be(2);
    }

    [Fact]
    public async Task ProcessAsync_ExpiredEntry_FetchesFresh()
    {
        var inner = new MockAgent(new[] { "first", "second" });
        var cache = new CachingMiddleware(inner, new CachingConfig(Ttl: TimeSpan.FromMilliseconds(50)));

        var r1 = await cache.ProcessAsync(Message.NewMessage("user", "test"));
        await Task.Delay(100);
        var r2 = await cache.ProcessAsync(Message.NewMessage("user", "test"));

        r1.ContentString().Should().Be("first");
        r2.ContentString().Should().Be("second");
        inner.CallCount.Should().Be(2);
    }

    [Fact]
    public async Task ProcessAsync_CacheHit_AddsMetadata()
    {
        var cache = new CachingMiddleware(new MockAgent("x"));
        await cache.ProcessAsync(Message.NewMessage("user", "test"));
        var r2 = await cache.ProcessAsync(Message.NewMessage("user", "test"));
        r2.Metadata.Should().ContainKey("cache_hit");
    }

    [Fact]
    public void InvalidateAll_ClearsCacheSize()
    {
        var cache = new CachingMiddleware(new MockAgent("r"));
        cache.CacheSize.Should().Be(0);
        cache.InvalidateAll();
        cache.CacheSize.Should().Be(0);
    }
}
