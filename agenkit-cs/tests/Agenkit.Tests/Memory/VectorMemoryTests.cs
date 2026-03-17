using Agenkit.Core;
using Agenkit.Memory;

namespace Agenkit.Tests.Memory;

public class VectorMemoryTests
{
    [Fact]
    public async Task StoreAsync_AndRetrieve_ReturnsMessages()
    {
        var mem = new VectorMemory();
        await mem.StoreAsync(Message.NewMessage("user", "hello world"));
        var retrieved = await mem.RetrieveAsync(10);
        retrieved.Should().HaveCount(1);
    }

    [Fact]
    public async Task RetrieveSimilarAsync_ReturnsMostRelevant()
    {
        var mem = new VectorMemory();
        await mem.StoreAsync(Message.NewMessage("user", "artificial intelligence machine learning"));
        await mem.StoreAsync(Message.NewMessage("user", "pizza pasta cooking recipe"));
        await mem.StoreAsync(Message.NewMessage("user", "neural network deep learning"));

        var results = await mem.RetrieveSimilarAsync("AI neural network", count: 2);
        results.Should().HaveCount(2);
        // The AI-related messages should rank higher
        results[0].ContentString().Should().NotBe("pizza pasta cooking recipe");
    }

    [Fact]
    public async Task ClearAsync_RemovesAllMessages()
    {
        var mem = new VectorMemory();
        await mem.StoreAsync(Message.NewMessage("user", "test"));
        await mem.ClearAsync();
        var retrieved = await mem.RetrieveAsync(10);
        retrieved.Should().BeEmpty();
    }

    [Fact]
    public async Task RetrieveAsync_EmptyMemory_ReturnsEmpty()
    {
        var mem = new VectorMemory();
        var result = await mem.RetrieveAsync();
        result.Should().BeEmpty();
    }

    [Fact]
    public async Task StoreAsync_ExceedsCapacity_EvictsOldest()
    {
        var mem = new VectorMemory(maxMessages: 2);
        await mem.StoreAsync(Message.NewMessage("user", "msg1"));
        await mem.StoreAsync(Message.NewMessage("user", "msg2"));
        await mem.StoreAsync(Message.NewMessage("user", "msg3")); // should evict msg1
        var retrieved = await mem.RetrieveAsync(10);
        retrieved.Should().HaveCount(2);
        retrieved.Should().NotContain(m => m.ContentString() == "msg1");
    }
}
