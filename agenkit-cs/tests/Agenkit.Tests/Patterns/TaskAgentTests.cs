using Agenkit.Core;
using Agenkit.Patterns;
using Agenkit.Tests.Helpers;
using FluentAssertions;

namespace Agenkit.Tests.Patterns;

public class TaskAgentTests
{
    [Fact]
    public async Task ProcessAsync_CompletesTask_ReturnsResponse()
    {
        var config = new TaskAgentConfig(new MockAgent("result"));
        var agent = new TaskAgent(config);

        var response = await agent.ProcessAsync(Message.NewMessage("user", "task"));
        response.ContentString().Should().Be("result");
        agent.State.Should().Be(TaskState.Completed);
    }

    [Fact]
    public async Task ProcessAsync_OnFailure_SetsFailedState()
    {
        var config = new TaskAgentConfig(new MockAgent(exception: new Exception("failed")));
        var agent = new TaskAgent(config);

        await agent.Invoking(a => a.ProcessAsync(Message.NewMessage("user", "task")))
            .Should().ThrowAsync<Exception>();
        agent.State.Should().Be(TaskState.Failed);
    }

    [Fact]
    public async Task Reset_AllowsReuse()
    {
        var config = new TaskAgentConfig(new MockAgent("r1"));
        var agent = new TaskAgent(config);

        await agent.ProcessAsync(Message.NewMessage("user", "first"));
        agent.State.Should().Be(TaskState.Completed);

        agent.Reset();
        agent.State.Should().Be(TaskState.Idle);

        await agent.ProcessAsync(Message.NewMessage("user", "second"));
        agent.State.Should().Be(TaskState.Completed);
    }

    [Fact]
    public async Task ProcessAsync_WhenAlreadyRunning_Throws()
    {
        // Create an agent that blocks until told to proceed
        var tcs = new TaskCompletionSource<Message>();
        var blockingAgent = new BlockingAgent(tcs.Task);
        var config = new TaskAgentConfig(blockingAgent);
        var agent = new TaskAgent(config);

        var first = agent.ProcessAsync(Message.NewMessage("user", "task1"));
        Action act = () => agent.ProcessAsync(Message.NewMessage("user", "task2")).GetAwaiter().GetResult();
        act.Should().Throw<InvalidOperationException>().WithMessage("*already running*");

        tcs.SetResult(Message.NewMessage("assistant", "done"));
        await first;
    }

    [Fact]
    public async Task ProcessAsync_WithTimeout_TimesOut()
    {
        var slow = new SlowAgent(TimeSpan.FromSeconds(10));
        var config = new TaskAgentConfig(slow, Timeout: TimeSpan.FromMilliseconds(50));
        var agent = new TaskAgent(config);

        await agent.Invoking(a => a.ProcessAsync(Message.NewMessage("user", "task")))
            .Should().ThrowAsync<Exception>();
        agent.State.Should().Be(TaskState.Failed);
    }

    [Fact]
    public void Introspect_ReturnsState()
    {
        var config = new TaskAgentConfig(new MockAgent());
        var agent = new TaskAgent(config);
        var result = agent.Introspect();
        result.State.Should().ContainKey("state");
    }

    private class BlockingAgent : IAgent
    {
        private readonly Task<Message> _task;
        public BlockingAgent(Task<Message> task) => _task = task;
        public string Name => "BlockingAgent";
        public IReadOnlyList<string> Capabilities => Array.Empty<string>();
        public Task<Message> ProcessAsync(Message message, CancellationToken ct = default) => _task;
        public IntrospectionResult Introspect() => new(Name, Capabilities);
    }

    private class SlowAgent : IAgent
    {
        private readonly TimeSpan _delay;
        public SlowAgent(TimeSpan delay) => _delay = delay;
        public string Name => "SlowAgent";
        public IReadOnlyList<string> Capabilities => Array.Empty<string>();
        public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
        {
            await Task.Delay(_delay, ct);
            return Message.NewMessage("assistant", "done");
        }
        public IntrospectionResult Introspect() => new(Name, Capabilities);
    }
}
