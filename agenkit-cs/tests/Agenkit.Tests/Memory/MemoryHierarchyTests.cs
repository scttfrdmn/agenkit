using Agenkit.Core;
using Agenkit.Memory;
using FluentAssertions;

namespace Agenkit.Tests.Memory;

public class MemoryHierarchyTests
{
    [Fact]
    public async Task StoreAsync_StoresInWorkingMemory()
    {
        var hierarchy = new MemoryHierarchy(workingCapacity: 5);
        await hierarchy.StoreAsync(Message.NewMessage("user", "hello"));

        var working = await hierarchy.RetrieveWorkingAsync();
        working.Should().HaveCount(1);
    }

    [Fact]
    public async Task RetrieveAsync_ReturnsRecentMessages()
    {
        var hierarchy = new MemoryHierarchy(workingCapacity: 10);
        await hierarchy.StoreAsync(Message.NewMessage("user", "msg1"));
        await hierarchy.StoreAsync(Message.NewMessage("assistant", "msg2"));

        var msgs = await hierarchy.RetrieveAsync(10);
        msgs.Should().HaveCountGreaterThan(0);
    }

    [Fact]
    public async Task ClearAsync_EmptiesAllTiers()
    {
        var hierarchy = new MemoryHierarchy();
        await hierarchy.StoreAsync(Message.NewMessage("user", "test"));
        await hierarchy.ClearAsync();

        var msgs = await hierarchy.RetrieveAsync(10);
        msgs.Should().BeEmpty();
    }

    [Fact]
    public async Task StoreAsync_OverflowingWorking_PromotesToShortTerm()
    {
        // Working capacity = 2, so third message should trigger promotion
        var hierarchy = new MemoryHierarchy(workingCapacity: 2, shortTermCapacity: 20);
        for (int i = 0; i < 5; i++)
            await hierarchy.StoreAsync(Message.NewMessage("user", $"msg{i}"));

        var shortTerm = await hierarchy.RetrieveShortTermAsync(10);
        shortTerm.Should().HaveCountGreaterThan(0);
    }

    [Fact]
    public async Task RetrieveAsync_LimitCount_ReturnsLimit()
    {
        var hierarchy = new MemoryHierarchy(workingCapacity: 20);
        for (int i = 0; i < 10; i++)
            await hierarchy.StoreAsync(Message.NewMessage("user", $"msg{i}"));

        var msgs = await hierarchy.RetrieveAsync(3);
        msgs.Should().HaveCount(3);
    }
}
