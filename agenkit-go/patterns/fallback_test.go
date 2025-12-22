package patterns

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestFallbackAgent_Constructor tests valid construction
func TestFallbackAgent_Constructor(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "result1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "result2"}

	fallback, err := NewFallbackAgent([]agenkit.Agent{agent1, agent2})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if fallback == nil {
		t.Fatal("expected non-nil FallbackAgent")
	}
	if fallback.Name() != "FallbackAgent" {
		t.Errorf("expected name 'FallbackAgent', got '%s'", fallback.Name())
	}
}

// TestFallbackAgent_ConstructorEmptyAgents tests error case with no agents
func TestFallbackAgent_ConstructorEmptyAgents(t *testing.T) {
	_, err := NewFallbackAgent([]agenkit.Agent{})
	if err == nil {
		t.Fatal("expected error for empty agents list")
	}
	if !strings.Contains(err.Error(), "at least one agent") {
		t.Errorf("expected 'at least one agent' error, got %v", err)
	}
}

// TestFallbackAgent_FirstAgentSuccess tests immediate success with first agent
func TestFallbackAgent_FirstAgentSuccess(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "success from agent1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "should not reach"}

	fallback, err := NewFallbackAgent([]agenkit.Agent{agent1, agent2})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := fallback.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "success from agent1" {
		t.Errorf("expected 'success from agent1', got '%s'", result.Content)
	}

	// Check metadata
	if result.Metadata["fallback_attempts"] != 1 {
		t.Errorf("expected fallback_attempts=1, got %v", result.Metadata["fallback_attempts"])
	}
	if result.Metadata["fallback_success_agent"] != "agent1" {
		t.Errorf("expected success from agent1, got %v", result.Metadata["fallback_success_agent"])
	}
}

// TestFallbackAgent_SecondAgentSuccess tests fallback to second agent
func TestFallbackAgent_SecondAgentSuccess(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", err: errors.New("agent1 failed")}
	agent2 := &extendedMockAgent{name: "agent2", response: "success from agent2"}
	agent3 := &extendedMockAgent{name: "agent3", response: "should not reach"}

	fallback, err := NewFallbackAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := fallback.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "success from agent2" {
		t.Errorf("expected 'success from agent2', got '%s'", result.Content)
	}

	// Check metadata
	if result.Metadata["fallback_attempts"] != 2 {
		t.Errorf("expected fallback_attempts=2, got %v", result.Metadata["fallback_attempts"])
	}
	if result.Metadata["fallback_success_index"] != 1 {
		t.Errorf("expected success_index=1, got %v", result.Metadata["fallback_success_index"])
	}

	// Check failed attempts recorded
	failedAttempts, ok := result.Metadata["fallback_failed_attempts"].([]map[string]interface{})
	if !ok {
		t.Fatal("expected fallback_failed_attempts in metadata")
	}
	if len(failedAttempts) != 1 {
		t.Errorf("expected 1 failed attempt, got %d", len(failedAttempts))
	}
	if failedAttempts[0]["agent"] != "agent1" {
		t.Errorf("expected failed agent to be agent1, got %v", failedAttempts[0]["agent"])
	}
}

// TestFallbackAgent_LastAgentSuccess tests success on last agent
func TestFallbackAgent_LastAgentSuccess(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", err: errors.New("error1")}
	agent2 := &extendedMockAgent{name: "agent2", err: errors.New("error2")}
	agent3 := &extendedMockAgent{name: "agent3", response: "success from agent3"}

	fallback, err := NewFallbackAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := fallback.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "success from agent3" {
		t.Errorf("expected 'success from agent3', got '%s'", result.Content)
	}

	// Should have tried all 3 agents
	if result.Metadata["fallback_attempts"] != 3 {
		t.Errorf("expected fallback_attempts=3, got %v", result.Metadata["fallback_attempts"])
	}

	// Check failed attempts
	failedAttempts, ok := result.Metadata["fallback_failed_attempts"].([]map[string]interface{})
	if !ok {
		t.Fatal("expected fallback_failed_attempts in metadata")
	}
	if len(failedAttempts) != 2 {
		t.Errorf("expected 2 failed attempts, got %d", len(failedAttempts))
	}
}

// TestFallbackAgent_AllAgentsFail tests when all agents fail
func TestFallbackAgent_AllAgentsFail(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", err: errors.New("error1")}
	agent2 := &extendedMockAgent{name: "agent2", err: errors.New("error2")}
	agent3 := &extendedMockAgent{name: "agent3", err: errors.New("error3")}

	fallback, err := NewFallbackAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := fallback.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error when all agents fail")
	}
	if result != nil {
		t.Error("expected nil result when all agents fail")
	}

	// Error should mention all agents
	if !strings.Contains(err.Error(), "all 3 agents failed") {
		t.Errorf("expected error to mention all agents, got: %v", err)
	}
	if !strings.Contains(err.Error(), "agent1") {
		t.Errorf("expected error to mention agent1, got: %v", err)
	}
	if !strings.Contains(err.Error(), "agent2") {
		t.Errorf("expected error to mention agent2, got: %v", err)
	}
	if !strings.Contains(err.Error(), "agent3") {
		t.Errorf("expected error to mention agent3, got: %v", err)
	}
}

