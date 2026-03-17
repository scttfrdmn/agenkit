using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class ReflectionAgentTests
{
    [Fact]
    public void Constructor_WithValidConfig_Succeeds()
    {
        var config = new ReflectionAgentConfig(new MockLlmClient(), MaxReflections: 1);
        var agent = new ReflectionAgent(config);
        agent.Name.Should().Be("ReflectionAgent");
        agent.Capabilities.Should().Contain("reflection");
    }

    [Fact]
    public async Task ProcessAsync_ReturnsAssistantMessage()
    {
        var agent = new ReflectionAgent(new ReflectionAgentConfig(new MockLlmClient("good answer")));
        var response = await agent.ProcessAsync(Message.NewMessage("user", "what is AI?"));
        response.Role.Should().Be("assistant");
    }

    [Fact]
    public async Task ProcessAsync_AddsReflectionCountMetadata()
    {
        var config = new ReflectionAgentConfig(new MockLlmClient(), MaxReflections: 2);
        var agent = new ReflectionAgent(config);
        var response = await agent.ProcessAsync(Message.NewMessage("user", "question"));
        response.Metadata.Should().ContainKey("reflection_count");
        ((int)response.Metadata!["reflection_count"]).Should().Be(2);
    }

    [Fact]
    public void Introspect_ReturnsState()
    {
        var agent = new ReflectionAgent(new ReflectionAgentConfig(new MockLlmClient()));
        var result = agent.Introspect();
        result.State.Should().ContainKey("last_reflection_count");
    }

    [Fact]
    public async Task ProcessAsync_WithZeroReflections_CallsLlmOnce()
    {
        var llm = new MockLlmClient();
        var config = new ReflectionAgentConfig(llm, MaxReflections: 0);
        var agent = new ReflectionAgent(config);
        await agent.ProcessAsync(Message.NewMessage("user", "test"));
        // 0 reflections => only initial call
        llm.CallCount.Should().Be(1);
    }
}
