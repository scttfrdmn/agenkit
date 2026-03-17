using Agenkit.Core;
using Agenkit.Middleware;
using Agenkit.Tests.Helpers;

namespace Agenkit.Tests.Middleware;

public class MetricsMiddlewareTests
{
    [Fact]
    public async Task ProcessAsync_Success_IncreasesRequestCount()
    {
        var inner = new MockAgent("ok");
        var metrics = new MetricsMiddleware(inner);
        await metrics.ProcessAsync(Message.NewMessage("user", "test"));
        metrics.TotalRequests.Should().Be(1);
        metrics.TotalErrors.Should().Be(0);
    }

    [Fact]
    public async Task ProcessAsync_Failure_IncreasesErrorCount()
    {
        var inner = new MockAgent(exception: new Exception("fail"));
        var metrics = new MetricsMiddleware(inner);

        try { await metrics.ProcessAsync(Message.NewMessage("user", "test")); }
        catch { /* expected */ }

        metrics.TotalErrors.Should().Be(1);
    }

    [Fact]
    public async Task AverageLatencyMs_AfterRequests_IsComputed()
    {
        var inner = new MockAgent("ok");
        var metrics = new MetricsMiddleware(inner);
        await metrics.ProcessAsync(Message.NewMessage("user", "a"));
        await metrics.ProcessAsync(Message.NewMessage("user", "b"));
        metrics.AverageLatencyMs.Should().BeGreaterThanOrEqualTo(0);
    }

    [Fact]
    public async Task Reset_ClearsCounters()
    {
        var inner = new MockAgent("ok");
        var metrics = new MetricsMiddleware(inner);
        await metrics.ProcessAsync(Message.NewMessage("user", "t"));
        metrics.Reset();
        metrics.TotalRequests.Should().Be(0);
    }

    [Fact]
    public void Introspect_ReturnsMetrics()
    {
        var metrics = new MetricsMiddleware(new MockAgent());
        var result = metrics.Introspect();
        result.State.Should().ContainKey("total_requests");
    }

    [Fact]
    public void Name_DelegatesToInner()
    {
        var inner = new MockAgent();
        var metrics = new MetricsMiddleware(inner);
        metrics.Name.Should().Be(inner.Name);
    }
}
