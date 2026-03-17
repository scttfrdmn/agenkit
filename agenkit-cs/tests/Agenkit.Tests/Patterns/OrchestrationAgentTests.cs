using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class OrchestrationAgentTests
{
    [Fact]
    public async Task Sequential_PassesOutputToNext()
    {
        var config = new OrchestrationAgentConfig(
            new IAgent[] { new MockAgent("step1"), new MockAgent("step2") },
            OrchestrationMode.Sequential);
        var agent = new OrchestrationAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "start"));
        response.ContentString().Should().Be("step2");
    }

    [Fact]
    public async Task Parallel_CombinesResults()
    {
        var config = new OrchestrationAgentConfig(
            new IAgent[] { new MockAgent("a"), new MockAgent("b") },
            OrchestrationMode.Parallel);
        var agent = new OrchestrationAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Contain("a");
        response.ContentString().Should().Contain("b");
    }

    [Fact]
    public async Task Router_RoutesToSelectedAgent()
    {
        var config = new OrchestrationAgentConfig(
            new IAgent[] { new MockAgent("agent0"), new MockAgent("agent1") },
            OrchestrationMode.Router,
            RouterFn: _ => 1);
        var agent = new OrchestrationAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("agent1");
    }

    [Fact]
    public void Constructor_RouterWithoutFn_Throws()
    {
        var act = () => new OrchestrationAgent(new OrchestrationAgentConfig(
            new IAgent[] { new MockAgent() },
            OrchestrationMode.Router));
        act.Should().Throw<ArgumentException>().WithMessage("*RouterFn*");
    }

    [Fact]
    public void Constructor_EmptyAgents_Throws()
    {
        var act = () => new OrchestrationAgent(new OrchestrationAgentConfig(new List<IAgent>()));
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void Introspect_ReturnsMode()
    {
        var config = new OrchestrationAgentConfig(new IAgent[] { new MockAgent() });
        var agent = new OrchestrationAgent(config);
        agent.Introspect().State!["mode"].Should().Be("Sequential");
    }
}
