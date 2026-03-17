using Agenkit.Core;
using Agenkit.Memory;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class MemoryAugmentedAgentTests
{
    [Fact]
    public async Task ProcessAsync_StoresMessagesInMemory()
    {
        var memory = new EphemeralMemory();
        var config = new MemoryAugmentedAgentConfig(new MockAgent("resp"), memory);
        var agent = new MemoryAugmentedAgent(config);

        await agent.ProcessAsync(Message.NewMessage("user", "hello"));
        memory.Count.Should().BeGreaterThan(0);
    }

    [Fact]
    public async Task ProcessAsync_ReturnsResponse()
    {
        var memory = new EphemeralMemory();
        var config = new MemoryAugmentedAgentConfig(new MockAgent("answer"), memory);
        var agent = new MemoryAugmentedAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "question"));
        response.ContentString().Should().Be("answer");
    }

    [Fact]
    public void Introspect_ContainsMemoryInfo()
    {
        var memory = new EphemeralMemory();
        var config = new MemoryAugmentedAgentConfig(new MockAgent(), memory);
        var agent = new MemoryAugmentedAgent(config);
        agent.Introspect().Memory.Should().ContainKey("context_messages");
    }

    [Fact]
    public void Name_MatchesExpected()
    {
        var config = new MemoryAugmentedAgentConfig(new MockAgent(), new EphemeralMemory());
        var agent = new MemoryAugmentedAgent(config);
        agent.Name.Should().Be("MemoryAugmentedAgent");
    }

    [Fact]
    public async Task ProcessAsync_MultipleMessages_AugmentsContext()
    {
        var memory = new EphemeralMemory();
        var inner = new MockAgent("response");
        var config = new MemoryAugmentedAgentConfig(inner, memory, ContextMessages: 10);
        var agent = new MemoryAugmentedAgent(config);

        await agent.ProcessAsync(Message.NewMessage("user", "first"));
        await agent.ProcessAsync(Message.NewMessage("user", "second"));

        // Second call should include context from first
        inner.LastMessage!.ContentString().Should().Contain("Recent context");
    }
}
