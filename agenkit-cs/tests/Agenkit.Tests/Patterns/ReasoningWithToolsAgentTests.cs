using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class ReasoningWithToolsAgentTests
{
    [Fact]
    public async Task ProcessAsync_WithNoToolCall_ReturnsDirectly()
    {
        var inner = new MockAgent("final answer here");
        var config = new ReasoningWithToolsAgentConfig(inner, new ITool[] { new MockTool("calc") });
        var agent = new ReasoningWithToolsAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("final answer here");
    }

    [Fact]
    public async Task ProcessAsync_WithToolCall_ExecutesTool()
    {
        var inner = new MockAgent(new[] { "USE_TOOL: calc(2+2)", "got 4" });
        var tool = new MockTool("calc", "4");
        var config = new ReasoningWithToolsAgentConfig(inner, new ITool[] { tool });
        var agent = new ReasoningWithToolsAgent(config);

        await agent.ProcessAsync(Message.NewMessage("user", "compute"));
        tool.CallCount.Should().Be(1);
    }

    [Fact]
    public void Constructor_Capabilities_ContainsInterleaved()
    {
        var config = new ReasoningWithToolsAgentConfig(new MockAgent(), new ITool[] { new MockTool("t") });
        var agent = new ReasoningWithToolsAgent(config);
        agent.Capabilities.Should().Contain("interleaved");
    }

    [Fact]
    public async Task ProcessAsync_AddsToolCallsMetadata()
    {
        var inner = new MockAgent("no tool call");
        var config = new ReasoningWithToolsAgentConfig(inner, new ITool[] { new MockTool("t") });
        var agent = new ReasoningWithToolsAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.Metadata.Should().ContainKey("tool_calls");
    }
}
