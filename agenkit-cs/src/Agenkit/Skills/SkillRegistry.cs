using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;

namespace Agenkit.Skills;

/// <summary>
/// Discovers and searches agent skills across filesystem paths.
///
/// Skills are discovered by walking search paths and loading any subdirectory
/// that contains a SKILL.md file. Invalid skill directories are skipped with
/// a warning.
/// </summary>
public sealed class SkillRegistry
{
    private readonly IReadOnlyList<string> _searchPaths;
    private readonly Dictionary<string, AgentSkill> _skills = new(StringComparer.Ordinal);
    private readonly ILogger _logger;

    /// <summary>Creates a registry over the given search paths.</summary>
    public SkillRegistry(IEnumerable<string> searchPaths, ILogger<SkillRegistry>? logger = null)
    {
        _searchPaths = searchPaths.ToList();
        _logger = logger ?? NullLogger<SkillRegistry>.Instance;
    }

    /// <summary>
    /// Walks each search path and loads all valid skill directories. Skill
    /// directories without a SKILL.md or with invalid format are skipped and
    /// logged as warnings.
    /// </summary>
    public void DiscoverSkills()
    {
        foreach (var searchPath in _searchPaths)
        {
            if (!Directory.Exists(searchPath))
                continue;

            foreach (var entry in Directory.EnumerateDirectories(searchPath))
            {
                if (!File.Exists(Path.Combine(entry, "SKILL.md")))
                    continue;

                try
                {
                    var skill = AgentSkill.FromDirectory(entry);
                    _skills[skill.Name] = skill;
                }
                catch (ArgumentException ex)
                {
                    _logger.LogWarning("skipping skill directory {Entry}: {Message}", entry, ex.Message);
                }
            }
        }
    }

    /// <summary>
    /// Returns skills most relevant to the given query string.
    ///
    /// Scoring:
    /// <list type="bullet">
    /// <item>+10 if query (lowercased) appears in the skill name (lowercased)</item>
    /// <item>+5 if query (lowercased) appears in the skill description (lowercased)</item>
    /// <item>+N for each query word that also appears in the description</item>
    /// </list>
    /// Only skills with score &gt; 0 are returned, sorted descending and capped
    /// at <paramref name="maxResults"/>.
    /// </summary>
    public IReadOnlyList<AgentSkill> FindRelevantSkills(string query, int maxResults = 5)
    {
        var queryLower = query.ToLowerInvariant();
        var queryWords = new HashSet<string>(
            queryLower.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries),
            StringComparer.Ordinal);

        var scored = new List<(int Score, AgentSkill Skill)>();
        foreach (var skill in _skills.Values)
        {
            var score = 0;
            var nameLower = skill.Name.ToLowerInvariant();
            var descLower = skill.Description.ToLowerInvariant();

            if (nameLower.Contains(queryLower, StringComparison.Ordinal))
                score += 10;
            if (descLower.Contains(queryLower, StringComparison.Ordinal))
                score += 5;

            var descWords = new HashSet<string>(
                descLower.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries),
                StringComparer.Ordinal);
            descWords.IntersectWith(queryWords);
            score += descWords.Count;

            if (score > 0)
                scored.Add((score, skill));
        }

        return scored
            .OrderByDescending(s => s.Score)
            .Take(maxResults)
            .Select(s => s.Skill)
            .ToList();
    }

    /// <summary>Returns the skill with the given name, or null if not found.</summary>
    public AgentSkill? GetSkill(string name) =>
        _skills.TryGetValue(name, out var skill) ? skill : null;

    /// <summary>Read-only copy of loaded skills keyed by name.</summary>
    public IReadOnlyDictionary<string, AgentSkill> Skills =>
        new Dictionary<string, AgentSkill>(_skills, StringComparer.Ordinal);
}
