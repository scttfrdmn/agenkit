package patterns

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Mock agent for testing
type mockAgent struct {
	name    string
	prefix  string
	failErr error
}

func (m *mockAgent) Name() string {
	return m.name
}

func (m *mockAgent) Capabilities() []string {
	return []string{m.name + "_cap"}
}

func (m *mockAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *mockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.failErr != nil {
		return nil, m.failErr
	}
	return &agenkit.Message{
		Role:    "assistant",
		Content: m.prefix + message.Content,
	}, nil
}

// Test helpers
func assertEqual(t *testing.T, got, want interface{}) {
	t.Helper()
	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

func assertError(t *testing.T, err error, wantErr bool) {
	t.Helper()
	if (err != nil) != wantErr {
		t.Errorf("error = %v, wantErr %v", err, wantErr)
	}
}

func assertContains(t *testing.T, s, substr string) {
	t.Helper()
	if !strings.Contains(s, substr) {
		t.Errorf("string %q does not contain %q", s, substr)
	}
}

// ============================================================================
// SequentialPattern Tests
// ============================================================================

func TestSequentialPattern_Creation(t *testing.T) {
	agent1 := &mockAgent{name: "agent1", prefix: "A:"}
	agent2 := &mockAgent{name: "agent2", prefix: "B:"}

	pattern, err := NewSequentialPattern([]agenkit.Agent{agent1, agent2}, nil)
	assertError(t, err, false)
	assertEqual(t, pattern.Name(), "sequential")
}

func TestSequentialPattern_EmptyAgents(t *testing.T) {
	_, err := NewSequentialPattern([]agenkit.Agent{}, nil)
	assertError(t, err, true)
}

func TestSequentialPattern_CustomName(t *testing.T) {
	agent := &mockAgent{name: "agent1", prefix: "A:"}
	config := &SequentialPatternConfig{Name: "my-pipeline"}

	pattern, err := NewSequentialPattern([]agenkit.Agent{agent}, config)
	assertError(t, err, false)
	assertEqual(t, pattern.Name(), "my-pipeline")
}

func TestSequentialPattern_Process(t *testing.T) {
	agent1 := &mockAgent{name: "agent1", prefix: "A:"}
	agent2 := &mockAgent{name: "agent2", prefix: "B:"}

	pattern, _ := NewSequentialPattern([]agenkit.Agent{agent1, agent2}, nil)

	result, err := pattern.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "test",
	})

	assertError(t, err, false)
	assertEqual(t, result.Content, "B:A:test")
}

func TestSequentialPattern_ThreeAgents(t *testing.T) {
	agent1 := &mockAgent{name: "agent1", prefix: "A:"}
	agent2 := &mockAgent{name: "agent2", prefix: "B:"}
	agent3 := &mockAgent{name: "agent3", prefix: "C:"}

	pattern, _ := NewSequentialPattern([]agenkit.Agent{agent1, agent2, agent3}, nil)

	result, err := pattern.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "test",
	})

	assertError(t, err, false)
	assertEqual(t, result.Content, "C:B:A:test")
}

func TestSequentialPattern_ErrorPropagation(t *testing.T) {
	agent1 := &mockAgent{name: "agent1", prefix: "A:"}
	agent2 := &mockAgent{name: "agent2", prefix: "B:", failErr: fmt.Errorf("agent2 failed")}
	agent3 := &mockAgent{name: "agent3", prefix: "C:"}

	pattern, _ := NewSequentialPattern([]agenkit.Agent{agent1, agent2, agent3}, nil)

	_, err := pattern.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "test",
	})

	assertError(t, err, true)
}

func TestSequentialPattern_Capabilities(t *testing.T) {
	agent1 := &mockAgent{name: "agent1"}
	agent2 := &mockAgent{name: "agent2"}

	pattern, _ := NewSequentialPattern([]agenkit.Agent{agent1, agent2}, nil)

	caps := pattern.Capabilities()
	if len(caps) != 2 {
		t.Errorf("expected 2 capabilities, got %d", len(caps))
	}
}

func TestSequentialPattern_BeforeHook(t *testing.T) {
	agent := &mockAgent{name: "agent1", prefix: "A:"}
	called := 0

	config := &SequentialPatternConfig{
		BeforeAgent: func(a agenkit.Agent, m *agenkit.Message) {
			called++
		},
	}

	pattern, _ := NewSequentialPattern([]agenkit.Agent{agent}, config)
	_, _ = pattern.Process(context.Background(), &agenkit.Message{Role: "user", Content: "test"})

	assertEqual(t, called, 1)
}

