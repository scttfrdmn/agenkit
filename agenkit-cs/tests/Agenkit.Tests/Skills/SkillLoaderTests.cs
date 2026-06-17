using Agenkit.Skills;

namespace Agenkit.Tests.Skills;

public sealed class SkillLoaderTests : IDisposable
{
    private readonly string _tmp;

    public SkillLoaderTests()
    {
        _tmp = Path.Combine(Path.GetTempPath(), "agenkit-skills-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tmp);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tmp))
            Directory.Delete(_tmp, recursive: true);
    }

    private string MakeSkillDir(string name, string description, string body = "Instructions here.")
    {
        var skillDir = Path.Combine(_tmp, name);
        Directory.CreateDirectory(skillDir);
        var content = $"---\nname: {name}\ndescription: {description}\n---\n{body}";
        File.WriteAllText(Path.Combine(skillDir, "SKILL.md"), content);
        return skillDir;
    }

    // ----- AgentSkill.FromDirectory -----

    [Fact]
    public void FromDirectory_ValidSkill()
    {
        var skillDir = MakeSkillDir("pdf-processing", "Extract text from PDFs.", "# PDF\nDo stuff.");
        var skill = AgentSkill.FromDirectory(skillDir);

        skill.Name.Should().Be("pdf-processing");
        skill.Description.Should().Be("Extract text from PDFs.");
        skill.Instructions.Should().Contain("Do stuff.");
        skill.SkillDir.Should().Be(skillDir);
    }

    [Fact]
    public void FromDirectory_WithLicenseAndMetadata()
    {
        var skillDir = Path.Combine(_tmp, "advanced");
        Directory.CreateDirectory(skillDir);
        var content =
            "---\n" +
            "name: advanced\n" +
            "description: Advanced skill.\n" +
            "license: Apache-2.0\n" +
            "metadata:\n" +
            "  version: '1.0'\n" +
            "---\n" +
            "Advanced instructions.";
        File.WriteAllText(Path.Combine(skillDir, "SKILL.md"), content);

        var skill = AgentSkill.FromDirectory(skillDir);

        skill.License.Should().Be("Apache-2.0");
        skill.Metadata.Should().ContainKey("version");
        skill.Metadata["version"].Should().Be("1.0");
    }

    [Fact]
    public void FromDirectory_MissingSkillMd_Throws()
    {
        var emptyDir = Path.Combine(_tmp, "empty");
        Directory.CreateDirectory(emptyDir);

        var act = () => AgentSkill.FromDirectory(emptyDir);
        act.Should().Throw<ArgumentException>().WithMessage("*No SKILL.md found*");
    }

    [Fact]
    public void FromDirectory_InvalidFrontmatter_Throws()
    {
        var skillDir = Path.Combine(_tmp, "bad");
        Directory.CreateDirectory(skillDir);
        // Missing second "---" delimiter.
        File.WriteAllText(Path.Combine(skillDir, "SKILL.md"), "name: foo\ndescription: bar\n");

        var act = () => AgentSkill.FromDirectory(skillDir);
        act.Should().Throw<ArgumentException>().WithMessage("*missing frontmatter delimiters*");
    }

    [Fact]
    public void FromDirectory_MissingName_Throws()
    {
        var skillDir = Path.Combine(_tmp, "noname");
        Directory.CreateDirectory(skillDir);
        File.WriteAllText(
            Path.Combine(skillDir, "SKILL.md"),
            "---\ndescription: A skill without a name.\n---\nInstructions.");

        var act = () => AgentSkill.FromDirectory(skillDir);
        act.Should().Throw<ArgumentException>().WithMessage("*Missing required field 'name'*");
    }

    [Fact]
    public void FromDirectory_MissingDescription_Throws()
    {
        var skillDir = Path.Combine(_tmp, "nodesc");
        Directory.CreateDirectory(skillDir);
        File.WriteAllText(
            Path.Combine(skillDir, "SKILL.md"),
            "---\nname: nodesc\n---\nInstructions.");

        var act = () => AgentSkill.FromDirectory(skillDir);
        act.Should().Throw<ArgumentException>().WithMessage("*Missing required field 'description'*");
    }

    [Fact]
    public void ToPrompt_RendersBlock()
    {
        var skillDir = MakeSkillDir("csv-tools", "Handle CSV files.", "Parse and write CSV.");
        var skill = AgentSkill.FromDirectory(skillDir);
        var prompt = skill.ToPrompt();

        prompt.Should().Contain("# Skill: csv-tools");
        prompt.Should().Contain("## Description");
        prompt.Should().Contain("Handle CSV files.");
        prompt.Should().Contain("## Instructions");
        prompt.Should().Contain("Parse and write CSV.");
    }

    // ----- SkillRegistry -----

    [Fact]
    public void Discover_SkipsNonDirs()
    {
        File.WriteAllText(Path.Combine(_tmp, "not_a_dir.md"), "ignored");
        var registry = new SkillRegistry(new[] { _tmp });
        registry.DiscoverSkills();

        registry.Skills.Should().BeEmpty();
    }

    [Fact]
    public void Discover_LoadsValidSkills()
    {
        MakeSkillDir("skill-a", "Skill A description.");
        MakeSkillDir("skill-b", "Skill B description.");
        var registry = new SkillRegistry(new[] { _tmp });
        registry.DiscoverSkills();

        registry.Skills.Should().ContainKey("skill-a");
        registry.Skills.Should().ContainKey("skill-b");
    }

    [Fact]
    public void FindRelevant_NameMatch()
    {
        MakeSkillDir("pdf-processing", "Work with PDF documents.");
        MakeSkillDir("csv-tools", "Handle CSV spreadsheets.");
        var registry = new SkillRegistry(new[] { _tmp });
        registry.DiscoverSkills();

        var results = registry.FindRelevantSkills("pdf");
        results.Should().HaveCountGreaterThanOrEqualTo(1);
        results[0].Name.Should().Be("pdf-processing");
    }

    [Fact]
    public void FindRelevant_MaxResults()
    {
        for (var i = 0; i < 6; i++)
            MakeSkillDir($"skill-{i}", $"A skill about document processing number {i}.");
        var registry = new SkillRegistry(new[] { _tmp });
        registry.DiscoverSkills();

        var results = registry.FindRelevantSkills("document", maxResults: 3);
        results.Count.Should().BeLessThanOrEqualTo(3);
    }

    [Fact]
    public void GetSkill_ReturnsOrNull()
    {
        MakeSkillDir("email-compose", "Compose professional emails.");
        var registry = new SkillRegistry(new[] { _tmp });
        registry.DiscoverSkills();

        var skill = registry.GetSkill("email-compose");
        skill.Should().NotBeNull();
        skill!.Name.Should().Be("email-compose");

        registry.GetSkill("nonexistent").Should().BeNull();
    }
}
