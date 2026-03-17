using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class CollaborativeAgentTests
{
    [Fact]
    public void Constructor_RequiresAtLeastTwoPeers()
    {
        var config = new CollaborativeAgentConfig(new[] { new MockAgent() });
        var act = () => new CollaborativeAgent(config);
        act.Should().Throw<ArgumentException>().WithMessage("*two peers*");
    }

    [Fact]
    public async Task ProcessAsync_WithTwoPeers_ReturnsResponse()
    {
        var config = new CollaborativeAgentConfig(new IAgent[] { new MockAgent("resp1"), new MockAgent("resp2") });
        var agent = new CollaborativeAgent(config);
        var response = await agent.ProcessAsync(Message.NewMessage("user", "question"));
        response.ContentString().Should().NotBeNullOrEmpty();
    }

    [Fact]
    public async Task ProcessAsync_AddsMetadata()
    {
        var config = new CollaborativeAgentConfig(new IAgent[] { new MockAgent(), new MockAgent() });
        var agent = new CollaborativeAgent(config);
        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.Metadata.Should().ContainKey("peer_count");
    }

    [Fact]
    public void Introspect_ReturnsPeerCount()
    {
        var config = new CollaborativeAgentConfig(new IAgent[] { new MockAgent(), new MockAgent(), new MockAgent() });
        var agent = new CollaborativeAgent(config);
        var result = agent.Introspect();
        result.State!["peer_count"].Should().Be(3);
    }

    [Fact]
    public async Task ProcessAsync_MultipleRounds_CallsAllPeers()
    {
        var peer1 = new MockAgent("p1");
        var peer2 = new MockAgent("p2");
        var config = new CollaborativeAgentConfig(new IAgent[] { peer1, peer2 }, Rounds: 2);
        var agent = new CollaborativeAgent(config);

        await agent.ProcessAsync(Message.NewMessage("user", "test"));
        // Each peer called once per round
        (peer1.CallCount + peer2.CallCount).Should().BeGreaterThanOrEqualTo(4);
    }
}
