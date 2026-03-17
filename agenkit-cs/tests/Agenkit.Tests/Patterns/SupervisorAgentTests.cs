using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class SupervisorAgentTests
{
    [Fact]
    public void Constructor_RequiresAtLeastOneSpecialist()
    {
        var planner = new SimplePlanner(new MockAgent());
        var act = () => new SupervisorAgent(planner, new Dictionary<string, IAgent>());
        act.Should().Throw<ArgumentException>().WithMessage("*specialist*");
    }

    [Fact]
    public async Task ProcessAsync_WithSimplePlanner_DelegatesToPlanner()
    {
        var inner = new MockAgent("planner response");
        var planner = new SimplePlanner(inner);
        var specialists = new Dictionary<string, IAgent> { ["spec"] = new MockAgent("specialist result") };
        var supervisor = new SupervisorAgent(planner, specialists);

        var response = await supervisor.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Contain("planner response");
    }

    [Fact]
    public void Introspect_ReturnsSpecialistCount()
    {
        var planner = new SimplePlanner(new MockAgent());
        var specialists = new Dictionary<string, IAgent>
        {
            ["a"] = new MockAgent(),
            ["b"] = new MockAgent()
        };
        var supervisor = new SupervisorAgent(planner, specialists);
        var result = supervisor.Introspect();
        result.State!["specialist_count"].Should().Be(2);
    }

    [Fact]
    public void SimplePlanner_Name_IsSimplePlanner()
    {
        var planner = new SimplePlanner(new MockAgent());
        planner.Name.Should().Be("SimplePlanner");
    }

    [Fact]
    public async Task SimplePlanner_PlanAsync_ReturnsEmpty()
    {
        var planner = new SimplePlanner(new MockAgent());
        var result = await planner.PlanAsync(Message.NewMessage("user", "test"));
        result.Should().BeEmpty();
    }

    [Fact]
    public async Task SupervisorAgent_WithUnknownSpecialistType_Throws()
    {
        var customPlanner = new DummyPlanner(new[] { new Subtask("unknown", Message.NewMessage("user", "x")) });
        var specialists = new Dictionary<string, IAgent> { ["known"] = new MockAgent() };
        var supervisor = new SupervisorAgent(customPlanner, specialists);

        await supervisor.Invoking(s => s.ProcessAsync(Message.NewMessage("user", "test")))
            .Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*unknown specialist type*");
    }

    private class DummyPlanner : IPlannerAgent
    {
        private readonly IReadOnlyList<Subtask> _subtasks;
        public DummyPlanner(IReadOnlyList<Subtask> subtasks) => _subtasks = subtasks;
        public string Name => "DummyPlanner";
        public IReadOnlyList<string> Capabilities => Array.Empty<string>();
        public Task<Message> ProcessAsync(Message message, CancellationToken ct = default) =>
            Task.FromResult(Message.NewMessage("assistant", "done"));
        public Task<IReadOnlyList<Subtask>> PlanAsync(Message message, CancellationToken ct = default) =>
            Task.FromResult(_subtasks);
        public Task<Message> SynthesizeAsync(Message original, IReadOnlyDictionary<string, Message> results, CancellationToken ct = default) =>
            Task.FromResult(Message.NewMessage("assistant", "synthesized"));
        public IntrospectionResult Introspect() => new(Name, Capabilities);
    }
}
