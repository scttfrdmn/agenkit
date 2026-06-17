package io.agenkit.skills;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SkillLoaderTest {

    private static Path makeSkillDir(Path base, String name, String description) throws IOException {
        return makeSkillDir(base, name, description, "Instructions here.");
    }

    private static Path makeSkillDir(Path base, String name, String description, String body)
            throws IOException {
        Path skillDir = base.resolve(name);
        Files.createDirectories(skillDir);
        String content = "---\nname: " + name + "\ndescription: " + description + "\n---\n" + body;
        Files.writeString(skillDir.resolve("SKILL.md"), content, StandardCharsets.UTF_8);
        return skillDir;
    }

    // -----------------------------------------------------------------------
    // AgentSkill.fromDirectory
    // -----------------------------------------------------------------------

    @Test
    void loadSkillValid(@TempDir Path tmp) throws IOException {
        Path skillDir = makeSkillDir(tmp, "pdf-processing", "Extract text from PDFs.", "# PDF\nDo stuff.");
        AgentSkill skill = AgentSkill.fromDirectory(skillDir);

        assertThat(skill.getName()).isEqualTo("pdf-processing");
        assertThat(skill.getDescription()).isEqualTo("Extract text from PDFs.");
        assertThat(skill.getInstructions()).contains("Do stuff.");
        assertThat(skill.getSkillDir()).hasValue(skillDir);
    }

    @Test
    void loadSkillWithLicenseAndMetadata(@TempDir Path tmp) throws IOException {
        Path skillDir = tmp.resolve("advanced");
        Files.createDirectories(skillDir);
        String content = "---\n"
                + "name: advanced\n"
                + "description: Advanced skill.\n"
                + "license: Apache-2.0\n"
                + "metadata:\n"
                + "  version: '1.0'\n"
                + "---\n"
                + "Advanced instructions.";
        Files.writeString(skillDir.resolve("SKILL.md"), content, StandardCharsets.UTF_8);

        AgentSkill skill = AgentSkill.fromDirectory(skillDir);

        assertThat(skill.getLicense()).hasValue("Apache-2.0");
        assertThat(skill.getMetadata()).containsEntry("version", "1.0");
    }

    @Test
    void loadSkillMissingSkillMd(@TempDir Path tmp) throws IOException {
        Path emptyDir = tmp.resolve("empty");
        Files.createDirectories(emptyDir);

        assertThatThrownBy(() -> AgentSkill.fromDirectory(emptyDir))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("No SKILL.md found");
    }

    @Test
    void loadSkillInvalidFrontmatter(@TempDir Path tmp) throws IOException {
        Path skillDir = tmp.resolve("bad");
        Files.createDirectories(skillDir);
        // Missing second "---" delimiter.
        Files.writeString(skillDir.resolve("SKILL.md"),
                "name: foo\ndescription: bar\n", StandardCharsets.UTF_8);

        assertThatThrownBy(() -> AgentSkill.fromDirectory(skillDir))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("missing frontmatter delimiters");
    }

    @Test
    void loadSkillMissingName(@TempDir Path tmp) throws IOException {
        Path skillDir = tmp.resolve("noname");
        Files.createDirectories(skillDir);
        String content = "---\ndescription: A skill without a name.\n---\nInstructions.";
        Files.writeString(skillDir.resolve("SKILL.md"), content, StandardCharsets.UTF_8);

        assertThatThrownBy(() -> AgentSkill.fromDirectory(skillDir))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Missing required field 'name'");
    }

    @Test
    void loadSkillMissingDescription(@TempDir Path tmp) throws IOException {
        Path skillDir = tmp.resolve("nodesc");
        Files.createDirectories(skillDir);
        String content = "---\nname: nodesc\n---\nInstructions.";
        Files.writeString(skillDir.resolve("SKILL.md"), content, StandardCharsets.UTF_8);

        assertThatThrownBy(() -> AgentSkill.fromDirectory(skillDir))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Missing required field 'description'");
    }

    @Test
    void skillToPrompt(@TempDir Path tmp) throws IOException {
        Path skillDir = makeSkillDir(tmp, "csv-tools", "Handle CSV files.", "Parse and write CSV.");
        AgentSkill skill = AgentSkill.fromDirectory(skillDir);
        String prompt = skill.toPrompt();

        assertThat(prompt).contains("# Skill: csv-tools");
        assertThat(prompt).contains("## Description");
        assertThat(prompt).contains("Handle CSV files.");
        assertThat(prompt).contains("## Instructions");
        assertThat(prompt).contains("Parse and write CSV.");
    }

    // -----------------------------------------------------------------------
    // SkillRegistry
    // -----------------------------------------------------------------------

    @Test
    void registryDiscoverSkipsNonDirs(@TempDir Path tmp) throws IOException {
        // A file (not directory) at the search path level must be ignored.
        Files.writeString(tmp.resolve("not_a_dir.md"), "ignored", StandardCharsets.UTF_8);
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        registry.discoverSkills();

        assertThat(registry.getSkills()).isEmpty();
    }

    @Test
    void registryDiscoversValidSkills(@TempDir Path tmp) throws IOException {
        makeSkillDir(tmp, "skill-a", "Skill A description.");
        makeSkillDir(tmp, "skill-b", "Skill B description.");
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        registry.discoverSkills();

        assertThat(registry.getSkills()).containsKeys("skill-a", "skill-b");
    }

    @Test
    void registryDiscoverSkipsInvalidSkills(@TempDir Path tmp) throws IOException {
        makeSkillDir(tmp, "good", "A valid skill.");
        // Invalid: present SKILL.md but missing the required 'name' field.
        Path bad = tmp.resolve("bad");
        Files.createDirectories(bad);
        Files.writeString(bad.resolve("SKILL.md"),
                "---\ndescription: missing name.\n---\nbody", StandardCharsets.UTF_8);

        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        registry.discoverSkills();

        assertThat(registry.getSkills()).containsKey("good");
        assertThat(registry.getSkills()).hasSize(1);
    }

    @Test
    void registryFindRelevantNameMatch(@TempDir Path tmp) throws IOException {
        makeSkillDir(tmp, "pdf-processing", "Work with PDF documents.");
        makeSkillDir(tmp, "csv-tools", "Handle CSV spreadsheets.");
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        registry.discoverSkills();

        List<AgentSkill> results = registry.findRelevantSkills("pdf");
        assertThat(results).isNotEmpty();
        assertThat(results.get(0).getName()).isEqualTo("pdf-processing");
    }

    @Test
    void registryFindRelevantMaxResults(@TempDir Path tmp) throws IOException {
        for (int i = 0; i < 6; i++) {
            makeSkillDir(tmp, "skill-" + i, "A skill about document processing number " + i + ".");
        }
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        registry.discoverSkills();

        List<AgentSkill> results = registry.findRelevantSkills("document", 3);
        assertThat(results).hasSizeLessThanOrEqualTo(3);
    }

    @Test
    void registryGetSkill(@TempDir Path tmp) throws IOException {
        makeSkillDir(tmp, "email-compose", "Compose professional emails.");
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        registry.discoverSkills();

        assertThat(registry.getSkill("email-compose"))
                .hasValueSatisfying(s -> assertThat(s.getName()).isEqualTo("email-compose"));
        assertThat(registry.getSkill("nonexistent")).isEmpty();
    }
}
