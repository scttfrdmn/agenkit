namespace Agenkit.Skills;

/// <summary>
/// Represents a single agent skill loaded from a directory.
///
/// A skill directory must contain a SKILL.md file structured as:
/// <code>
/// ---
/// name: skill-name
/// description: What this skill does.
/// license: Apache-2.0  # optional
/// metadata:            # optional
///   key: value
/// ---
/// # Skill Title
/// Markdown instructions here.
/// </code>
/// </summary>
public sealed class AgentSkill
{
    /// <summary>Unique name of the skill.</summary>
    public string Name { get; }

    /// <summary>Short human-readable description of what the skill does.</summary>
    public string Description { get; }

    /// <summary>Markdown instruction body for the skill.</summary>
    public string Instructions { get; }

    /// <summary>Optional SPDX license identifier.</summary>
    public string? License { get; }

    /// <summary>Optional metadata key/value pairs from the frontmatter.</summary>
    public IReadOnlyDictionary<string, object> Metadata { get; }

    /// <summary>Directory the skill was loaded from, or null if constructed directly.</summary>
    public string? SkillDir { get; }

    /// <summary>Creates an AgentSkill.</summary>
    public AgentSkill(
        string name,
        string description,
        string instructions,
        string? license = null,
        IReadOnlyDictionary<string, object>? metadata = null,
        string? skillDir = null)
    {
        Name = name;
        Description = description;
        Instructions = instructions;
        License = license;
        Metadata = metadata ?? new Dictionary<string, object>();
        SkillDir = skillDir;
    }

    /// <summary>
    /// Loads a skill from a directory containing a SKILL.md file.
    /// </summary>
    /// <param name="skillDir">Path to the skill directory.</param>
    /// <returns>An <see cref="AgentSkill"/> instance.</returns>
    /// <exception cref="ArgumentException">
    /// If the directory lacks SKILL.md, has invalid frontmatter, or is missing
    /// required fields (name, description).
    /// </exception>
    public static AgentSkill FromDirectory(string skillDir)
    {
        var skillFile = Path.Combine(skillDir, "SKILL.md");
        if (!File.Exists(skillFile))
            throw new ArgumentException($"No SKILL.md found in {skillDir}");

        var raw = File.ReadAllText(skillFile);

        // Split on "---" delimiters (max 3 parts). File must start with "---".
        var parts = SplitFrontmatter(raw);
        if (parts.Length < 3)
            throw new ArgumentException($"Invalid SKILL.md in {skillDir}: missing frontmatter delimiters");

        var frontmatterText = parts[1].Trim();
        var instructions = parts[2].Trim();

        var fm = SimpleYaml.ParseMapping(frontmatterText);

        if (!fm.TryGetValue("name", out var nameObj) || nameObj is not string name || string.IsNullOrEmpty(name))
            throw new ArgumentException($"Missing required field 'name' in {skillDir}/SKILL.md");

        if (!fm.TryGetValue("description", out var descObj) || descObj is not string description ||
            string.IsNullOrEmpty(description))
            throw new ArgumentException($"Missing required field 'description' in {skillDir}/SKILL.md");

        string? license = fm.TryGetValue("license", out var licObj) ? licObj as string : null;

        var metadata = fm.TryGetValue("metadata", out var metaObj) &&
                       metaObj is IReadOnlyDictionary<string, object> meta
            ? meta
            : new Dictionary<string, object>();

        return new AgentSkill(name, description, instructions, license, metadata, skillDir);
    }

    /// <summary>
    /// Renders the skill as a prompt block for injection into agent messages.
    /// </summary>
    public string ToPrompt() =>
        $"# Skill: {Name}\n\n" +
        $"## Description\n{Description}\n\n" +
        $"## Instructions\n{Instructions}\n";

    // Splits raw text on "---" into at most 3 parts, mirroring Python's str.split("---", 2).
    private static string[] SplitFrontmatter(string raw)
    {
        const string delim = "---";
        var first = raw.IndexOf(delim, StringComparison.Ordinal);
        if (first < 0)
            return new[] { raw };

        var second = raw.IndexOf(delim, first + delim.Length, StringComparison.Ordinal);
        if (second < 0)
            return new[] { raw[..first], raw[(first + delim.Length)..] };

        return new[]
        {
            raw[..first],
            raw[(first + delim.Length)..second],
            raw[(second + delim.Length)..],
        };
    }
}
