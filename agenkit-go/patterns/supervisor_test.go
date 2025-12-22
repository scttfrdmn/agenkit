package patterns

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mockPlanner implements PlannerAgent for testing
type mockPlanner struct {
	name         string
	subtasks     []Subtask
	planErr      error
	synthesized  string
	synthesisErr error
}

func (m *mockPlanner) Name() string {
	return m.name
}

func (m *mockPlanner) Capabilities() []string {
	return []string{"planning", "synthesis"}
}

func (m *mockPlanner) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *mockPlanner) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "direct response"), nil
}

func (m *mockPlanner) Plan(ctx context.Context, message *agenkit.Message) ([]Subtask, error) {
	if m.planErr != nil {
		return nil, m.planErr
	}
	return m.subtasks, nil
}

func (m *mockPlanner) Synthesize(ctx context.Context, original *agenkit.Message, results map[string]*agenkit.Message) (*agenkit.Message, error) {
	if m.synthesisErr != nil {
		return nil, m.synthesisErr
	}
	return agenkit.NewMessage("assistant", m.synthesized), nil
}

// TestSupervisorAgent_Constructor tests valid construction
func TestSupervisorAgent_Constructor(t *testing.T) {
	planner := &mockPlanner{name: "planner"}
	specialists := map[string]agenkit.Agent{
		"coder":  &extendedMockAgent{name: "coder", response: "code"},
		"tester": &extendedMockAgent{name: "tester", response: "tests"},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if supervisor == nil {
		t.Fatal("expected non-nil SupervisorAgent")
	}
	if supervisor.Name() != "SupervisorAgent" {
		t.Errorf("expected name 'SupervisorAgent', got '%s'", supervisor.Name())
	}
}

// TestSupervisorAgent_ConstructorNilPlanner tests error case with nil planner
func TestSupervisorAgent_ConstructorNilPlanner(t *testing.T) {
	specialists := map[string]agenkit.Agent{
		"coder": &extendedMockAgent{name: "coder"},
	}

	_, err := NewSupervisorAgent(nil, specialists)
	if err == nil {
		t.Fatal("expected error for nil planner")
	}
	if !strings.Contains(err.Error(), "planner") {
		t.Errorf("expected 'planner' error, got %v", err)
	}
}

// TestSupervisorAgent_ConstructorEmptySpecialists tests error case with no specialists
func TestSupervisorAgent_ConstructorEmptySpecialists(t *testing.T) {
	planner := &mockPlanner{name: "planner"}

	_, err := NewSupervisorAgent(planner, map[string]agenkit.Agent{})
	if err == nil {
		t.Fatal("expected error for empty specialists")
	}
	if !strings.Contains(err.Error(), "at least one specialist") {
		t.Errorf("expected 'at least one specialist' error, got %v", err)
	}
}

// TestSupervisorAgent_BasicProcess tests simple success case
func TestSupervisorAgent_BasicProcess(t *testing.T) {
	planner := &mockPlanner{
		name: "planner",
		subtasks: []Subtask{
			{Type: "coder", Message: agenkit.NewMessage("user", "write code")},
			{Type: "tester", Message: agenkit.NewMessage("user", "write tests")},
		},
		synthesized: "final synthesized result",
	}

	specialists := map[string]agenkit.Agent{
		"coder":  &extendedMockAgent{name: "coder", response: "code result"},
		"tester": &extendedMockAgent{name: "tester", response: "test result"},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "build a feature")
	result, err := supervisor.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "final synthesized result" {
		t.Errorf("expected 'final synthesized result', got '%s'", result.Content)
	}
}

// TestSupervisorAgent_NoSubtasks tests direct processing when no subtasks
func TestSupervisorAgent_NoSubtasks(t *testing.T) {
	planner := &mockPlanner{
		name:     "planner",
		subtasks: []Subtask{}, // Empty subtasks
	}

	specialists := map[string]agenkit.Agent{
		"coder": &extendedMockAgent{name: "coder"},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "simple task")
	result, err := supervisor.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should use planner's direct response
	if result.Content != "direct response" {
		t.Errorf("expected 'direct response', got '%s'", result.Content)
	}
}

// TestSupervisorAgent_Metadata tests metadata handling
func TestSupervisorAgent_Metadata(t *testing.T) {
	planner := &mockPlanner{
		name: "planner",
		subtasks: []Subtask{
			{Type: "worker1", Message: agenkit.NewMessage("user", "task1")},
			{Type: "worker2", Message: agenkit.NewMessage("user", "task2")},
		},
		synthesized: "result",
	}

	specialists := map[string]agenkit.Agent{
		"worker1": &extendedMockAgent{name: "w1", response: "r1"},
		"worker2": &extendedMockAgent{name: "w2", response: "r2"},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := supervisor.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check metadata
	if result.Metadata["supervisor_subtasks"] != 2 {
		t.Errorf("expected supervisor_subtasks=2, got %v", result.Metadata["supervisor_subtasks"])
	}
	if result.Metadata["supervisor_specialists"] != 2 {
		t.Errorf("expected supervisor_specialists=2, got %v", result.Metadata["supervisor_specialists"])
	}

	execOrder, ok := result.Metadata["execution_order"].([]map[string]interface{})
	if !ok {
		t.Fatal("expected execution_order in metadata")
	}
	if len(execOrder) != 2 {
		t.Errorf("expected 2 execution records, got %d", len(execOrder))
	}
}

// TestSupervisorAgent_PlanningError tests error in planning phase
func TestSupervisorAgent_PlanningError(t *testing.T) {
	planner := &mockPlanner{
		name:    "planner",
		planErr: errors.New("planning failed"),
	}

	specialists := map[string]agenkit.Agent{
		"worker": &extendedMockAgent{name: "worker"},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = supervisor.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from planning failure")
	}
	if !strings.Contains(err.Error(), "planning failed") {
		t.Errorf("expected planning error, got: %v", err)
	}
}

// TestSupervisorAgent_SpecialistError tests error in specialist execution
func TestSupervisorAgent_SpecialistError(t *testing.T) {
	planner := &mockPlanner{
		name: "planner",
		subtasks: []Subtask{
			{Type: "worker1", Message: agenkit.NewMessage("user", "task1")},
			{Type: "worker2", Message: agenkit.NewMessage("user", "task2")},
		},
	}

	specialists := map[string]agenkit.Agent{
		"worker1": &extendedMockAgent{name: "w1", response: "success"},
		"worker2": &extendedMockAgent{name: "w2", err: errors.New("worker2 failed")},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = supervisor.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from specialist failure")
	}
	if !strings.Contains(err.Error(), "worker2") || !strings.Contains(err.Error(), "failed") {
		t.Errorf("expected worker2 error, got: %v", err)
	}
}

// TestSupervisorAgent_SynthesisError tests error in synthesis phase
func TestSupervisorAgent_SynthesisError(t *testing.T) {
	planner := &mockPlanner{
		name: "planner",
		subtasks: []Subtask{
			{Type: "worker", Message: agenkit.NewMessage("user", "task")},
		},
		synthesisErr: errors.New("synthesis failed"),
	}

	specialists := map[string]agenkit.Agent{
		"worker": &extendedMockAgent{name: "worker", response: "success"},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = supervisor.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from synthesis failure")
	}
	if !strings.Contains(err.Error(), "synthesis failed") {
		t.Errorf("expected synthesis error, got: %v", err)
	}
}

// TestSupervisorAgent_UnknownSpecialistType tests error for unknown specialist
func TestSupervisorAgent_UnknownSpecialistType(t *testing.T) {
	planner := &mockPlanner{
		name: "planner",
		subtasks: []Subtask{
			{Type: "unknown_type", Message: agenkit.NewMessage("user", "task")},
		},
	}

	specialists := map[string]agenkit.Agent{
		"worker": &extendedMockAgent{name: "worker"},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = supervisor.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error for unknown specialist type")
	}
	if !strings.Contains(err.Error(), "unknown specialist type") {
		t.Errorf("expected unknown specialist error, got: %v", err)
	}
	if !strings.Contains(err.Error(), "unknown_type") {
		t.Errorf("expected error to mention 'unknown_type', got: %v", err)
	}
}

// TestSupervisorAgent_ContextCancellation tests context cancellation
func TestSupervisorAgent_ContextCancellation(t *testing.T) {
	planner := &mockPlanner{
		name: "planner",
		subtasks: []Subtask{
			{Type: "worker1", Message: agenkit.NewMessage("user", "task1")},
			{Type: "worker2", Message: agenkit.NewMessage("user", "task2")},
		},
	}

	specialists := map[string]agenkit.Agent{
		"worker1": &extendedMockAgent{name: "w1", response: "r1"},
		"worker2": &extendedMockAgent{
			name: "w2",
			processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
				select {
				case <-ctx.Done():
					return nil, ctx.Err()
				default:
					return agenkit.NewMessage("assistant", "r2"), nil
				}
			},
		},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	msg := agenkit.NewMessage("user", "test")
	_, err = supervisor.Process(ctx, msg)

	if err == nil {
		t.Fatal("expected error from cancelled context")
	}
	if !strings.Contains(err.Error(), "cancelled") {
		t.Errorf("expected cancellation error, got: %v", err)
	}
}

// TestSupervisorAgent_NilMessage tests nil message handling
func TestSupervisorAgent_NilMessage(t *testing.T) {
	planner := &mockPlanner{name: "planner"}
	specialists := map[string]agenkit.Agent{
		"worker": &extendedMockAgent{name: "worker"},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = supervisor.Process(context.Background(), nil)
	if err == nil {
		t.Fatal("expected error for nil message")
	}
	if !strings.Contains(err.Error(), "cannot be nil") {
		t.Errorf("expected 'cannot be nil' error, got: %v", err)
	}
}

// TestSupervisorAgent_Capabilities tests combined capabilities
func TestSupervisorAgent_Capabilities(t *testing.T) {
	planner := &mockPlanner{name: "planner"}
	specialists := map[string]agenkit.Agent{
		"coder":  &extendedMockAgent{name: "coder", capabilities: []string{"coding"}},
		"tester": &extendedMockAgent{name: "tester", capabilities: []string{"testing"}},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	caps := supervisor.Capabilities()

	expectedCaps := map[string]bool{
		"planning":     true,
		"synthesis":    true,
		"coding":       true,
		"testing":      true,
		"supervisor":   true,
		"hierarchical": true,
		"coordination": true,
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d: %v", len(expectedCaps), len(caps), caps)
	}

	for _, cap := range caps {
		if !expectedCaps[cap] {
			t.Errorf("unexpected capability: %s", cap)
		}
	}
}

// TestSupervisorAgent_SimplePlanner tests SimplePlanner implementation
func TestSupervisorAgent_SimplePlanner(t *testing.T) {
	baseAgent := &extendedMockAgent{name: "base", response: "result"}
	planner := NewSimplePlanner(baseAgent)

	if planner.Name() != "SimplePlanner" {
		t.Errorf("expected name 'SimplePlanner', got '%s'", planner.Name())
	}

	// Test Plan (should return empty subtasks)
	msg := agenkit.NewMessage("user", "test")
	subtasks, err := planner.Plan(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(subtasks) != 0 {
		t.Errorf("expected 0 subtasks, got %d", len(subtasks))
	}

	// Test Synthesize
	results := map[string]*agenkit.Message{
		"worker1": agenkit.NewMessage("assistant", "result1"),
		"worker2": agenkit.NewMessage("assistant", "result2"),
	}
	synthesized, err := planner.Synthesize(context.Background(), msg, results)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(synthesized.Content, "result1") || !strings.Contains(synthesized.Content, "result2") {
		t.Errorf("expected synthesized result to contain both results, got: %s", synthesized.Content)
	}
}

// TestSupervisorAgent_ExecutionOrder tests that execution order is tracked
func TestSupervisorAgent_ExecutionOrder(t *testing.T) {
	planner := &mockPlanner{
		name: "planner",
		subtasks: []Subtask{
			{Type: "first", Message: agenkit.NewMessage("user", "task1")},
			{Type: "second", Message: agenkit.NewMessage("user", "task2")},
			{Type: "third", Message: agenkit.NewMessage("user", "task3")},
		},
		synthesized: "done",
	}

	specialists := map[string]agenkit.Agent{
		"first":  &extendedMockAgent{name: "f", response: "r1"},
		"second": &extendedMockAgent{name: "s", response: "r2"},
		"third":  &extendedMockAgent{name: "t", response: "r3"},
	}

	supervisor, err := NewSupervisorAgent(planner, specialists)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := supervisor.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	execOrder, ok := result.Metadata["execution_order"].([]map[string]interface{})
	if !ok {
		t.Fatal("expected execution_order in metadata")
	}

	expectedTypes := []string{"first", "second", "third"}
	for i, record := range execOrder {
		if record["index"] != i {
			t.Errorf("record %d: expected index=%d, got %v", i, i, record["index"])
		}
		if record["type"] != expectedTypes[i] {
			t.Errorf("record %d: expected type=%s, got %v", i, expectedTypes[i], record["type"])
		}
	}
}
