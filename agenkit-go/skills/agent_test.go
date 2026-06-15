package skills

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	agenkit "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// echoAgent returns the message content as-is.
type echoAgent struct{}

func (e *echoAgent) Name() string { return "echo" }

func (e *echoAgent) Process(_ context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	out := agenkit.NewMessage("agent", msg.ContentString())
	for k, v := range msg.Metadata {
		out.WithMetadata(k, v)
	}
	return out, nil
}

func (e *echoAgent) Capabilities() []string { return []string{} }
func (e *echoAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(e)
}

func TestSkillEnabledAgent_AugmentsMessage(t *testing.T) {
	dir := t.TempDir()
	makeSkillDir(t, dir, "pdf-processing", "Extract text from PDF documents.", "")

	registry := NewSkillRegistry([]string{dir})
	require.NoError(t, registry.DiscoverSkills())

	agent := NewSkillEnabledAgent(&echoAgent{}, registry)
	msg := agenkit.NewMessage("user", "How do I parse pdf files?")
	resp, err := agent.Process(context.Background(), msg)
	require.NoError(t, err)

	assert.Contains(t, resp.ContentString(), "<available_skills>")
	assert.Contains(t, resp.ContentString(), "pdf-processing")
}

func TestSkillEnabledAgent_NoSkillsPassthrough(t *testing.T) {
	dir := t.TempDir()
	skillDir := filepath.Join(dir, "email-compose")
	require.NoError(t, os.MkdirAll(skillDir, 0o755))
	content := "---\nname: email-compose\ndescription: Compose professional emails.\n---\nInstructions."
	require.NoError(t, os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(content), 0o644))

	registry := NewSkillRegistry([]string{dir})
	require.NoError(t, registry.DiscoverSkills())

	agent := NewSkillEnabledAgent(&echoAgent{}, registry)
	msg := agenkit.NewMessage("user", "tell me a joke")
	resp, err := agent.Process(context.Background(), msg)
	require.NoError(t, err)

	assert.NotContains(t, resp.ContentString(), "<available_skills>")
	assert.Equal(t, "tell me a joke", resp.ContentString())
}

func TestSkillEnabledAgent_ActiveSkillsMetadata(t *testing.T) {
	dir := t.TempDir()
	makeSkillDir(t, dir, "csv-tools", "Handle and transform CSV spreadsheets.", "")

	registry := NewSkillRegistry([]string{dir})
	require.NoError(t, registry.DiscoverSkills())

	agent := NewSkillEnabledAgent(&echoAgent{}, registry)
	msg := agenkit.NewMessage("user", "parse this csv spreadsheet data")
	resp, err := agent.Process(context.Background(), msg)
	require.NoError(t, err)

	activeSkills, ok := resp.Metadata["active_skills"]
	require.True(t, ok, "active_skills metadata should be set")
	assert.Contains(t, activeSkills.(string), "csv-tools")
}

func TestSkillEnabledAgent_Capabilities(t *testing.T) {
	dir := t.TempDir()
	registry := NewSkillRegistry([]string{dir})
	agent := NewSkillEnabledAgent(&echoAgent{}, registry)

	caps := agent.Capabilities()
	found := false
	for _, c := range caps {
		if c == "skill_injection" {
			found = true
			break
		}
	}
	assert.True(t, found, "capabilities should include 'skill_injection'")
}

func TestSkillEnabledAgent_NameDelegates(t *testing.T) {
	dir := t.TempDir()
	registry := NewSkillRegistry([]string{dir})
	agent := NewSkillEnabledAgent(&echoAgent{}, registry)
	assert.Equal(t, "echo", agent.Name())
}

func TestSkillEnabledAgent_WithMaxActiveSkills(t *testing.T) {
	dir := t.TempDir()
	for i := 0; i < 5; i++ {
		name := strings.ToLower(filepath.Base(dir)) + "-skill-" + string(rune('a'+i))
		makeSkillDir(t, dir, name, "A skill about document processing tasks.", "")
	}

	registry := NewSkillRegistry([]string{dir})
	require.NoError(t, registry.DiscoverSkills())

	agent := NewSkillEnabledAgent(&echoAgent{}, registry, WithMaxActiveSkills(2))
	msg := agenkit.NewMessage("user", "help me with document processing tasks")
	resp, err := agent.Process(context.Background(), msg)
	require.NoError(t, err)

	// Count occurrences of "# Skill:" in the response.
	count := strings.Count(resp.ContentString(), "# Skill:")
	assert.LessOrEqual(t, count, 2)
}
