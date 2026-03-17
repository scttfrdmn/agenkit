using Agenkit.Core;
using Agenkit.Memory;
using FluentAssertions;

namespace Agenkit.Tests.Memory;

public class EphemeralMemoryTests
{
    [Fact]
    public async Task StoreAsync_IncreasesCount()
    {
        var mem = new EphemeralMemory();
        await mem.StoreAsync(Message.NewMessage("user", "hello"));
        mem.Count.Should().Be(1);
    }

    [Fact]
    public async Task RetrieveAsync_ReturnsStoredMessages()
    {
        var mem = new EphemeralMemory();
        await mem.StoreAsync(Message.NewMessage("user", "msg1"));
        await mem.StoreAsync(Message.NewMessage("assistant", "msg2"));

        var retrieved = await mem.RetrieveAsync(10);
        retrieved.Should().HaveCount(2);
    }

    [Fact]
    public async Task RetrieveAsync_LimitedCount_ReturnsMostRecent()
    {
        var mem = new EphemeralMemory();
        for (int i = 0; i < 10; i++)
            await mem.StoreAsync(Message.NewMessage("user", $"msg{i}"));

        var retrieved = await mem.RetrieveAsync(3);
        retrieved.Should().HaveCount(3);
        retrieved[^1].ContentString().Should().Be("msg9");
    }

    [Fact]
    public async Task ClearAsync_RemovesAllMessages()
    {
        var mem = new EphemeralMemory();
        await mem.StoreAsync(Message.NewMessage("user", "test"));
        await mem.ClearAsync();
        mem.Count.Should().Be(0);
    }

    [Fact]
    public async Task StoreAsync_ExceedsCapacity_EvictsOldest()
    {
        var mem = new EphemeralMemory(maxMessages: 3);
        for (int i = 0; i < 5; i++)
            await mem.StoreAsync(Message.NewMessage("user", $"msg{i}"));

        mem.Count.Should().Be(3);
        var retrieved = await mem.RetrieveAsync(10);
        retrieved[0].ContentString().Should().Be("msg2"); // oldest retained
    }

    [Fact]
    public async Task RetrieveAsync_EmptyMemory_ReturnsEmpty()
    {
        var mem = new EphemeralMemory();
        var retrieved = await mem.RetrieveAsync();
        retrieved.Should().BeEmpty();
    }
}
