using Agenkit.Core;
using FluentAssertions;

namespace Agenkit.Tests.Core;

public class ToolResultTests
{
    [Fact]
    public void Ok_CreatesSuccessfulResult()
    {
        var result = ToolResult.Ok("data");
        result.Success.Should().BeTrue();
        result.Data.Should().Be("data");
        result.Error.Should().BeNull();
    }

    [Fact]
    public void Fail_CreatesFailedResult()
    {
        var result = ToolResult.Fail("something went wrong");
        result.Success.Should().BeFalse();
        result.Error.Should().Be("something went wrong");
        result.Data.Should().BeNull();
    }

    [Fact]
    public void WithMetadata_AddsKey()
    {
        var result = ToolResult.Ok("data").WithMetadata("key", 42);
        result.Metadata.Should().ContainKey("key");
        result.Metadata!["key"].Should().Be(42);
    }

    [Fact]
    public void Ok_WithNullData_Succeeds()
    {
        var result = ToolResult.Ok(null);
        result.Success.Should().BeTrue();
        result.Data.Should().BeNull();
    }
}
