using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class RouterAgentTests
{
    private static RouterAgent MakeRouter(IAgent? defaultAgent = null)
    {
        var routes = new Dictionary<string, IAgent>
        {
            ["math"] = new MockAgent("math result"),
            ["text"] = new MockAgent("text result")
        };

        return new RouterAgent(
            m => m.ContentString().Contains("number") ? "math" : "text",
            routes,
            defaultAgent);
    }

    [Fact]
    public void Constructor_WithValidConfig_Succeeds()
    {
        var agent = MakeRouter();
        agent.Name.Should().Be("RouterAgent");
        agent.Capabilities.Should().Contain("routing");
    }

    [Fact]
    public async Task ProcessAsync_RoutesToMath_WhenNumberInMessage()
    {
        var agent = MakeRouter();
        var response = await agent.ProcessAsync(Message.NewMessage("user", "add two numbers"));
        response.ContentString().Should().Be("math result");
    }

    [Fact]
    public async Task ProcessAsync_RoutesToText_WhenNoNumber()
    {
        var agent = MakeRouter();
        var response = await agent.ProcessAsync(Message.NewMessage("user", "tell me a joke"));
        response.ContentString().Should().Be("text result");
    }

    [Fact]
    public async Task ProcessAsync_UsesDefaultWhenNoRoute()
    {
        var routes = new Dictionary<string, IAgent> { ["known"] = new MockAgent("known") };
        var defaultAgent = new MockAgent("default");
        var agent = new RouterAgent(m => "unknown", routes, defaultAgent);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("default");
    }

    [Fact]
    public async Task ProcessAsync_ThrowsWhenNoRouteAndNoDefault()
    {
        var routes = new Dictionary<string, IAgent> { ["known"] = new MockAgent() };
        var agent = new RouterAgent(m => "unknown", routes);

        await agent.Invoking(a => a.ProcessAsync(Message.NewMessage("user", "test")))
            .Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*No route found*");
    }

    [Fact]
    public void Constructor_RequiresAtLeastOneRoute()
    {
        var act = () => new RouterAgent(m => "key", new Dictionary<string, IAgent>());
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void Introspect_ReturnsRouteList()
    {
        var agent = MakeRouter();
        var result = agent.Introspect();
        result.State.Should().ContainKey("routes");
    }
}
