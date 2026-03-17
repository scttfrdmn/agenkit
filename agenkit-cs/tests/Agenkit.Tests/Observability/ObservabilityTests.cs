using Agenkit.Core;
using Agenkit.Observability;
using Agenkit.Tests.Helpers;

namespace Agenkit.Tests.Observability;

public class TracingAgentTests
{
    [Fact]
    public async Task ProcessAsync_ForwardsToInner()
    {
        var inner = new MockAgent("traced response");
        var agent = new TracingAgent(inner);
        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("traced response");
    }

    [Fact]
    public void Name_DelegatesToInner()
    {
        var inner = new MockAgent();
        var agent = new TracingAgent(inner);
        agent.Name.Should().Be(inner.Name);
    }

    [Fact]
    public void Introspect_DelegatesToInner()
    {
        var inner = new MockAgent();
        var agent = new TracingAgent(inner);
        agent.Introspect().AgentName.Should().Be(inner.Name);
    }

    [Fact]
    public async Task ProcessAsync_WhenInnerThrows_PropagatesException()
    {
        var inner = new MockAgent(exception: new InvalidOperationException("inner error"));
        var agent = new TracingAgent(inner);

        await agent.Invoking(a => a.ProcessAsync(Message.NewMessage("user", "test")))
            .Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("inner error");
    }
}

public class MetricsCollectorTests
{
    [Fact]
    public void RecordSuccess_IncreasesRequestCount()
    {
        var collector = new MetricsCollector();
        collector.RecordSuccess("agent1", TimeSpan.FromMilliseconds(100));
        collector.GetMetrics("agent1")!.TotalRequests.Should().Be(1);
    }

    [Fact]
    public void RecordError_IncreasesErrorCount()
    {
        var collector = new MetricsCollector();
        collector.RecordError("agent1");
        collector.GetMetrics("agent1")!.TotalErrors.Should().Be(1);
    }

    [Fact]
    public void GetAllMetrics_ReturnsAllAgents()
    {
        var collector = new MetricsCollector();
        collector.RecordSuccess("a", TimeSpan.FromMilliseconds(10));
        collector.RecordSuccess("b", TimeSpan.FromMilliseconds(20));
        collector.GetAllMetrics().Should().ContainKey("a").And.ContainKey("b");
    }

    [Fact]
    public void Reset_ClearsMetrics()
    {
        var collector = new MetricsCollector();
        collector.RecordSuccess("a", TimeSpan.FromMilliseconds(10));
        collector.Reset();
        collector.GetMetrics("a").Should().BeNull();
    }

    [Fact]
    public void AverageLatencyMs_ComputedCorrectly()
    {
        var collector = new MetricsCollector();
        collector.RecordSuccess("a", TimeSpan.FromMilliseconds(100));
        collector.RecordSuccess("a", TimeSpan.FromMilliseconds(200));
        collector.GetMetrics("a")!.AverageLatencyMs.Should().Be(150);
    }
}
