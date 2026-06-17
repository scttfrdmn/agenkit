/**
 * @file skill.cpp
 * @brief Agent Skill loader and registry implementation.
 */

#include "agenkit/skills/skill.hpp"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace agenkit {
namespace skills {

namespace {

/** Lowercase a copy of the given string (ASCII). */
std::string to_lower(const std::string& s) {
    std::string out = s;
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return out;
}

/** Trim leading and trailing whitespace (matches Python str.strip semantics). */
std::string trim(const std::string& s) {
    auto is_space = [](unsigned char c) { return std::isspace(c) != 0; };
    std::size_t start = 0;
    while (start < s.size() && is_space(static_cast<unsigned char>(s[start]))) {
        ++start;
    }
    std::size_t end = s.size();
    while (end > start && is_space(static_cast<unsigned char>(s[end - 1]))) {
        --end;
    }
    return s.substr(start, end - start);
}

/**
 * @brief Strip matching surrounding single or double quotes from a scalar.
 *
 * Mirrors enough of YAML scalar handling for the frontmatter we support
 * (e.g. version: '1.0' -> 1.0).
 */
std::string unquote(const std::string& s) {
    if (s.size() >= 2) {
        char first = s.front();
        char last = s.back();
        if ((first == '\'' && last == '\'') || (first == '"' && last == '"')) {
            return s.substr(1, s.size() - 2);
        }
    }
    return s;
}

/** Read an entire file into a string. */
std::string read_file(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

/**
 * @brief Split a string on the first `max_splits` occurrences of `delim`.
 *
 * Replicates Python's str.split(delim, maxsplit) behaviour, which is what the
 * reference loader relies on: raw.split("---", 2).
 */
std::vector<std::string> split_n(const std::string& s, const std::string& delim,
                                 std::size_t max_splits) {
    std::vector<std::string> parts;
    std::size_t pos = 0;
    std::size_t splits = 0;
    while (splits < max_splits) {
        std::size_t next = s.find(delim, pos);
        if (next == std::string::npos) {
            break;
        }
        parts.push_back(s.substr(pos, next - pos));
        pos = next + delim.size();
        ++splits;
    }
    parts.push_back(s.substr(pos));
    return parts;
}

/**
 * @brief Minimal YAML frontmatter parser for skill SKILL.md files.
 *
 * Supports the subset used by skills:
 *   - top-level scalar entries: `key: value`
 *   - a `metadata:` mapping block with indented `key: value` entries
 *
 * Populates name/description/license/metadata on the skill. Returns false only
 * if the frontmatter is not a mapping (no key/value lines at all and not empty
 * — empty maps to an empty mapping, matching yaml.safe_load("") -> None being
 * rejected; here we treat any non-mapping content as invalid).
 */
struct Frontmatter {
    std::string name;
    std::string description;
    std::optional<std::string> license;
    std::map<std::string, std::string> metadata;
    bool has_name = false;
    bool has_description = false;
};

Frontmatter parse_frontmatter(const std::string& text) {
    Frontmatter fm;
    std::istringstream stream(text);
    std::string line;
    bool in_metadata = false;

    while (std::getline(stream, line)) {
        // Strip a trailing carriage return for CRLF files.
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }

        const std::string trimmed = trim(line);
        if (trimmed.empty() || trimmed[0] == '#') {
            continue;
        }

        // Determine indentation to detect nested metadata entries.
        const std::size_t indent = line.find_first_not_of(" \t");
        const bool indented = (indent != std::string::npos && indent > 0);

        const std::size_t colon = trimmed.find(':');
        if (colon == std::string::npos) {
            // Not a key/value line; ignore (lenient).
            continue;
        }

        const std::string key = trim(trimmed.substr(0, colon));
        const std::string value = trim(trimmed.substr(colon + 1));

        if (in_metadata && indented) {
            if (!key.empty()) {
                fm.metadata[key] = unquote(value);
            }
            continue;
        }

        // A non-indented line ends any metadata block.
        in_metadata = false;

        if (key == "metadata" && value.empty()) {
            in_metadata = true;
            continue;
        }

        if (key == "name") {
            fm.name = unquote(value);
            fm.has_name = !fm.name.empty();
        } else if (key == "description") {
            fm.description = unquote(value);
            fm.has_description = !fm.description.empty();
        } else if (key == "license") {
            std::string lic = unquote(value);
            if (!lic.empty()) {
                fm.license = lic;
            }
        }
        // Unknown top-level keys are ignored.
    }

    return fm;
}

} // namespace

AgentSkill AgentSkill::from_directory(const std::filesystem::path& skill_dir) {
    const std::filesystem::path skill_file = skill_dir / "SKILL.md";
    if (!std::filesystem::exists(skill_file)) {
        throw std::invalid_argument("No SKILL.md found in " + skill_dir.string());
    }

    const std::string raw = read_file(skill_file);

    // Split on "---" delimiters (first two occurrences). File must start with
    // "---" so that parts[0] is empty and parts[1] is the frontmatter.
    const std::vector<std::string> parts = split_n(raw, "---", 2);
    if (parts.size() < 3) {
        throw std::invalid_argument("Invalid SKILL.md in " + skill_dir.string() +
                                    ": missing frontmatter delimiters");
    }

    const std::string frontmatter_text = trim(parts[1]);
    const std::string instructions = trim(parts[2]);

    const Frontmatter fm = parse_frontmatter(frontmatter_text);

    if (!fm.has_name) {
        throw std::invalid_argument("Missing required field 'name' in " +
                                    skill_dir.string() + "/SKILL.md");
    }
    if (!fm.has_description) {
        throw std::invalid_argument("Missing required field 'description' in " +
                                    skill_dir.string() + "/SKILL.md");
    }

    AgentSkill skill;
    skill.name = fm.name;
    skill.description = fm.description;
    skill.instructions = instructions;
    skill.license = fm.license;
    skill.metadata = fm.metadata;
    skill.skill_dir = skill_dir;
    return skill;
}

std::string AgentSkill::to_prompt() const {
    return "# Skill: " + name + "\n\n" +
           "## Description\n" + description + "\n\n" +
           "## Instructions\n" + instructions + "\n";
}

SkillRegistry::SkillRegistry(std::vector<std::filesystem::path> search_paths)
    : search_paths_(std::move(search_paths)) {}

void SkillRegistry::discover_skills() {
    for (const auto& search_path : search_paths_) {
        std::error_code ec;
        if (!std::filesystem::is_directory(search_path, ec) || ec) {
            continue;
        }
        for (const auto& entry : std::filesystem::directory_iterator(search_path, ec)) {
            if (ec) {
                break;
            }
            if (!entry.is_directory(ec) || ec) {
                continue;
            }
            const std::filesystem::path skill_md = entry.path() / "SKILL.md";
            if (!std::filesystem::exists(skill_md)) {
                continue;
            }
            try {
                AgentSkill skill = AgentSkill::from_directory(entry.path());
                skills_[skill.name] = std::move(skill);
            } catch (const std::invalid_argument& exc) {
                std::cerr << "skipping skill directory " << entry.path().string()
                          << ": " << exc.what() << std::endl;
            }
        }
    }
}

std::vector<AgentSkill> SkillRegistry::find_relevant_skills(const std::string& query,
                                                            std::size_t max_results) const {
    const std::string query_lower = to_lower(query);

    // Unique query words.
    std::set<std::string> query_words;
    {
        std::istringstream qs(query_lower);
        std::string word;
        while (qs >> word) {
            query_words.insert(word);
        }
    }

    std::vector<std::pair<int, const AgentSkill*>> scored;
    for (const auto& [name, skill] : skills_) {
        int score = 0;
        const std::string name_lower = to_lower(skill.name);
        const std::string desc_lower = to_lower(skill.description);

        if (!query_lower.empty() && name_lower.find(query_lower) != std::string::npos) {
            score += 10;
        }
        if (!query_lower.empty() && desc_lower.find(query_lower) != std::string::npos) {
            score += 5;
        }

        // Count unique query words that appear as whitespace-delimited words in
        // the description.
        std::set<std::string> desc_words;
        {
            std::istringstream ds(desc_lower);
            std::string word;
            while (ds >> word) {
                desc_words.insert(word);
            }
        }
        for (const auto& qw : query_words) {
            if (desc_words.count(qw) > 0) {
                score += 1;
            }
        }

        if (score > 0) {
            scored.emplace_back(score, &skill);
        }
    }

    // Stable sort by score descending so equal-scored skills keep a
    // deterministic (name-ordered) order from the map iteration above.
    std::stable_sort(scored.begin(), scored.end(),
                     [](const auto& a, const auto& b) { return a.first > b.first; });

    std::vector<AgentSkill> result;
    for (std::size_t i = 0; i < scored.size() && i < max_results; ++i) {
        result.push_back(*scored[i].second);
    }
    return result;
}

std::optional<AgentSkill> SkillRegistry::get_skill(const std::string& name) const {
    auto it = skills_.find(name);
    if (it == skills_.end()) {
        return std::nullopt;
    }
    return it->second;
}

std::map<std::string, AgentSkill> SkillRegistry::skills() const {
    return skills_;
}

} // namespace skills
} // namespace agenkit
