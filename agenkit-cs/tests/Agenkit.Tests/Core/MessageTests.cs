using Agenkit.Core;
using FluentAssertions;

namespace Agenkit.Tests.Core;

public class MessageTests
{
    [Fact]
    public void NewMessage_SetsRoleAndContent()
    {
        var msg = Message.NewMessage("user", "hello");
        msg.Role.Should().Be("user");
        msg.ContentString().Should().Be("hello");
    }

    [Fact]
    public void ContentString_NullContent_ReturnsEmpty()
    {
        var msg = new Message("user", null);
        msg.ContentString().Should().Be("");
    }

    [Fact]
    public void ContentString_ObjectContent_ReturnsToString()
    {
        var msg = new Message("user", 42);
        msg.ContentString().Should().Be("42");
    }

    [Fact]
    public void Validate_ValidMessage_ReturnsSelf()
    {
        var msg = Message.NewMessage("user", "hello");
        msg.Validate().Should().Be(msg);
    }

    [Fact]
    public void Validate_EmptyRole_Throws()
    {
        var msg = new Message("", "hello");
        msg.Invoking(m => m.Validate())
            .Should().Throw<ArgumentException>()
            .WithMessage("*role cannot be empty*");
    }

    [Fact]
    public void Validate_InvalidRole_Throws()
    {
        var msg = new Message("badRole", "hello");
        msg.Invoking(m => m.Validate())
            .Should().Throw<ArgumentException>()
            .WithMessage("*invalid message role*");
    }

    [Theory]
    [InlineData("user")]
    [InlineData("assistant")]
    [InlineData("system")]
    [InlineData("tool")]
    [InlineData("agent")]
    public void Validate_AllowedRoles_Passes(string role)
    {
        var msg = new Message(role, "content");
        msg.Invoking(m => m.Validate()).Should().NotThrow();
    }

    [Fact]
    public void WithMetadata_AddsKey()
    {
        var msg = Message.NewMessage("user", "hello");
        var updated = msg.WithMetadata("key", "value");
        updated.Metadata.Should().ContainKey("key");
        updated.Metadata!["key"].Should().Be("value");
    }

    [Fact]
    public void Validate_RoleTooLong_Throws()
    {
        var msg = new Message(new string('a', 21), "hello");
        msg.Invoking(m => m.Validate())
            .Should().Throw<ArgumentException>()
            .WithMessage("*exceeds maximum length*");
    }
}
