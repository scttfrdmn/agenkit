using Agenkit.Composition;
using Agenkit.Core;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Composition;

public class ParallelAgentTests
{
    [Fact]
    public void Constructor_EmptyAgents_Throws()
    {
        var act = () => new ParallelAgent(new List<IAgent>());
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public async Task ProcessAsync_RunsAllAgents()
    {
        var a = new MockAgent("a");
        var b = new MockAgent("b");
        var parallel = new ParallelAgent(new IAgent[] { a, b });

        await parallel.ProcessAsync(Message.NewMessage("user", "test"));
        a.CallCount.Should().Be(1);
        b.CallCount.Should().Be(1);
    }

    [Fact]
    public async Task ProcessAsync_DefaultAggregator_CombinesResults()
    {
        var parallel = new ParallelAgent(new IAgent[] { new MockAgent("A"), new MockAgent("B") });
        var response = await parallel.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Contain("A");
        response.ContentString().Should().Contain("B");
    }

    [Fact]
    public async Task ProcessAsync_CustomAggregator_UsesIt()
    {
        var parallel = new ParallelAgent(
            new IAgent[] { new MockAgent("x"), new MockAgent("y") },
            results => Message.NewMessage("assistant", string.Join(",", results.Select(r => r.ContentString()))));

        var response = await parallel.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("x,y");
    }

    [Fact]
    public void Introspect_ReturnsAgentCount()
    {
        var parallel = new ParallelAgent(new IAgent[] { new MockAgent(), new MockAgent() });
        parallel.Introspect().State!["agent_count"].Should().Be(2);
    }
}
