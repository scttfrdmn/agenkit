using Agenkit.Core;
using FluentAssertions;

namespace Agenkit.Tests.Core;

public class IntrospectionTests
{
    [Fact]
    public void IntrospectionResult_StoresFields()
    {
        var caps = new[] { "cap1", "cap2" };
        var mem = new Dictionary<string, object> { ["k"] = "v" };
        var state = new Dictionary<string, object> { ["count"] = 5 };
        var tools = new[] { "tool1" };

        var result = new IntrospectionResult("TestAgent", caps, mem, state, tools);

        result.AgentName.Should().Be("TestAgent");
        result.Capabilities.Should().BeEquivalentTo(caps);
        result.Memory.Should().ContainKey("k");
        result.State.Should().ContainKey("count");
        result.Tools.Should().Contain("tool1");
    }

    [Fact]
    public void IntrospectionResult_MinimalConstructor()
    {
        var result = new IntrospectionResult("Agent", new[] { "cap" });
        result.Memory.Should().BeNull();
        result.State.Should().BeNull();
        result.Tools.Should().BeNull();
    }
}
