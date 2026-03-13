package testutil

import (
	"context"
	"fmt"
	"sync/atomic"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// MockLLMClient is a configurable test double for LLM adapters.
// It satisfies the same Process/Complete interface as real adapters and
// records all calls for assertion in tests.
type MockLLMClient struct {
	responses []string
	callCount atomic.Int64
	failCalls map[int64]bool
	failErr   error
}

// MockLLMOption is a functional option for MockLLMClient.
type MockLLMOption func(*MockLLMClient)

// WithLLMFailure marks specific 0-based call indices to return an error.
func WithLLMFailure(indices []int64, err error) MockLLMOption {
	return func(m *MockLLMClient) {
		m.failCalls = make(map[int64]bool)
		for _, i := range indices {
			m.failCalls[i] = true
		}
		m.failErr = err
	}
}

// NewMockLLMClient creates a client that cycles through the given responses.
// If no responses are provided, it defaults to "mock llm response".
func NewMockLLMClient(responses []string, opts ...MockLLMOption) *MockLLMClient {
	if len(responses) == 0 {
		responses = []string{"mock llm response"}
	}
	m := &MockLLMClient{
		responses: responses,
		failCalls: make(map[int64]bool),
	}
	for _, opt := range opts {
		opt(m)
	}
	return m
}

// Process implements the agenkit.Agent Process interface so MockLLMClient
// can be used anywhere an agent is expected.
func (m *MockLLMClient) Process(_ context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	idx := m.callCount.Add(1) - 1
	if m.failCalls[idx] {
		if m.failErr != nil {
			return nil, m.failErr
		}
		return nil, fmt.Errorf("mock llm: configured failure at call %d", idx)
	}
	resp := m.responses[idx%int64(len(m.responses))]
	reply := agenkit.NewMessage("assistant", resp)
	reply.Metadata["model"] = "mock"
	reply.Metadata["input_tokens"] = int64(len(msg.Content) / 4)
	reply.Metadata["output_tokens"] = int64(len(resp) / 4)
	reply.Metadata["stop_reason"] = "end_turn"
	return reply, nil
}

// Name satisfies a minimal Agent interface for use in infrastructure tests.
func (m *MockLLMClient) Name() string { return "mock_llm" }

// Capabilities satisfies a minimal Agent interface.
func (m *MockLLMClient) Capabilities() []string { return []string{"mock", "llm"} }

// Introspect satisfies the full agenkit.Agent interface.
func (m *MockLLMClient) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{AgentName: "mock_llm"}
}

// CallCount returns the number of calls made so far.
func (m *MockLLMClient) CallCount() int64 { return m.callCount.Load() }
