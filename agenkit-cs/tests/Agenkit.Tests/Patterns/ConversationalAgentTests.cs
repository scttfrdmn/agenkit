using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class ConversationalAgentTests
{
    private readonly MockLlmClient _mockClient = new("hello back");
    private ConversationalAgentConfig DefaultConfig => new(_mockClient);

    [Fact]
    public void Constructor_WithValidConfig_CreatesAgent()
    {
        var agent = new ConversationalAgent(DefaultConfig);
        agent.Name.Should().Be("ConversationalAgent");
        agent.Capabilities.Should().Contain("conversational");
    }

    [Fact]
    public async Task ProcessAsync_SingleMessage_ReturnsResponse()
    {
        var agent = new ConversationalAgent(DefaultConfig);
        var response = await agent.ProcessAsync(Message.NewMessage("user", "Hello"));
        response.Role.Should().Be("assistant");
        response.ContentString().Should().Be("hello back");
    }

    [Fact]
    public async Task ProcessAsync_BuildsHistory()
    {
        var agent = new ConversationalAgent(DefaultConfig);
        await agent.ProcessAsync(Message.NewMessage("user", "First"));
        await agent.ProcessAsync(Message.NewMessage("user", "Second"));
        agent.GetHistory().Count.Should().BeGreaterThan(2);
    }

    [Fact]
    public void Constructor_WithSystemPrompt_AddsToHistory()
    {
        var agent = new ConversationalAgent(new ConversationalAgentConfig(_mockClient, SystemPrompt: "Be helpful."));
        var history = agent.GetHistory();
        history.Should().ContainSingle(m => m.Role == "system");
    }

    [Fact]
    public async Task ClearHistory_RemovesMessages()
    {
        var agent = new ConversationalAgent(DefaultConfig);
        await agent.ProcessAsync(Message.NewMessage("user", "Hello"));
        agent.ClearHistory();
        agent.GetHistory().Should().BeEmpty();
    }

    [Fact]
    public async Task ClearHistory_KeepSystem_RetainsSystemMessage()
    {
        var agent = new ConversationalAgent(new ConversationalAgentConfig(_mockClient, SystemPrompt: "System."));
        await agent.ProcessAsync(Message.NewMessage("user", "Hello"));
        agent.ClearHistory(keepSystem: true);
        agent.GetHistory().Should().ContainSingle(m => m.Role == "system");
    }

    [Fact]
    public void Introspect_ReturnsState()
    {
        var agent = new ConversationalAgent(DefaultConfig);
        var result = agent.Introspect();
        result.AgentName.Should().Be("ConversationalAgent");
        result.State.Should().ContainKey("history_count");
    }

    [Fact]
    public async Task PrunesHistory_WhenExceedsMax()
    {
        var agent = new ConversationalAgent(new ConversationalAgentConfig(_mockClient, MaxHistory: 4));
        for (int i = 0; i < 10; i++)
            await agent.ProcessAsync(Message.NewMessage("user", $"msg {i}"));
        agent.GetHistory().Count.Should().BeLessThanOrEqualTo(4);
    }
}
