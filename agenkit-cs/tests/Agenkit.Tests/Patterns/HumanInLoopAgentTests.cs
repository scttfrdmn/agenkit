using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class HumanInLoopAgentTests
{
    [Fact]
    public async Task ProcessAsync_WhenApproved_ForwardsToInner()
    {
        var inner = new MockAgent("inner response");
        var config = new HumanInLoopAgentConfig(
            inner,
            _ => Task.FromResult(new ApprovalResponse(true)));
        var agent = new HumanInLoopAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("inner response");
    }

    [Fact]
    public async Task ProcessAsync_WhenDenied_ReturnsDeniedMessage()
    {
        var inner = new MockAgent("should not reach");
        var config = new HumanInLoopAgentConfig(
            inner,
            _ => Task.FromResult(new ApprovalResponse(false, "not allowed")));
        var agent = new HumanInLoopAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Contain("not allowed");
        inner.CallCount.Should().Be(0);
    }

    [Fact]
    public async Task ProcessAsync_Approved_AddsApprovedMetadata()
    {
        var config = new HumanInLoopAgentConfig(
            new MockAgent(),
            _ => Task.FromResult(new ApprovalResponse(true)));
        var agent = new HumanInLoopAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.Metadata.Should().ContainKey("human_approved");
    }

    [Fact]
    public void Introspect_IncludesCapabilities()
    {
        var config = new HumanInLoopAgentConfig(new MockAgent(), _ => Task.FromResult(new ApprovalResponse(true)));
        var agent = new HumanInLoopAgent(config);
        agent.Capabilities.Should().Contain("human-in-loop");
    }

    [Fact]
    public void Constructor_WithNullConfig_Throws()
    {
        var act = () => new HumanInLoopAgent(null!);
        act.Should().Throw<ArgumentNullException>();
    }
}
