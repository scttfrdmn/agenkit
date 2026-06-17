package skills

import (
	"context"
	"strings"
	"time"

	agenkit "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// SkillEnabledAgent wraps an Agent and injects relevant skill instructions
// into each incoming message before delegating to the wrapped agent.
type SkillEnabledAgent struct {
	agent           agenkit.Agent
	registry        *SkillRegistry
	maxActiveSkills int
}

// SkillEnabledAgentOption is a functional option for SkillEnabledAgent.
type SkillEnabledAgentOption func(*SkillEnabledAgent)

// WithMaxActiveSkills sets the maximum number of skills to inject per message.
func WithMaxActiveSkills(n int) SkillEnabledAgentOption {
	return func(s *SkillEnabledAgent) {
		s.maxActiveSkills = n
	}
}

// NewSkillEnabledAgent creates a SkillEnabledAgent wrapping the given agent.
// Default maxActiveSkills is 3.
func NewSkillEnabledAgent(agent agenkit.Agent, registry *SkillRegistry, opts ...SkillEnabledAgentOption) *SkillEnabledAgent {
	s := &SkillEnabledAgent{
		agent:           agent,
		registry:        registry,
		maxActiveSkills: 3,
	}
	for _, opt := range opts {
		opt(s)
	}
	return s
}

// Name returns the name of the wrapped agent.
func (s *SkillEnabledAgent) Name() string {
	return s.agent.Name()
}

// Capabilities returns the wrapped agent's capabilities plus "skill_injection".
func (s *SkillEnabledAgent) Capabilities() []string {
	base := s.agent.Capabilities()
	for _, c := range base {
		if c == "skill_injection" {
			return base
		}
	}
	return append(base, "skill_injection")
}

// Introspect delegates to the wrapped agent's introspect method.
func (s *SkillEnabledAgent) Introspect() *agenkit.IntrospectionResult {
	return s.agent.Introspect()
}

// Process finds relevant skills for the message content, prepends an
// <available_skills> block if any are found, and delegates to the wrapped agent.
// The returned message's metadata will contain "active_skills".
func (s *SkillEnabledAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	query := message.ContentString()
	relevant := s.registry.FindRelevantSkills(query, s.maxActiveSkills)

	if len(relevant) == 0 {
		return s.agent.Process(ctx, message)
	}

	// Build <available_skills> prefix.
	var sb strings.Builder
	sb.WriteString("<available_skills>\n")
	for _, skill := range relevant {
		sb.WriteString(skill.ToPrompt())
		sb.WriteString("\n")
	}
	sb.WriteString("</available_skills>\n\n")
	sb.WriteString(query)

	// Build active skill names list.
	activeNames := make([]string, len(relevant))
	for i, skill := range relevant {
		activeNames[i] = skill.Name
	}

	// Build enhanced message with augmented content and active_skills metadata.
	enhanced := &agenkit.Message{
		Role:      message.Role,
		Content:   sb.String(),
		Timestamp: time.Now().UTC(),
		Metadata:  make(map[string]interface{}),
	}
	for k, v := range message.Metadata {
		enhanced.Metadata[k] = v
	}
	enhanced.Metadata["active_skills"] = strings.Join(activeNames, ",")

	return s.agent.Process(ctx, enhanced)
}