// TestFallbackAgent_ContextCancellation tests context cancellation
func TestFallbackAgent_ContextCancellation(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", err: errors.New("error1")}
	agent2 := &extendedMockAgent{
		name: "agent2",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			default:
				return agenkit.NewMessage("assistant", "success"), nil
			}
		},
	}

	fallback, err := NewFallbackAgent([]agenkit.Agent{agent1, agent2})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	msg := agenkit.NewMessage("user", "test")
	_, err = fallback.Process(ctx, msg)

	if err == nil {
		t.Fatal("expected error from cancelled context")
	}
	if !strings.Contains(err.Error(), "cancelled") {
		t.Errorf("expected cancellation error, got: %v", err)
	}
}

// TestFallbackAgent_NilMessage tests nil message handling
func TestFallbackAgent_NilMessage(t *testing.T) {
	agent := &extendedMockAgent{name: "agent1", response: "test"}
	fallback, err := NewFallbackAgent([]agenkit.Agent{agent})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = fallback.Process(context.Background(), nil)
	if err == nil {
		t.Fatal("expected error for nil message")
	}
	if !strings.Contains(err.Error(), "cannot be nil") {
		t.Errorf("expected 'cannot be nil' error, got: %v", err)
	}
}

// TestFallbackAgent_Capabilities tests combined capabilities
func TestFallbackAgent_Capabilities(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", capabilities: []string{"cap1", "cap2"}}
	agent2 := &extendedMockAgent{name: "agent2", capabilities: []string{"cap2", "cap3"}}

	fallback, err := NewFallbackAgent([]agenkit.Agent{agent1, agent2})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	caps := fallback.Capabilities()

	expectedCaps := map[string]bool{
		"cap1":              true,
		"cap2":              true,
		"cap3":              true,
		"fallback":          true,
		"retry":             true,
		"high-availability": true,
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d: %v", len(expectedCaps), len(caps), caps)
	}
}

// TestFallbackAgent_SingleAgent tests fallback with single agent
func TestFallbackAgent_SingleAgent(t *testing.T) {
	agent := &extendedMockAgent{name: "solo", response: "result"}
	fallback, err := NewFallbackAgent([]agenkit.Agent{agent})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := fallback.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "result" {
		t.Errorf("expected 'result', got '%s'", result.Content)
	}

	// Should have no failed attempts
	if result.Metadata["fallback_failed_attempts"] != nil {
		t.Error("expected no fallback_failed_attempts for single successful agent")
	}
}

// TestFallbackAgent_MetadataTracking tests detailed metadata tracking
func TestFallbackAgent_MetadataTracking(t *testing.T) {
	agent1 := &extendedMockAgent{name: "primary", err: errors.New("primary down")}
	agent2 := &extendedMockAgent{name: "secondary", err: errors.New("secondary down")}
	agent3 := &extendedMockAgent{name: "tertiary", response: "tertiary success"}

	fallback, err := NewFallbackAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := fallback.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Verify all metadata fields
	if result.Metadata["fallback_total_agents"] != 3 {
		t.Errorf("expected fallback_total_agents=3, got %v", result.Metadata["fallback_total_agents"])
	}
	if result.Metadata["fallback_success_index"] != 2 {
		t.Errorf("expected fallback_success_index=2, got %v", result.Metadata["fallback_success_index"])
	}
	if result.Metadata["fallback_success_agent"] != "tertiary" {
		t.Errorf("expected fallback_success_agent='tertiary', got %v", result.Metadata["fallback_success_agent"])
	}

	failedAttempts, ok := result.Metadata["fallback_failed_attempts"].([]map[string]interface{})
	if !ok {
		t.Fatal("expected fallback_failed_attempts")
	}

	// Verify failed attempts details
	if len(failedAttempts) != 2 {
		t.Fatalf("expected 2 failed attempts, got %d", len(failedAttempts))
	}

	expectedFailed := []struct {
		index int
		agent string
		error string
	}{
		{0, "primary", "primary down"},
		{1, "secondary", "secondary down"},
	}

	for i, expected := range expectedFailed {
		if failedAttempts[i]["index"] != expected.index {
			t.Errorf("failed attempt %d: expected index=%d, got %v", i, expected.index, failedAttempts[i]["index"])
		}
		if failedAttempts[i]["agent"] != expected.agent {
			t.Errorf("failed attempt %d: expected agent=%s, got %v", i, expected.agent, failedAttempts[i]["agent"])
		}
		errorStr, ok := failedAttempts[i]["error"].(string)
		if !ok || !strings.Contains(errorStr, expected.error) {
			t.Errorf("failed attempt %d: expected error containing '%s', got %v", i, expected.error, failedAttempts[i]["error"])
		}
	}
}

