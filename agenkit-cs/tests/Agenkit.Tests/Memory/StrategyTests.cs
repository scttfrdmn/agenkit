using Agenkit.Core;
using Agenkit.Memory.Strategies;

namespace Agenkit.Tests.Memory;

public class SlidingWindowStrategyTests
{
    [Fact]
    public void Apply_WithinWindow_ReturnsAll()
    {
        var strategy = new SlidingWindowStrategy(10);
        var msgs = Enumerable.Range(0, 5).Select(i => Message.NewMessage("user", $"msg{i}")).ToList();
        var result = strategy.Apply(msgs);
        result.Should().HaveCount(5);
    }

    [Fact]
    public void Apply_ExceedsWindow_ReturnsMostRecent()
    {
        var strategy = new SlidingWindowStrategy(3);
        var msgs = Enumerable.Range(0, 10).Select(i => Message.NewMessage("user", $"msg{i}")).ToList();
        var result = strategy.Apply(msgs);
        result.Should().HaveCount(3);
        result[^1].ContentString().Should().Be("msg9");
    }

    [Fact]
    public void Apply_EmptyList_ReturnsEmpty()
    {
        var strategy = new SlidingWindowStrategy(5);
        var result = strategy.Apply(new List<Message>());
        result.Should().BeEmpty();
    }
}

public class ImportanceWeightingStrategyTests
{
    [Fact]
    public void Apply_ReturnsTopK()
    {
        var strategy = new ImportanceWeightingStrategy(topK: 2);
        var msgs = new List<Message>
        {
            Message.NewMessage("user", "low").WithMetadata("importance", 0.1),
            Message.NewMessage("user", "high").WithMetadata("importance", 0.9),
            Message.NewMessage("user", "mid").WithMetadata("importance", 0.5)
        };
        var result = strategy.Apply(msgs);
        result.Should().HaveCount(2);
        result.Should().Contain(m => m.ContentString() == "high");
        result.Should().Contain(m => m.ContentString() == "mid");
    }

    [Fact]
    public void Apply_NoMetadata_UsesZeroScore()
    {
        var strategy = new ImportanceWeightingStrategy(topK: 2);
        var msgs = new List<Message>
        {
            Message.NewMessage("user", "a"),
            Message.NewMessage("user", "b"),
            Message.NewMessage("user", "c")
        };
        var result = strategy.Apply(msgs);
        result.Should().HaveCount(2);
    }
}

public class SummarizationStrategyTests
{
    [Fact]
    public async Task ApplyAsync_WithinCapacity_ReturnsUnchanged()
    {
        var strategy = new SummarizationStrategy(10, msgs =>
            Task.FromResult(Message.NewMessage("assistant", "summary")));
        var msgs = Enumerable.Range(0, 5).Select(i => Message.NewMessage("user", $"m{i}")).ToList();
        var result = await strategy.ApplyAsync(msgs);
        result.Should().HaveCount(5);
    }

    [Fact]
    public async Task ApplyAsync_ExceedsCapacity_SummarizesOld()
    {
        var strategy = new SummarizationStrategy(4, msgs =>
            Task.FromResult(Message.NewMessage("assistant", "summary of old")));
        var msgs = Enumerable.Range(0, 10).Select(i => Message.NewMessage("user", $"m{i}")).ToList();
        var result = await strategy.ApplyAsync(msgs);
        // Result should contain the summary + 2 recent (capacity/2 = 2)
        result.Should().HaveCountLessThan(10);
        result.Should().Contain(m => m.ContentString() == "summary of old");
    }
}
