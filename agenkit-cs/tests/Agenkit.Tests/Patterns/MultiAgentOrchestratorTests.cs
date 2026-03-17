using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class MultiAgentOrchestratorTests
{
    [Fact]
    public void Constructor_EmptyAgents_Throws()
    {
        var act = () => new MultiAgentOrchestrator(new MultiAgentOrchestratorConfig(new Dictionary<string, IAgent>()));
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public async Task ProcessAsync_ExecutesInOrder_ReturnsFinalAgentResult()
    {
        var agents = new Dictionary<string, IAgent>
        {
            ["a"] = new MockAgent("from_a"),
            ["b"] = new MockAgent("from_b")
        };
        var config = new MultiAgentOrchestratorConfig(agents, new[] { "a", "b" });
        var orchestrator = new MultiAgentOrchestrator(config);

        var response = await orchestrator.ProcessAsync(Message.NewMessage("user", "start"));
        response.ContentString().Should().Be("from_b");
    }

    [Fact]
    public async Task ProcessAsync_AddsAgentCountMetadata()
    {
        var agents = new Dictionary<string, IAgent> { ["x"] = new MockAgent("x") };
        var config = new MultiAgentOrchestratorConfig(agents);
        var orchestrator = new MultiAgentOrchestrator(config);

        var response = await orchestrator.ProcessAsync(Message.NewMessage("user", "test"));
        response.Metadata.Should().ContainKey("agent_count");
    }

    [Fact]
    public void Constructor_InvalidOrderKey_Throws()
    {
        var agents = new Dictionary<string, IAgent> { ["a"] = new MockAgent() };
        var act = () => new MultiAgentOrchestrator(new MultiAgentOrchestratorConfig(agents, new[] { "a", "nonexistent" }));
        act.Should().Throw<ArgumentException>().WithMessage("*nonexistent*");
    }

    [Fact]
    public void Introspect_ReturnsAgentCount()
    {
        var agents = new Dictionary<string, IAgent>
        {
            ["a"] = new MockAgent(),
            ["b"] = new MockAgent(),
            ["c"] = new MockAgent()
        };
        var orchestrator = new MultiAgentOrchestrator(new MultiAgentOrchestratorConfig(agents));
        orchestrator.Introspect().State!["agent_count"].Should().Be(3);
    }
}
