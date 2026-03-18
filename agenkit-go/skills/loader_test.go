package skills

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// makeSkillDir creates a minimal valid skill directory inside parent.
func makeSkillDir(t *testing.T, parent, name, description, body string) string {
	t.Helper()
	skillDir := filepath.Join(parent, name)
	require.NoError(t, os.MkdirAll(skillDir, 0o755))
	content := "---\nname: " + name + "\ndescription: " + description + "\n---\n" + body
	require.NoError(t, os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(content), 0o644))
	return skillDir
}

// ---------------------------------------------------------------------------
// LoadSkill
// ---------------------------------------------------------------------------

func TestLoadSkill_Valid(t *testing.T) {
	dir := t.TempDir()
	skillDir := makeSkillDir(t, dir, "pdf-processing", "Extract text from PDFs.", "# PDF\nDo stuff.")

	skill, err := LoadSkill(skillDir)
	require.NoError(t, err)
	assert.Equal(t, "pdf-processing", skill.Name)
	assert.Equal(t, "Extract text from PDFs.", skill.Description)
	assert.Contains(t, skill.Instructions, "Do stuff.")
	assert.Equal(t, skillDir, skill.SkillDir)
}

func TestLoadSkill_WithLicenseAndMetadata(t *testing.T) {
	dir := t.TempDir()
	skillDir := dir + "/advanced"
	require.NoError(t, os.MkdirAll(skillDir, 0o755))
	content := "---\nname: advanced\ndescription: Advanced skill.\nlicense: Apache-2.0\nmetadata:\n  version: \"1.0\"\n---\nAdvanced instructions."
	require.NoError(t, os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(content), 0o644))

	skill, err := LoadSkill(skillDir)
	require.NoError(t, err)
	assert.Equal(t, "Apache-2.0", skill.License)
	assert.Equal(t, "1.0", skill.Metadata["version"])
}

func TestLoadSkill_MissingSkillMd(t *testing.T) {
	dir := t.TempDir()
	emptyDir := filepath.Join(dir, "empty")
	require.NoError(t, os.MkdirAll(emptyDir, 0o755))

	_, err := LoadSkill(emptyDir)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "no SKILL.md found")
}

func TestLoadSkill_InvalidFrontmatter(t *testing.T) {
	dir := t.TempDir()
	skillDir := filepath.Join(dir, "bad")
	require.NoError(t, os.MkdirAll(skillDir, 0o755))
	// No "---" delimiters — invalid format.
	require.NoError(t, os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte("name: foo\ndescription: bar\n"), 0o644))

	_, err := LoadSkill(skillDir)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "missing frontmatter delimiters")
}

func TestLoadSkill_MissingName(t *testing.T) {
	dir := t.TempDir()
	skillDir := filepath.Join(dir, "noname")
	require.NoError(t, os.MkdirAll(skillDir, 0o755))
	content := "---\ndescription: A skill without a name.\n---\nInstructions."
	require.NoError(t, os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(content), 0o644))

	_, err := LoadSkill(skillDir)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "missing required field 'name'")
}

func TestLoadSkill_MissingDescription(t *testing.T) {
	dir := t.TempDir()
	skillDir := filepath.Join(dir, "nodesc")
	require.NoError(t, os.MkdirAll(skillDir, 0o755))
	content := "---\nname: nodesc\n---\nInstructions."
	require.NoError(t, os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(content), 0o644))

	_, err := LoadSkill(skillDir)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "missing required field 'description'")
}

func TestSkill_ToPrompt(t *testing.T) {
	dir := t.TempDir()
	skillDir := makeSkillDir(t, dir, "csv-tools", "Handle CSV files.", "Parse and write CSV.")
	skill, err := LoadSkill(skillDir)
	require.NoError(t, err)

	prompt := skill.ToPrompt()
	assert.Contains(t, prompt, "# Skill: csv-tools")
	assert.Contains(t, prompt, "## Description")
	assert.Contains(t, prompt, "Handle CSV files.")
	assert.Contains(t, prompt, "## Instructions")
	assert.Contains(t, prompt, "Parse and write CSV.")
}

// ---------------------------------------------------------------------------
// SkillRegistry
// ---------------------------------------------------------------------------

func TestRegistry_DiscoverSkipsNonDirs(t *testing.T) {
	dir := t.TempDir()
	// Create a file (not a directory) at the search path level.
	require.NoError(t, os.WriteFile(filepath.Join(dir, "not_a_dir.md"), []byte("ignored"), 0o644))

	registry := NewSkillRegistry([]string{dir})
	require.NoError(t, registry.DiscoverSkills())
	assert.Empty(t, registry.skills)
}

func TestRegistry_DiscoversValidSkills(t *testing.T) {
	dir := t.TempDir()
	makeSkillDir(t, dir, "skill-a", "Skill A description.", "")
	makeSkillDir(t, dir, "skill-b", "Skill B description.", "")

	registry := NewSkillRegistry([]string{dir})
	require.NoError(t, registry.DiscoverSkills())

	_, okA := registry.GetSkill("skill-a")
	_, okB := registry.GetSkill("skill-b")
	assert.True(t, okA)
	assert.True(t, okB)
}

func TestRegistry_FindRelevantNameMatch(t *testing.T) {
	dir := t.TempDir()
	makeSkillDir(t, dir, "pdf-processing", "Work with PDF documents.", "")
	makeSkillDir(t, dir, "csv-tools", "Handle CSV spreadsheets.", "")

	registry := NewSkillRegistry([]string{dir})
	require.NoError(t, registry.DiscoverSkills())

	results := registry.FindRelevantSkills("pdf", 5)
	require.NotEmpty(t, results)
	assert.Equal(t, "pdf-processing", results[0].Name)
}

func TestRegistry_FindRelevantMaxResults(t *testing.T) {
	dir := t.TempDir()
	for i := 0; i < 6; i++ {
		name := filepath.Join(dir)
		_ = name
		makeSkillDir(t, dir, filepath.Base(t.TempDir())+"-skill", "A skill about document processing.", "")
	}

	registry := NewSkillRegistry([]string{dir})
	require.NoError(t, registry.DiscoverSkills())

	results := registry.FindRelevantSkills("document", 3)
	assert.LessOrEqual(t, len(results), 3)
}

func TestRegistry_GetSkill(t *testing.T) {
	dir := t.TempDir()
	makeSkillDir(t, dir, "email-compose", "Compose professional emails.", "")

	registry := NewSkillRegistry([]string{dir})
	require.NoError(t, registry.DiscoverSkills())

	skill, ok := registry.GetSkill("email-compose")
	require.True(t, ok)
	assert.Equal(t, "email-compose", skill.Name)

	_, missing := registry.GetSkill("nonexistent")
	assert.False(t, missing)
}
