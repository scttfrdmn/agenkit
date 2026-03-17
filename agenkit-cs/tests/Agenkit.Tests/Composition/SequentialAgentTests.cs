using Agenkit.Composition;
using Agenkit.Core;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Composition;

public class SequentialAgentTests
{
    [Fact]
    public void Constructor_EmptyPipeline_Throws()
    {
        var act = () => new SequentialAgent(new List<IAgent>());
        act.Should().Throw<ArgumentException>().WithMessage("*pipeline*");
    }

    [Fact]
    public async Task ProcessAsync_SingleAgent_ReturnsItsResult()
    {
        var agent = new SequentialAgent(new IAgent[] { new MockAgent("result") });
        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("result");
    }

    [Fact]
    public async Task ProcessAsync_ChainOfAgents_PipesOutput()
    {
        // Second agent returns fixed response regardless of input
        var agents = new IAgent[]
        {
            new MockAgent("intermediate"),
            new MockAgent("final")
        };
        var pipeline = new SequentialAgent(agents);
        var response = await pipeline.ProcessAsync(Message.NewMessage("user", "input"));
        response.ContentString().Should().Be("final");
    }

    [Fact]
    public async Task ProcessAsync_EachAgentReceivesPreviousOutput()
    {
        var second = new CapturingAgent();
        var agents = new IAgent[] { new MockAgent("from_first"), second };
        var pipeline = new SequentialAgent(agents);
        await pipeline.ProcessAsync(Message.NewMessage("user", "start"));
        second.GetCaptured().Should().Contain("from_first");
    }

    [Fact]
    public void Introspect_ReturnsPipelineLength()
    {
        var pipeline = new SequentialAgent(new IAgent[] { new MockAgent(), new MockAgent(), new MockAgent() });
        pipeline.Introspect().State!["pipeline_length"].Should().Be(3);
    }

    private class CapturingAgent : IAgent
    {
        private string? _captured;
        public CapturingAgent() { }
        public string Name => "Capturing";
        public IReadOnlyList<string> Capabilities => Array.Empty<string>();
        public Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
        {
            _captured = message.ContentString();
            return Task.FromResult(Message.NewMessage("assistant", "captured"));
        }
        public IntrospectionResult Introspect() => new(Name, Capabilities);
        public string? GetCaptured() => _captured;
    }
}
