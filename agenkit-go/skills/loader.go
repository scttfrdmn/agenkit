// Package skills provides support for the Agent Skills specification.
//
// An agent skill is a directory containing a SKILL.md file with YAML
// frontmatter (name, description, optional license and metadata fields)
// followed by Markdown instructions.
package skills

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// AgentSkill represents a single loaded agent skill.
type AgentSkill struct {
	Name         string
	Description  string
	Instructions string
	License      string
	Metadata     map[string]interface{}
	SkillDir     string
}

// frontmatter holds YAML-parsed fields from SKILL.md.
type frontmatter struct {
	Name        string                 `yaml:"name"`
	Description string                 `yaml:"description"`
	License     string                 `yaml:"license,omitempty"`
	Metadata    map[string]interface{} `yaml:"metadata,omitempty"`
}

// LoadSkill reads a skill directory, parses its SKILL.md, and returns an
// AgentSkill.  Returns an error if the directory lacks a SKILL.md, has
// invalid YAML frontmatter, or is missing the required name/description.
func LoadSkill(skillDir string) (*AgentSkill, error) {
	skillFile := filepath.Join(skillDir, "SKILL.md")
	data, err := os.ReadFile(skillFile)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("no SKILL.md found in %s", skillDir)
		}
		return nil, fmt.Errorf("reading SKILL.md in %s: %w", skillDir, err)
	}

	raw := string(data)
	// File must start with "---"; split on "---" expecting at least 3 parts.
	parts := strings.SplitN(raw, "---", 3)
	if len(parts) < 3 {
		return nil, fmt.Errorf("invalid SKILL.md in %s: missing frontmatter delimiters", skillDir)
	}

	frontmatterText := strings.TrimSpace(parts[1])
	instructions := strings.TrimSpace(parts[2])

	var fm frontmatter
	if err := yaml.Unmarshal([]byte(frontmatterText), &fm); err != nil {
		return nil, fmt.Errorf("invalid YAML frontmatter in %s/SKILL.md: %w", skillDir, err)
	}

	if fm.Name == "" {
		return nil, fmt.Errorf("missing required field 'name' in %s/SKILL.md", skillDir)
	}
	if fm.Description == "" {
		return nil, fmt.Errorf("missing required field 'description' in %s/SKILL.md", skillDir)
	}

	skill := &AgentSkill{
		Name:         fm.Name,
		Description:  fm.Description,
		Instructions: instructions,
		License:      fm.License,
		SkillDir:     skillDir,
	}
	if fm.Metadata != nil {
		skill.Metadata = fm.Metadata
	} else {
		skill.Metadata = make(map[string]interface{})
	}
	return skill, nil
}

// ToPrompt renders the skill as a prompt block for injection into agent messages.
func (s *AgentSkill) ToPrompt() string {
	return fmt.Sprintf(
		"# Skill: %s\n\n## Description\n%s\n\n## Instructions\n%s\n",
		s.Name, s.Description, s.Instructions,
	)
}

// SkillRegistry discovers and searches agent skills across filesystem paths.
type SkillRegistry struct {
	searchPaths []string
	skills      map[string]*AgentSkill
}

// NewSkillRegistry creates a new SkillRegistry with the given search paths.
func NewSkillRegistry(searchPaths []string) *SkillRegistry {
	return &SkillRegistry{
		searchPaths: searchPaths,
		skills:      make(map[string]*AgentSkill),
	}
}

// DiscoverSkills walks each search path and loads all valid skill directories.
// Invalid skill directories are skipped without returning an error.
func (r *SkillRegistry) DiscoverSkills() error {
	for _, searchPath := range r.searchPaths {
		entries, err := os.ReadDir(searchPath)
		if err != nil {
			// Non-fatal: skip missing search paths.
			continue
		}
		for _, entry := range entries {
			if !entry.IsDir() {
				continue
			}
			skillDir := filepath.Join(searchPath, entry.Name())
			if _, statErr := os.Stat(filepath.Join(skillDir, "SKILL.md")); os.IsNotExist(statErr) {
				continue
			}
			skill, loadErr := LoadSkill(skillDir)
			if loadErr != nil {
				// Skip invalid skill directories.
				continue
			}
			r.skills[skill.Name] = skill
		}
	}
	return nil
}

// FindRelevantSkills returns up to maxResults skills most relevant to query.
//
// Scoring:
//   - +10 if query (lowercased) is contained in the skill name
//   - +5  if query (lowercased) is contained in the skill description
//   - +N  for each word in query that also appears in the description
//
// Only skills with score > 0 are returned, ordered best-first.
func (r *SkillRegistry) FindRelevantSkills(query string, maxResults int) []*AgentSkill {
	queryLower := strings.ToLower(query)
	queryWords := strings.Fields(queryLower)

	type scored struct {
		score int
		skill *AgentSkill
	}

	var results []scored
	for _, skill := range r.skills {
		score := 0
		nameLower := strings.ToLower(skill.Name)
		descLower := strings.ToLower(skill.Description)

		if strings.Contains(nameLower, queryLower) {
			score += 10
		}
		if strings.Contains(descLower, queryLower) {
			score += 5
		}

		descWords := strings.Fields(descLower)
		descWordSet := make(map[string]struct{}, len(descWords))
		for _, w := range descWords {
			descWordSet[w] = struct{}{}
		}
		for _, w := range queryWords {
			if _, ok := descWordSet[w]; ok {
				score++
			}
		}

		if score > 0 {
			results = append(results, scored{score: score, skill: skill})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].score > results[j].score
	})

	if maxResults > 0 && len(results) > maxResults {
		results = results[:maxResults]
	}

	out := make([]*AgentSkill, len(results))
	for i, s := range results {
		out[i] = s.skill
	}
	return out
}

// GetSkill returns the skill with the given name, or (nil, false) if not found.
func (r *SkillRegistry) GetSkill(name string) (*AgentSkill, bool) {
	s, ok := r.skills[name]
	return s, ok
}

// All returns all loaded skills as an unordered slice.
func (r *SkillRegistry) All() []*AgentSkill {
	out := make([]*AgentSkill, 0, len(r.skills))
	for _, s := range r.skills {
		out = append(out, s)
	}
	return out
}
