// Package testutil provides shared test helpers for agenkit-go tests.
//
// Use these helpers instead of defining per-file mock types so that changes
// to the Agent interface only need to be updated in one place.
package testutil

import (
	"context"
	"fmt"
	"sync/atomic"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// MockAgent is a thread-safe test double for the agenkit.Agent interface.
// It cycles through a list of configured responses and records every call.
type MockAgent struct {
	name         string
	capabilities []string
	responses    []string
	callCount    atomic.Int64
	shouldFail   bool
	failErr      error
}

// MockAgentOption is a functional option for MockAgent.
type MockAgentOption func(*MockAgent)

// WithCapabilities sets the capabilities returned by the mock.
func WithCapabilities(caps ...string) MockAgentOption {
	return func(m *MockAgent) { m.capabilities = caps }
}

// WithFailure configures the mock to return an error on every call.
func WithFailure(err error) MockAgentOption {
	return func(m *MockAgent) {
		m.shouldFail = true
		m.failErr = err
	}
}

// NewMockAgent creates a MockAgent that cycles through the given responses.
// If no responses are provided, it defaults to "mock response".
func NewMockAgent(name string, responses []string, opts ...MockAgentOption) *MockAgent {
	if len(responses) == 0 {
		responses = []string{"mock response"}
	}
	m := &MockAgent{
		name:         name,
		capabilities: []string{"mock"},
		responses:    responses,
	}
	for _, opt := range opts {
		opt(m)
	}
	return m
}

// Name implements agenkit.Agent.
func (m *MockAgent) Name() string { return m.name }

// Capabilities implements agenkit.Agent.
func (m *MockAgent) Capabilities() []string { return m.capabilities }

// Introspect implements agenkit.Agent.
func (m *MockAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{AgentName: m.name}
}

// Process implements agenkit.Agent. Returns the next cycling response.
func (m *MockAgent) Process(_ context.Context, _ *agenkit.Message) (*agenkit.Message, error) {
	idx := m.callCount.Add(1) - 1
	if m.shouldFail {
		if m.failErr != nil {
			return nil, m.failErr
		}
		return nil, fmt.Errorf("mock agent %q: configured to fail", m.name)
	}
	resp := m.responses[idx%int64(len(m.responses))]
	return agenkit.NewMessage("agent", resp), nil
}

// CallCount returns the number of times Process has been called.
func (m *MockAgent) CallCount() int64 { return m.callCount.Load() }
