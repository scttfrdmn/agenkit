package io.agenkit.skills;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Discovers and searches agent skills across filesystem paths.
 *
 * <p>Skills are discovered by walking search paths and loading any subdirectory
 * that contains a {@code SKILL.md} file. Invalid skill directories are skipped
 * with a warning.
 */
public final class SkillRegistry {

    private static final Logger log = LoggerFactory.getLogger(SkillRegistry.class);

    private final List<Path> searchPaths;
    private final Map<String, AgentSkill> skills = new LinkedHashMap<>();

    public SkillRegistry(List<Path> searchPaths) {
        this.searchPaths = new ArrayList<>(searchPaths);
    }

    /**
     * Walk each search path and load all valid skill directories.
     *
     * <p>Skill directories without a {@code SKILL.md} or with invalid format are
     * skipped and logged as warnings.
     */
    public void discoverSkills() {
        for (Path searchPath : searchPaths) {
            if (!Files.isDirectory(searchPath)) {
                continue;
            }
            try (Stream<Path> entries = Files.list(searchPath)) {
                List<Path> dirs = entries
                        .filter(Files::isDirectory)
                        .filter(entry -> Files.exists(entry.resolve("SKILL.md")))
                        .collect(Collectors.toList());
                for (Path entry : dirs) {
                    try {
                        AgentSkill skill = AgentSkill.fromDirectory(entry);
                        skills.put(skill.getName(), skill);
                    } catch (IllegalArgumentException exc) {
                        log.warn("skipping skill directory {}: {}", entry, exc.getMessage());
                    }
                }
            } catch (IOException exc) {
                log.warn("failed to list search path {}: {}", searchPath, exc.getMessage());
            }
        }
    }

    /**
     * Return skills most relevant to the given query string.
     *
     * <p>Scoring:
     * <ul>
     *   <li>+10 if query (lowercased) appears in skill name (lowercased)</li>
     *   <li>+5 if query (lowercased) appears in skill description (lowercased)</li>
     *   <li>+N for each word in query that also appears in description</li>
     * </ul>
     * Only skills with score &gt; 0 are returned, sorted descending.
     *
     * @param query natural-language query to match against skills
     * @param maxResults maximum number of skills to return
     * @return ordered list of matching skills (best match first)
     */
    public List<AgentSkill> findRelevantSkills(String query, int maxResults) {
        String queryLower = query.toLowerCase();
        Set<String> queryWords = new HashSet<>(Arrays.asList(queryLower.split("\\s+")));

        List<AgentSkill> scored = skills.values().stream()
                .map(skill -> Map.entry(score(skill, queryLower, queryWords), skill))
                .filter(e -> e.getKey() > 0)
                .sorted(Comparator.comparingInt(Map.Entry<Integer, AgentSkill>::getKey).reversed())
                .limit(Math.max(0, maxResults))
                .map(Map.Entry::getValue)
                .collect(Collectors.toList());

        return scored;
    }

    /** Find relevant skills using the default maximum of 5 results. */
    public List<AgentSkill> findRelevantSkills(String query) {
        return findRelevantSkills(query, 5);
    }

    private static int score(AgentSkill skill, String queryLower, Set<String> queryWords) {
        int score = 0;
        String nameLower = skill.getName().toLowerCase();
        String descLower = skill.getDescription().toLowerCase();

        if (nameLower.contains(queryLower)) {
            score += 10;
        }
        if (descLower.contains(queryLower)) {
            score += 5;
        }

        Set<String> descWords = new HashSet<>(Arrays.asList(descLower.split("\\s+")));
        descWords.retainAll(queryWords);
        score += descWords.size();

        return score;
    }

    /** Return the skill with the given name, if present. */
    public Optional<AgentSkill> getSkill(String name) {
        return Optional.ofNullable(skills.get(name));
    }

    /** Read-only copy of loaded skills keyed by name. */
    public Map<String, AgentSkill> getSkills() {
        return new LinkedHashMap<>(skills);
    }
}
