using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class AutonomousAgentTests
{
    [Fact]
    public async Task ProcessAsync_WhenGoalMet_ReturnsImmediately()
    {
        var inner = new MockAgent("DONE");
        var config = new AutonomousAgentConfig(inner, m => m.ContentString() == "DONE", MaxIterations: 5);
        var agent = new AutonomousAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "task"));
        response.ContentString().Should().Be("DONE");
        ((bool)response.Metadata!["goal_reached"]).Should().BeTrue();
    }

    [Fact]
    public async Task ProcessAsync_WhenGoalNeverMet_ReturnsAfterMaxIterations()
    {
        var inner = new MockAgent("not done");
        var config = new AutonomousAgentConfig(inner, _ => false, MaxIterations: 3);
        var agent = new AutonomousAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "task"));
        ((bool)response.Metadata!["goal_reached"]).Should().BeFalse();
        ((int)response.Metadata["iterations"]).Should().Be(3);
    }

    [Fact]
    public void Introspect_ReturnsMaxIterations()
    {
        var config = new AutonomousAgentConfig(new MockAgent(), _ => false, MaxIterations: 7);
        var agent = new AutonomousAgent(config);
        agent.Introspect().State!["max_iterations"].Should().Be(7);
    }

    [Fact]
    public async Task ProcessAsync_WithInitialPrompt_PrependsPrompt()
    {
        var inner = new MockAgent("DONE");
        var config = new AutonomousAgentConfig(inner, _ => true, InitialPrompt: "Goal:");
        var agent = new AutonomousAgent(config);

        await agent.ProcessAsync(Message.NewMessage("user", "task"));
        inner.LastMessage!.ContentString().Should().Contain("Goal:");
    }

    [Fact]
    public async Task ProcessAsync_CallsInnerRepeatedly()
    {
        int count = 0;
        var inner = new MockAgent("response");
        var config = new AutonomousAgentConfig(inner, _ => ++count >= 3, MaxIterations: 5);
        var agent = new AutonomousAgent(config);

        await agent.ProcessAsync(Message.NewMessage("user", "task"));
        inner.CallCount.Should().Be(3);
    }
}
