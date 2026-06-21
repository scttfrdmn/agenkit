using Agenkit.Adapters;
using Agenkit.Core;

namespace Agenkit.Tests.Adapters;

public class TokenUsageTests
{
    private static Message MsgWith(Dictionary<string, object> usage) =>
        Message.NewMessage("assistant", "hi").WithMetadata("usage", usage);

    [Fact]
    public void FromMessage_NullWhenNoUsage()
    {
        TokenUsage.FromMessage(null).Should().BeNull();
        TokenUsage.FromMessage(Message.NewMessage("assistant", "hi")).Should().BeNull();
    }

    [Fact]
    public void FromMessage_PromptCompletionConvention()
    {
        var u = TokenUsage.FromMessage(MsgWith(new()
        {
            ["prompt_tokens"] = 10, ["completion_tokens"] = 5, ["total_tokens"] = 15
        }));
        u.Should().NotBeNull();
        u!.PromptTokens.Should().Be(10);
        u.CompletionTokens.Should().Be(5);
        u.TotalTokens.Should().Be(15);
    }

    [Fact]
    public void FromMessage_AnthropicConventionDerivesTotal()
    {
        var u = TokenUsage.FromMessage(MsgWith(new()
        {
            ["input_tokens"] = 30, ["output_tokens"] = 7
        }));
        u.Should().NotBeNull();
        u!.PromptTokens.Should().Be(30);
        u.CompletionTokens.Should().Be(7);
        u.TotalTokens.Should().Be(37);
    }

    [Fact]
    public void FromMessage_NormalizedCacheKeys()
    {
        var u = TokenUsage.FromMessage(MsgWith(new()
        {
            ["prompt_tokens"] = 1000, ["completion_tokens"] = 50, ["total_tokens"] = 1050,
            ["cache_read_tokens"] = 900, ["cache_creation_tokens"] = 100
        }));
        u.Should().NotBeNull();
        u!.CacheReadTokens.Should().Be(900);
        u.CacheCreationTokens.Should().Be(100);
    }

    [Fact]
    public void FromMessage_RawProviderCacheAliases()
    {
        var u = TokenUsage.FromMessage(MsgWith(new()
        {
            ["input_tokens"] = 20, ["output_tokens"] = 4,
            ["cache_read_input_tokens"] = 15, ["cache_creation_input_tokens"] = 5
        }));
        u.Should().Be(new TokenUsage(20, 4, 24, 15, 5));
    }

    [Fact]
    public void FromMessage_IgnoresNonNumeric()
    {
        var u = TokenUsage.FromMessage(MsgWith(new()
        {
            ["prompt_tokens"] = "x", ["completion_tokens"] = 5
        }));
        u.Should().NotBeNull();
        u!.PromptTokens.Should().Be(0);
        u.CompletionTokens.Should().Be(5);
    }
}
