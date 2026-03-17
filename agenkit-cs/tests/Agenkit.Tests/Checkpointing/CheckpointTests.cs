using Agenkit.Checkpointing;
using Agenkit.Core;
using Agenkit.Tests.Helpers;

namespace Agenkit.Tests.Checkpointing;

public class CheckpointManagerTests : IDisposable
{
    private readonly string _dir = Path.Combine(Path.GetTempPath(), $"cp-test-{Guid.NewGuid()}");
    private readonly CheckpointManager _manager;

    public CheckpointManagerTests()
    {
        _manager = new CheckpointManager(_dir);
    }

    public void Dispose()
    {
        if (Directory.Exists(_dir))
            Directory.Delete(_dir, recursive: true);
    }

    [Fact]
    public async Task SaveAsync_CreatesFile()
    {
        await _manager.SaveAsync("test", new { value = 42 });
        _manager.Exists("test").Should().BeTrue();
    }

    [Fact]
    public async Task LoadAsync_ReturnsStoredData()
    {
        await _manager.SaveAsync("data", new { name = "agenkit" });
        var loaded = await _manager.LoadAsync<Dictionary<string, object>>("data");
        loaded.Should().NotBeNull();
    }

    [Fact]
    public async Task LoadAsync_NonExistent_ReturnsNull()
    {
        var result = await _manager.LoadAsync<Dictionary<string, object>>("nonexistent");
        result.Should().BeNull();
    }

    [Fact]
    public async Task Delete_RemovesFile()
    {
        await _manager.SaveAsync("todelete", new { x = 1 });
        _manager.Delete("todelete");
        _manager.Exists("todelete").Should().BeFalse();
    }

    [Fact]
    public async Task ListCheckpoints_ReturnsAllNames()
    {
        await _manager.SaveAsync("cp1", new { });
        await _manager.SaveAsync("cp2", new { });
        var list = _manager.ListCheckpoints();
        list.Should().Contain("cp1").And.Contain("cp2");
    }
}

public class DurableAgentTests
{
    private readonly string _dir = Path.Combine(Path.GetTempPath(), $"durable-{Guid.NewGuid()}");

    [Fact]
    public async Task ProcessAsync_CheckpointsAfterEachMessage()
    {
        var manager = new CheckpointManager(_dir);
        var agent = new DurableAgent(new MockAgent("result"), manager);

        await agent.ProcessAsync(Message.NewMessage("user", "hello"));
        manager.Exists(agent.Name).Should().BeTrue();

        if (Directory.Exists(_dir)) Directory.Delete(_dir, recursive: true);
    }

    [Fact]
    public async Task ProcessAsync_TracksMessageCount()
    {
        var dir = Path.Combine(Path.GetTempPath(), $"dur2-{Guid.NewGuid()}");
        var manager = new CheckpointManager(dir);
        var agent = new DurableAgent(new MockAgent(), manager);

        await agent.ProcessAsync(Message.NewMessage("user", "a"));
        await agent.ProcessAsync(Message.NewMessage("user", "b"));
        agent.MessageCount.Should().Be(2);

        if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
    }

    [Fact]
    public void Introspect_ContainsMessageCount()
    {
        var manager = new CheckpointManager(Path.GetTempPath());
        var agent = new DurableAgent(new MockAgent(), manager);
        agent.Introspect().State!["message_count"].Should().Be(0);
    }
}
