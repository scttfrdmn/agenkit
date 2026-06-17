using Agenkit.Core;
using Agenkit.Skills;

namespace Agenkit.Tests.Skills;

public sealed class SkillEnabledAgentTests : IDisposable
{
    private readonly string _tmp;

    public SkillEnabledAgentTests()
    {
        _tmp = Path.Combine(Path.GetTempPath(), "agenkit-skillagent-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tmp);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tmp))
            Directory.Delete(_tmp, recursive: true);
    }

    private void MakeSkillDir(string name, string description, string body = "Instructions here.")
    {
        var skillDir = Path.Combine(_tmp, name);
        Directory.CreateDirectory(skillDir);
        var content = $"---\nname: {name}\ndescription: {description}\n---\n{body}";
        File.WriteAllText(Path.Combine(skillDir, "SKILL.md"), content);
    }

    /// <summary>Agent that echoes its input content (and metadata) back.</summary>
    private sealed class EchoAgent : IAgent
    {
        public string Name => "echo";
        public IReadOnlyList<string> Capabilities => Array.Empty<string>();

        public Task<Message> ProcessAsync(Message message, CancellationToken ct = default) =>
            Task.FromResult(new Message("agent", message.Content, message.Metadata));

        public IntrospectionResult Introspect() => new(Name, Capabilities);
    }

    [Fact]
    public async Task ProcessAsync_AugmentsMessage()
    {
        MakeSkillDir("pdf-processing", "Extract text from PDF documents.");
        var registry = new SkillRegistry(new[] { _tmp });
        var agent = new SkillEnabledAgent(new EchoAgent(), registry, autoDiscover: true);

        var msg = new Message("user", "How do I parse pdf files?");
        var response = await agent.ProcessAsync(msg);

        response.ContentString().Should().Contain("<available_skills>");
        response.ContentString().Should().Contain("pdf-processing");
    }

    [Fact]
    public async Task ProcessAsync_NoSkillsPassthrough()
    {
        MakeSkillDir("email-compose", "Compose professional emails.");
        var registry = new SkillRegistry(new[] { _tmp });
        var agent = new SkillEnabledAgent(new EchoAgent(), registry, autoDiscover: true);

        var msg = new Message("user", "tell me a joke");
        var response = await agent.ProcessAsync(msg);

        response.ContentString().Should().NotContain("<available_skills>");
        response.ContentString().Should().Be("tell me a joke");
    }

    [Fact]
    public async Task ProcessAsync_ActiveSkillsMetadata()
    {
        MakeSkillDir("csv-tools", "Handle and transform CSV spreadsheets.");
        var registry = new SkillRegistry(new[] { _tmp });
        var agent = new SkillEnabledAgent(new EchoAgent(), registry, autoDiscover: true);

        var msg = new Message("user", "parse this csv spreadsheet data");
        var response = await agent.ProcessAsync(msg);

        response.Metadata.Should().NotBeNull();
        response.Metadata!.Should().ContainKey("active_skills");
        var active = (IReadOnlyList<string>)response.Metadata!["active_skills"];
        active.Should().Contain("csv-tools");
    }

    [Fact]
    public void Capabilities_IncludesSkillInjection()
    {
        var registry = new SkillRegistry(new[] { _tmp });
        var agent = new SkillEnabledAgent(new EchoAgent(), registry, autoDiscover: false);

        agent.Capabilities.Should().Contain("skill_injection");
    }

    [Fact]
    public void Name_Delegates()
    {
        var registry = new SkillRegistry(new[] { _tmp });
        var agent = new SkillEnabledAgent(new EchoAgent(), registry, autoDiscover: false);

        agent.Name.Should().Be("echo");
    }
}