func TestSequentialPattern_AfterHook(t *testing.T) {
	agent := &mockAgent{name: "agent1", prefix: "A:"}
	called := 0

	config := &SequentialPatternConfig{
		AfterAgent: func(a agenkit.Agent, m *agenkit.Message) {
			called++
		},
	}

	pattern, _ := NewSequentialPattern([]agenkit.Agent{agent}, config)
	_, _ = pattern.Process(context.Background(), &agenkit.Message{Role: "user", Content: "test"})

	assertEqual(t, called, 1)
}

func TestSequentialPattern_Unwrap(t *testing.T) {
	agent1 := &mockAgent{name: "agent1"}
	agent2 := &mockAgent{name: "agent2"}
	agents := []agenkit.Agent{agent1, agent2}

	pattern, _ := NewSequentialPattern(agents, nil)
	unwrapped := pattern.Unwrap()

	assertEqual(t, len(unwrapped), 2)
	assertEqual(t, unwrapped[0].Name(), "agent1")
	assertEqual(t, unwrapped[1].Name(), "agent2")
}

// ============================================================================
// ParallelPattern Tests
// ============================================================================

func TestParallelPattern_Creation(t *testing.T) {
	agent1 := &mockAgent{name: "agent1", prefix: "A:"}
	agent2 := &mockAgent{name: "agent2", prefix: "B:"}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		return &agenkit.Message{Role: "assistant", Content: "aggregated"}
	}

	pattern, err := NewParallelPattern([]agenkit.Agent{agent1, agent2}, aggregator, nil)
	assertError(t, err, false)
	assertEqual(t, pattern.Name(), "parallel")
}

func TestParallelPattern_EmptyAgents(t *testing.T) {
	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		return &agenkit.Message{Role: "assistant", Content: "aggregated"}
	}

	_, err := NewParallelPattern([]agenkit.Agent{}, aggregator, nil)
	assertError(t, err, true)
}

func TestParallelPattern_NilAggregator(t *testing.T) {
	agent := &mockAgent{name: "agent1"}

	_, err := NewParallelPattern([]agenkit.Agent{agent}, nil, nil)
	assertError(t, err, true)
}

func TestParallelPattern_Process(t *testing.T) {
	agent1 := &mockAgent{name: "agent1", prefix: "A:"}
	agent2 := &mockAgent{name: "agent2", prefix: "B:"}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		combined := ""
		for _, msg := range messages {
			combined += msg.Content + ","
		}
		return &agenkit.Message{Role: "assistant", Content: combined}
	}

	pattern, _ := NewParallelPattern([]agenkit.Agent{agent1, agent2}, aggregator, nil)

	result, err := pattern.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "test",
	})

	assertError(t, err, false)
	assertContains(t, result.Content, "A:test")
	assertContains(t, result.Content, "B:test")
}

func TestParallelPattern_ErrorHandling(t *testing.T) {
	agent1 := &mockAgent{name: "agent1", prefix: "A:"}
	agent2 := &mockAgent{name: "agent2", failErr: fmt.Errorf("agent2 failed")}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		return &agenkit.Message{Role: "assistant", Content: "aggregated"}
	}

	pattern, _ := NewParallelPattern([]agenkit.Agent{agent1, agent2}, aggregator, nil)

	_, err := pattern.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "test",
	})

	assertError(t, err, true)
}

func TestParallelPattern_Capabilities(t *testing.T) {
	agent1 := &mockAgent{name: "agent1"}
	agent2 := &mockAgent{name: "agent2"}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		return &agenkit.Message{Role: "assistant", Content: "aggregated"}
	}

	pattern, _ := NewParallelPattern([]agenkit.Agent{agent1, agent2}, aggregator, nil)

	caps := pattern.Capabilities()
	if len(caps) != 2 {
		t.Errorf("expected 2 capabilities, got %d", len(caps))
	}
}

func TestParallelPattern_Unwrap(t *testing.T) {
	agent1 := &mockAgent{name: "agent1"}
	agent2 := &mockAgent{name: "agent2"}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		return &agenkit.Message{Role: "assistant", Content: "aggregated"}
	}

	pattern, _ := NewParallelPattern([]agenkit.Agent{agent1, agent2}, aggregator, nil)
	unwrapped := pattern.Unwrap()

	assertEqual(t, len(unwrapped), 2)
}

// ============================================================================
// RouterPattern Tests
// ============================================================================

func TestRouterPattern_Creation(t *testing.T) {
	agent1 := &mockAgent{name: "agent1"}
	agent2 := &mockAgent{name: "agent2"}

	router := func(msg *agenkit.Message) string {
		return "agent1"
	}

	handlers := map[string]agenkit.Agent{
		"agent1": agent1,
		"agent2": agent2,
	}

	pattern, err := NewRouterPattern(router, handlers, nil)
	assertError(t, err, false)
	assertEqual(t, pattern.Name(), "router")
}

