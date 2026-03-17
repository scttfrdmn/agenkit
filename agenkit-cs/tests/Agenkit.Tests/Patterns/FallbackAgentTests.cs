using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class FallbackAgentTests
{
    [Fact]
    public void Constructor_EmptyChain_Throws()
    {
        var act = () => new FallbackAgent(new FallbackAgentConfig(new List<IAgent>()));
        act.Should().Throw<ArgumentException>().WithMessage("*chain*");
    }

    [Fact]
    public async Task ProcessAsync_FirstSucceeds_ReturnsFirstResult()
    {
        var config = new FallbackAgentConfig(new IAgent[] { new MockAgent("first"), new MockAgent("second") });
        var agent = new FallbackAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("first");
    }

    [Fact]
    public async Task ProcessAsync_FirstFails_FallsBackToSecond()
    {
        var failing = new MockAgent(exception: new Exception("first failed"));
        var working = new MockAgent("second");
        var config = new FallbackAgentConfig(new IAgent[] { failing, working });
        var agent = new FallbackAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("second");
    }

    [Fact]
    public async Task ProcessAsync_AllFail_ThrowsAggregateException()
    {
        var agents = new IAgent[]
        {
            new MockAgent(exception: new Exception("fail1")),
            new MockAgent(exception: new Exception("fail2"))
        };
        var config = new FallbackAgentConfig(agents);
        var agent = new FallbackAgent(config);

        await agent.Invoking(a => a.ProcessAsync(Message.NewMessage("user", "test")))
            .Should().ThrowAsync<AggregateException>()
            .WithMessage("*all agents in fallback chain failed*");
    }

    [Fact]
    public void Introspect_ReturnsChainLength()
    {
        var config = new FallbackAgentConfig(new IAgent[] { new MockAgent(), new MockAgent(), new MockAgent() });
        var agent = new FallbackAgent(config);
        agent.Introspect().State!["chain_length"].Should().Be(3);
    }
}
