package patterns

import (
	"context"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// extendedMockAgent provides more flexible mocking for comprehensive tests
type extendedMockAgent struct {
	name         string
	response     string
	err          error
	capabilities []string
	processFunc  func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error)
}

func (m *extendedMockAgent) Name() string {
	return m.name
}

func (m *extendedMockAgent) Capabilities() []string {
	if m.capabilities != nil {
		return m.capabilities
	}
	return []string{"mock"}
}

func (m *extendedMockAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *extendedMockAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	if m.processFunc != nil {
		return m.processFunc(ctx, msg)
	}
	if m.err != nil {
		return nil, m.err
	}
	return agenkit.NewMessage("assistant", m.response), nil
}