func TestRouterPattern_NilRouter(t *testing.T) {
	agent := &mockAgent{name: "agent1"}
	handlers := map[string]agenkit.Agent{"agent1": agent}

	_, err := NewRouterPattern(nil, handlers, nil)
	assertError(t, err, true)
}

func TestRouterPattern_EmptyHandlers(t *testing.T) {
	router := func(msg *agenkit.Message) string {
		return "agent1"
	}

	_, err := NewRouterPattern(router, map[string]agenkit.Agent{}, nil)
	assertError(t, err, true)
}

func TestRouterPattern_Process(t *testing.T) {
	agent1 := &mockAgent{name: "agent1", prefix: "A:"}
	agent2 := &mockAgent{name: "agent2", prefix: "B:"}

	router := func(msg *agenkit.Message) string {
		if strings.Contains(msg.Content, "route1") {
			return "agent1"
		}
		return "agent2"
	}

	handlers := map[string]agenkit.Agent{
		"agent1": agent1,
		"agent2": agent2,
	}

	pattern, _ := NewRouterPattern(router, handlers, nil)

	// Route to agent1
	result1, err := pattern.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "route1",
	})

	assertError(t, err, false)
	assertEqual(t, result1.Content, "A:route1")

	// Route to agent2
	result2, err := pattern.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "route2",
	})

	assertError(t, err, false)
	assertEqual(t, result2.Content, "B:route2")
}

func TestRouterPattern_UnknownKey(t *testing.T) {
	agent1 := &mockAgent{name: "agent1"}

	router := func(msg *agenkit.Message) string {
		return "unknown"
	}

	handlers := map[string]agenkit.Agent{
		"agent1": agent1,
	}

	pattern, _ := NewRouterPattern(router, handlers, nil)

	_, err := pattern.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "test",
	})

	assertError(t, err, true)
}

func TestRouterPattern_DefaultHandler(t *testing.T) {
	agent1 := &mockAgent{name: "agent1"}
	defaultAgent := &mockAgent{name: "default", prefix: "DEFAULT:"}

	router := func(msg *agenkit.Message) string {
		return "unknown"
	}

	handlers := map[string]agenkit.Agent{
		"agent1": agent1,
	}

	config := &RouterPatternConfig{
		DefaultHandler: defaultAgent,
	}

	pattern, _ := NewRouterPattern(router, handlers, config)

	result, err := pattern.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "test",
	})

	assertError(t, err, false)
	assertEqual(t, result.Content, "DEFAULT:test")
}

func TestRouterPattern_Capabilities(t *testing.T) {
	agent1 := &mockAgent{name: "agent1"}
	agent2 := &mockAgent{name: "agent2"}

	router := func(msg *agenkit.Message) string {
		return "agent1"
	}

	handlers := map[string]agenkit.Agent{
		"agent1": agent1,
		"agent2": agent2,
	}

	pattern, _ := NewRouterPattern(router, handlers, nil)

	caps := pattern.Capabilities()
	if len(caps) != 2 {
		t.Errorf("expected 2 capabilities, got %d", len(caps))
	}
}

func TestRouterPattern_Unwrap(t *testing.T) {
	agent1 := &mockAgent{name: "agent1"}
	agent2 := &mockAgent{name: "agent2"}

	router := func(msg *agenkit.Message) string {
		return "agent1"
	}

	handlers := map[string]agenkit.Agent{
		"agent1": agent1,
		"agent2": agent2,
	}

	pattern, _ := NewRouterPattern(router, handlers, nil)
	unwrapped := pattern.Unwrap()

	assertEqual(t, len(unwrapped), 2)
}

// ============================================================================
// Composition Tests
// ============================================================================

func TestComposition_SequentialOfParallel(t *testing.T) {
	agent1 := &mockAgent{name: "agent1", prefix: "A:"}
	agent2 := &mockAgent{name: "agent2", prefix: "B:"}
	agent3 := &mockAgent{name: "agent3", prefix: "C:"}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		return &agenkit.Message{Role: "assistant", Content: "parallel_result"}
	}

	parallel, _ := NewParallelPattern([]agenkit.Agent{agent1, agent2}, aggregator, nil)
	sequential, _ := NewSequentialPattern([]agenkit.Agent{parallel, agent3}, nil)

	result, err := sequential.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "test",
	})

	assertError(t, err, false)
	assertEqual(t, result.Content, "C:parallel_result")
}