// TestRecoveryAgent_BasicRecovery tests RecoveryAgent with successful recovery
func TestRecoveryAgent_BasicRecovery(t *testing.T) {
	agent := &extendedMockAgent{name: "agent", err: errors.New("agent failed")}

	recoveryFunc := func(ctx context.Context, message *agenkit.Message, originalError error) (*agenkit.Message, error) {
		return agenkit.NewMessage("assistant", "recovered successfully"), nil
	}

	recovery := WithRecovery(agent, recoveryFunc)

	if !strings.Contains(recovery.Name(), "Recovery") {
		t.Errorf("expected name to contain 'Recovery', got '%s'", recovery.Name())
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := recovery.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "recovered successfully" {
		t.Errorf("expected 'recovered successfully', got '%s'", result.Content)
	}

	// Check recovery metadata
	if result.Metadata["recovery_used"] != true {
		t.Error("expected recovery_used=true")
	}
	if result.Metadata["original_error"] == nil {
		t.Error("expected original_error in metadata")
	}
}

// TestRecoveryAgent_NoRecoveryNeeded tests RecoveryAgent when primary succeeds
func TestRecoveryAgent_NoRecoveryNeeded(t *testing.T) {
	agent := &extendedMockAgent{name: "agent", response: "primary success"}

	recoveryFunc := func(ctx context.Context, message *agenkit.Message, originalError error) (*agenkit.Message, error) {
		t.Error("recovery function should not be called")
		return nil, errors.New("should not reach")
	}

	recovery := WithRecovery(agent, recoveryFunc)

	msg := agenkit.NewMessage("user", "test")
	result, err := recovery.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "primary success" {
		t.Errorf("expected 'primary success', got '%s'", result.Content)
	}

	// Should not have recovery metadata
	if result.Metadata["recovery_used"] != nil {
		t.Error("expected no recovery_used when primary succeeds")
	}
}

// TestRecoveryAgent_RecoveryFailure tests RecoveryAgent when recovery fails
func TestRecoveryAgent_RecoveryFailure(t *testing.T) {
	agent := &extendedMockAgent{name: "agent", err: errors.New("primary error")}

	recoveryFunc := func(ctx context.Context, message *agenkit.Message, originalError error) (*agenkit.Message, error) {
		return nil, errors.New("recovery error")
	}

	recovery := WithRecovery(agent, recoveryFunc)

	msg := agenkit.NewMessage("user", "test")
	_, err := recovery.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error when both primary and recovery fail")
	}

	// Error should mention both failures
	if !strings.Contains(err.Error(), "primary agent failed") {
		t.Errorf("expected error to mention primary failure, got: %v", err)
	}
	if !strings.Contains(err.Error(), "recovery failed") {
		t.Errorf("expected error to mention recovery failure, got: %v", err)
	}
}

// TestRecoveryAgent_Capabilities tests RecoveryAgent capabilities
func TestRecoveryAgent_Capabilities(t *testing.T) {
	agent := &extendedMockAgent{name: "agent", capabilities: []string{"cap1"}}

	recoveryFunc := func(ctx context.Context, message *agenkit.Message, originalError error) (*agenkit.Message, error) {
		return agenkit.NewMessage("assistant", "recovered"), nil
	}

	recovery := WithRecovery(agent, recoveryFunc)
	caps := recovery.Capabilities()

	expectedCaps := map[string]bool{
		"cap1":           true,
		"recovery":       true,
		"error-handling": true,
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d: %v", len(expectedCaps), len(caps), caps)
	}
}

// TestDefaultRecovery_StaticMessage tests static message recovery
func TestDefaultRecovery_StaticMessage(t *testing.T) {
	recoveryFunc := DefaultRecovery.StaticMessage("Service temporarily unavailable")

	msg := agenkit.NewMessage("user", "test")
	result, err := recoveryFunc(context.Background(), msg, errors.New("original error"))

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Content != "Service temporarily unavailable" {
		t.Errorf("expected static message, got '%s'", result.Content)
	}
}

// TestDefaultRecovery_EmptyResponse tests empty response recovery
func TestDefaultRecovery_EmptyResponse(t *testing.T) {
	msg := agenkit.NewMessage("user", "test")
	result, err := DefaultRecovery.EmptyResponse(context.Background(), msg, errors.New("error"))

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Content != "" {
		t.Errorf("expected empty content, got '%s'", result.Content)
	}
}
