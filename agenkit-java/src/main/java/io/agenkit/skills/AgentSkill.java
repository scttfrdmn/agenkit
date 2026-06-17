package io.agenkit.skills;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Represents a single agent skill loaded from a directory.
 *
 * <p>A skill directory must contain a {@code SKILL.md} file structured as:
 * <pre>{@code
 * ---
 * name: skill-name
 * description: What this skill does.
 * license: Apache-2.0  # optional
 * metadata:            # optional
 *   key: value
 * ---
 * # Skill Title
 * Markdown instructions here.
 * }</pre>
 */
public final class AgentSkill {

    private final String name;
    private final String description;
    private final String instructions;
    private final String license;
    private final Map<String, Object> metadata;
    private final Path skillDir;

    public AgentSkill(
            String name,
            String description,
            String instructions,
            String license,
            Map<String, Object> metadata,
            Path skillDir) {
        this.name = name;
        this.description = description;
        this.instructions = instructions;
        this.license = license;
        this.metadata = metadata != null
                ? Collections.unmodifiableMap(new LinkedHashMap<>(metadata))
                : Collections.emptyMap();
        this.skillDir = skillDir;
    }

    /**
     * Load a skill from a directory containing a {@code SKILL.md} file.
     *
     * @param skillDir path to the skill directory
     * @return the loaded skill
     * @throws IllegalArgumentException if the directory lacks SKILL.md, has
     *         invalid frontmatter, or is missing required fields (name, description)
     */
    public static AgentSkill fromDirectory(Path skillDir) {
        Path skillFile = skillDir.resolve("SKILL.md");
        if (!Files.exists(skillFile)) {
            throw new IllegalArgumentException("No SKILL.md found in " + skillDir);
        }

        String raw;
        try {
            raw = Files.readString(skillFile, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("failed to read " + skillFile, e);
        }

        // Split on "---" delimiters into at most 3 parts. File must start with "---".
        String[] parts = raw.split("---", 3);
        if (parts.length < 3) {
            throw new IllegalArgumentException(
                    "Invalid SKILL.md in " + skillDir + ": missing frontmatter delimiters");
        }

        String frontmatterText = parts[1].strip();
        String instructions = parts[2].strip();

        Map<String, Object> fm = parseFrontmatter(frontmatterText);

        Object name = fm.get("name");
        if (name == null || name.toString().isEmpty()) {
            throw new IllegalArgumentException(
                    "Missing required field 'name' in " + skillDir + "/SKILL.md");
        }

        Object description = fm.get("description");
        if (description == null || description.toString().isEmpty()) {
            throw new IllegalArgumentException(
                    "Missing required field 'description' in " + skillDir + "/SKILL.md");
        }

        Object license = fm.get("license");
        Object metadata = fm.get("metadata");

        @SuppressWarnings("unchecked")
        Map<String, Object> metadataMap = metadata instanceof Map
                ? (Map<String, Object>) metadata
                : Collections.emptyMap();

        return new AgentSkill(
                name.toString(),
                description.toString(),
                instructions,
                license != null ? license.toString() : null,
                metadataMap,
                skillDir);
    }

    /**
     * Minimal YAML frontmatter parser. Supports flat {@code key: value} pairs
     * and a single level of nested mapping under a key with an empty value
     * (e.g. {@code metadata:}) whose entries are indented. Quotes around scalar
     * values are stripped.
     */
    private static Map<String, Object> parseFrontmatter(String text) {
        Map<String, Object> result = new LinkedHashMap<>();
        Map<String, Object> nested = null;
        String[] lines = text.split("\n", -1);

        for (String line : lines) {
            if (line.isBlank() || line.strip().startsWith("#")) {
                continue;
            }

            boolean indented = line.startsWith("  ") || line.startsWith("\t");
            String trimmed = line.strip();
            int colon = trimmed.indexOf(':');
            if (colon < 0) {
                continue;
            }

            String key = trimmed.substring(0, colon).strip();
            String value = trimmed.substring(colon + 1).strip();

            if (indented && nested != null) {
                nested.put(key, parseScalar(value));
                continue;
            }

            if (value.isEmpty()) {
                // Begin a nested mapping (e.g. "metadata:").
                nested = new LinkedHashMap<>();
                result.put(key, nested);
            } else {
                nested = null;
                result.put(key, parseScalar(value));
            }
        }

        return result;
    }

    private static Object parseScalar(String value) {
        if (value.length() >= 2
                && ((value.startsWith("\"") && value.endsWith("\""))
                || (value.startsWith("'") && value.endsWith("'")))) {
            return value.substring(1, value.length() - 1);
        }
        return value;
    }

    /**
     * Render the skill as a prompt block for injection into agent messages.
     *
     * @return formatted string with skill name, description, and instructions
     */
    public String toPrompt() {
        return "# Skill: " + name + "\n\n"
                + "## Description\n" + description + "\n\n"
                + "## Instructions\n" + instructions + "\n";
    }

    public String getName() { return name; }
    public String getDescription() { return description; }
    public String getInstructions() { return instructions; }
    public Optional<String> getLicense() { return Optional.ofNullable(license); }
    public Map<String, Object> getMetadata() { return metadata; }
    public Optional<Path> getSkillDir() { return Optional.ofNullable(skillDir); }

    @Override
    public String toString() {
        return "AgentSkill{name='" + name + "', description='" + description + "'}";
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof AgentSkill s)) return false;
        return name.equals(s.name)
                && description.equals(s.description)
                && instructions.equals(s.instructions)
                && java.util.Objects.equals(license, s.license)
                && metadata.equals(s.metadata)
                && java.util.Objects.equals(skillDir, s.skillDir);
    }

    @Override
    public int hashCode() {
        return java.util.Objects.hash(name, description, instructions, license, metadata, skillDir);
    }
}
