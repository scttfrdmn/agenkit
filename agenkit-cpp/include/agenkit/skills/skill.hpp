/**
 * @file skill.hpp
 * @brief Agent Skill loader and registry
 *
 * Implements the Agent Skills specification: each skill is a directory
 * containing a SKILL.md file with YAML frontmatter (name, description, optional
 * license and metadata) followed by Markdown instructions.
 *
 * Mirrors the Python reference implementation (agenkit/skills/loader.py).
 */

#ifndef AGENKIT_SKILLS_SKILL_HPP
#define AGENKIT_SKILLS_SKILL_HPP

#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace agenkit {
namespace skills {

/**
 * @brief Represents a single agent skill loaded from a directory.
 *
 * A skill directory must contain a SKILL.md file structured as:
 * @code
 *     ---
 *     name: skill-name
 *     description: What this skill does.
 *     license: Apache-2.0  # optional
 *     metadata:            # optional
 *       key: value
 *     ---
 *     # Skill Title
 *     Markdown instructions here.
 * @endcode
 */
struct AgentSkill {
    /** Skill name (required). */
    std::string name;

    /** Human-readable description (required). */
    std::string description;

    /** Markdown instructions (body after frontmatter). */
    std::string instructions;

    /** Optional SPDX license identifier. */
    std::optional<std::string> license;

    /** Optional metadata key/value pairs. */
    std::map<std::string, std::string> metadata;

    /** Directory the skill was loaded from (if loaded from disk). */
    std::optional<std::filesystem::path> skill_dir;

    /**
     * @brief Load a skill from a directory containing a SKILL.md file.
     *
     * @param skill_dir Path to the skill directory.
     * @return AgentSkill instance.
     *
     * @throws std::invalid_argument If the directory lacks SKILL.md, has invalid
     *         frontmatter, or is missing required fields (name, description).
     *         The message contains one of:
     *         "No SKILL.md found", "missing frontmatter delimiters",
     *         "Missing required field 'name'",
     *         "Missing required field 'description'".
     */
    static AgentSkill from_directory(const std::filesystem::path& skill_dir);

    /**
     * @brief Render the skill as a prompt block for injection into messages.
     *
     * Format:
     * @code
     * # Skill: {name}
     *
     * ## Description
     * {description}
     *
     * ## Instructions
     * {instructions}
     * @endcode
     *
     * @return Formatted prompt string.
     */
    std::string to_prompt() const;
};

/**
 * @brief Discovers and searches agent skills across filesystem paths.
 *
 * Skills are discovered by walking search paths and loading any subdirectory
 * that contains a SKILL.md file. Invalid skill directories are skipped with a
 * warning logged to stderr.
 */
class SkillRegistry {
public:
    /**
     * @brief Construct a registry over the given search paths.
     * @param search_paths Directories to scan for skill subdirectories.
     */
    explicit SkillRegistry(std::vector<std::filesystem::path> search_paths);

    /**
     * @brief Walk each search path and load all valid skill directories.
     *
     * Skill directories without a SKILL.md or with invalid format are skipped
     * and logged as warnings.
     */
    void discover_skills();

    /**
     * @brief Return skills most relevant to the given query string.
     *
     * Scoring:
     *   +10 if query (lowercased) appears in skill name (lowercased)
     *   +5  if query (lowercased) appears in skill description (lowercased)
     *   +N  for each unique word in query that also appears in description
     *
     * Only skills with score > 0 are returned, sorted descending, capped at
     * max_results.
     *
     * @param query Natural-language query to match against skills.
     * @param max_results Maximum number of skills to return (default 5).
     * @return Ordered list of matching skills (best match first).
     */
    std::vector<AgentSkill> find_relevant_skills(const std::string& query,
                                                 std::size_t max_results = 5) const;

    /**
     * @brief Return the skill with the given name, or nullopt if not found.
     * @param name Skill name to look up.
     * @return Optional containing a copy of the skill if present.
     */
    std::optional<AgentSkill> get_skill(const std::string& name) const;

    /**
     * @brief Read-only copy of loaded skills keyed by name.
     * @return Map of skill name to skill.
     */
    std::map<std::string, AgentSkill> skills() const;

private:
    std::vector<std::filesystem::path> search_paths_;
    std::map<std::string, AgentSkill> skills_;
};

} // namespace skills
} // namespace agenkit

#endif // AGENKIT_SKILLS_SKILL_HPP
