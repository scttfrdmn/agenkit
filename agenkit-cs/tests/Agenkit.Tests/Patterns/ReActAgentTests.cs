using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class ReActAgentTests
{
    private static ReActConfig MakeConfig(MockAgent agent, params MockTool[] tools) =>
        new(agent, tools.Cast<ITool>().ToList());

    [Fact]
    public void Constructor_RequiresAtLeastOneTool()
    {
        var agent = new MockAgent();
        var act = () => new ReActAgent(new ReActConfig(agent, new List<ITool>()));
        act.Should().Throw<ArgumentException>().WithMessage("*tool*");
    }

    [Fact]
    public async Task ProcessAsync_FinalAnswer_ReturnsFinalContent()
    {
        var inner = new MockAgent("Thought: done\nFinal Answer: 42");
        var config = MakeConfig(inner, new MockTool("calc"));
        var agent = new ReActAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "what is 2+2?"));
        response.ContentString().Should().Be("42");
    }

    [Fact]
    public async Task ProcessAsync_InvalidAction_StopsLoop()
    {
        var inner = new MockAgent("Thought: hmm\n(no action or final answer)");
        var config = MakeConfig(inner, new MockTool("calc"));
        var agent = new ReActAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().NotBeNullOrEmpty();
    }

    [Fact]
    public async Task ProcessAsync_WithToolUse_ExecutesTool()
    {
        // First call uses a tool; second call gives final answer
        var inner = new MockAgent(new[] { "Thought: try calc\nAction: calc\nAction Input: 2+2", "Thought: got it\nFinal Answer: 4" });
        var tool = new MockTool("calc", "4");
        var config = MakeConfig(inner, tool);
        var agent = new ReActAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "what is 2+2?"));
        tool.CallCount.Should().Be(1);
        response.ContentString().Should().Be("4");
    }

    [Fact]
    public async Task GetSteps_ReturnsReasoningHistory()
    {
        var inner = new MockAgent("Thought: done\nFinal Answer: answer");
        var config = MakeConfig(inner, new MockTool("tool"));
        var agent = new ReActAgent(config);

        await agent.ProcessAsync(Message.NewMessage("user", "test"));
        agent.GetSteps().Should().HaveCount(1);
    }

    [Fact]
    public async Task ProcessAsync_MaxSteps_Terminates()
    {
        var inner = new MockAgent("Thought: still thinking\nAction: tool\nAction Input: x");
        var tool = new MockTool("tool");
        var config = new ReActConfig(inner, new ITool[] { tool }, MaxSteps: 3);
        var agent = new ReActAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Contain("Unable to complete");
    }
}
