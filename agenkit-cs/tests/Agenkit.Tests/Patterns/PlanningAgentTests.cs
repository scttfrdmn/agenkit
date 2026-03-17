using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class PlanningAgentTests
{
    private static MockLlmClient MakeLlm(string response = "Goal: test\nSteps:\n1. Step one\n2. Step two") =>
        new(response);

    [Fact]
    public void Constructor_WithDefaults_Succeeds()
    {
        var agent = new PlanningAgent(MakeLlm());
        agent.Name.Should().Be("PlanningAgent");
        agent.Capabilities.Should().Contain("planning");
    }

    [Fact]
    public async Task ProcessAsync_ReturnsPlanSummary()
    {
        var agent = new PlanningAgent(MakeLlm());
        var response = await agent.ProcessAsync(Message.NewMessage("user", "plan something"));
        response.ContentString().Should().Contain("Task completed");
    }

    [Fact]
    public async Task GetPlan_AfterProcess_ReturnsPlan()
    {
        var agent = new PlanningAgent(MakeLlm());
        await agent.ProcessAsync(Message.NewMessage("user", "organize team event"));
        agent.GetPlan().Should().NotBeNull();
        agent.GetPlan()!.Steps.Should().HaveCountGreaterThan(0);
    }

    [Fact]
    public async Task GetProgress_AfterCompletion_Returns100()
    {
        var agent = new PlanningAgent(MakeLlm());
        await agent.ProcessAsync(Message.NewMessage("user", "task"));
        agent.GetProgress().Should().Be(100.0);
    }

    [Fact]
    public void Introspect_WithNoPlan_ReturnsDefaults()
    {
        var agent = new PlanningAgent(MakeLlm());
        var result = agent.Introspect();
        result.AgentName.Should().Be("PlanningAgent");
        result.State!["has_plan"].Should().Be(false);
    }

    [Fact]
    public void PlanStep_StatusUpdates()
    {
        var step = new PlanStep { Description = "test", StepNumber = 0 };
        step.Status.Should().Be(StepStatus.Pending);
        step.Status = StepStatus.Completed;
        step.Status.Should().Be(StepStatus.Completed);
    }
}
