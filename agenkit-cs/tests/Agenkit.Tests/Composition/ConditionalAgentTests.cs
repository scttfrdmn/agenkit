using Agenkit.Composition;
using Agenkit.Core;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Composition;

public class ConditionalAgentTests
{
    private static ConditionalAgent MakeAgent(string trueResp = "true branch", string falseResp = "false branch")
    {
        return new ConditionalAgent(
            m => m.ContentString().Contains("yes"),
            new MockAgent(trueResp),
            new MockAgent(falseResp));
    }

    [Fact]
    public async Task ProcessAsync_ConditionTrue_RoutesToTrueBranch()
    {
        var agent = MakeAgent();
        var response = await agent.ProcessAsync(Message.NewMessage("user", "yes please"));
        response.ContentString().Should().Be("true branch");
    }

    [Fact]
    public async Task ProcessAsync_ConditionFalse_RoutesToFalseBranch()
    {
        var agent = MakeAgent();
        var response = await agent.ProcessAsync(Message.NewMessage("user", "no thanks"));
        response.ContentString().Should().Be("false branch");
    }

    [Fact]
    public void Introspect_ReturnsBranchNames()
    {
        var agent = MakeAgent();
        var state = agent.Introspect().State!;
        state.Should().ContainKey("true_branch");
        state.Should().ContainKey("false_branch");
    }

    [Fact]
    public async Task ProcessAsync_BothBranches_CallOnlyOne()
    {
        var trueMock = new MockAgent("t");
        var falseMock = new MockAgent("f");
        var agent = new ConditionalAgent(_ => true, trueMock, falseMock);

        await agent.ProcessAsync(Message.NewMessage("user", "test"));
        trueMock.CallCount.Should().Be(1);
        falseMock.CallCount.Should().Be(0);
    }
}
