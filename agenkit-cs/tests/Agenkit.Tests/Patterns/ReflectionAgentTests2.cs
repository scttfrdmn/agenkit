// Additional reflection tests
using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;

namespace Agenkit.Tests.Patterns;

public class ReflectionAgentTests2
{
    [Fact]
    public void Name_IsReflectionAgent()
    {
        var agent = new ReflectionAgent(new ReflectionAgentConfig(new MockLlmClient()));
        agent.Name.Should().Be("ReflectionAgent");
    }

    [Fact]
    public async Task ProcessAsync_WithMultipleReflections_ProducesRefinedResponse()
    {
        var llm = new MockLlmClient(new[] { "initial", "critique", "refined1", "critique2", "refined2" });
        var agent = new ReflectionAgent(new ReflectionAgentConfig(llm, MaxReflections: 2));
        var response = await agent.ProcessAsync(Message.NewMessage("user", "question"));
        response.Role.Should().Be("assistant");
    }

    [Fact]
    public async Task ProcessAsync_WithNegativeMaxReflections_DefaultsToTwo()
    {
        var llm = new MockLlmClient();
        var agent = new ReflectionAgent(new ReflectionAgentConfig(llm, MaxReflections: -1));
        await agent.ProcessAsync(Message.NewMessage("user", "test"));
        // -1 defaults to 2 reflections = 1 initial + 2*(2 calls) = 5 calls
        llm.CallCount.Should().Be(5);
    }
}
