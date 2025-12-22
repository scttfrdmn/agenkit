package patterns

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mockLLMClient is a mock LLM client for testing.
type mockLLMClient struct {
	responses []string
	callCount int
	lastInput []*agenkit.Message
}

func (m *mockLLMClient) Chat(ctx context.Context, messages []*agenkit.Message) (*agenkit.Message, error) {
	// Store the input for verification
	m.lastInput = messages

	if m.callCount >= len(m.responses) {
		return nil, fmt.Errorf("no more mock responses available")
	}

	response := m.responses[m.callCount]
	m.callCount++

	return &agenkit.Message{
		Role:    "assistant",
		Content: response,
	}, nil
}

// ============================================================================
// Configuration Validation Tests
// ============================================================================

func TestConversationalAgent_NilConfig(t *testing.T) {
	_, err := NewConversationalAgent(nil)
	if err == nil {
		t.Error("expected error for nil config, got nil")
	}
}

func TestConversationalAgent_NilLLMClient(t *testing.T) {
	_, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient: nil,
	})
	if err == nil || !strings.Contains(err.Error(), "llmClient is required") {
		t.Errorf("expected 'llmClient is required' error, got %v", err)
	}
}

func TestConversationalAgent_DefaultMaxHistory(t *testing.T) {
	client := &mockLLMClient{responses: []string{}}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient: client,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if agent.maxHistory != 10 {
		t.Errorf("expected default maxHistory 10, got %d", agent.maxHistory)
	}
}

func TestConversationalAgent_CustomMaxHistory(t *testing.T) {
	client := &mockLLMClient{responses: []string{}}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:  client,
		MaxHistory: 5,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if agent.maxHistory != 5 {
		t.Errorf("expected maxHistory 5, got %d", agent.maxHistory)
	}
}

func TestConversationalAgent_SystemPromptInHistory(t *testing.T) {
	client := &mockLLMClient{responses: []string{}}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:     client,
		SystemPrompt:  "You are helpful",
		IncludeSystem: true,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(agent.history) != 1 {
		t.Errorf("expected 1 message in history, got %d", len(agent.history))
	}
	if agent.history[0].Role != "system" {
		t.Errorf("expected system message, got %s", agent.history[0].Role)
	}
	if agent.history[0].Content != "You are helpful" {
		t.Errorf("expected 'You are helpful', got %s", agent.history[0].Content)
	}
}

func TestConversationalAgent_SystemPromptNotInHistory(t *testing.T) {
	client := &mockLLMClient{responses: []string{}}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:     client,
		SystemPrompt:  "You are helpful",
		IncludeSystem: false,
		MaxHistory:    5,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(agent.history) != 0 {
		t.Errorf("expected 0 messages in history, got %d", len(agent.history))
	}
}

// ============================================================================
// Basic Conversation Tests
// ============================================================================

func TestConversationalAgent_SingleTurn(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"Hello! How can I help you?"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient: client,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	response, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Hi there",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if response.Content != "Hello! How can I help you?" {
		t.Errorf("unexpected response: %s", response.Content)
	}
	if agent.HistoryLength() != 2 {
		t.Errorf("expected 2 messages in history, got %d", agent.HistoryLength())
	}
}

func TestConversationalAgent_MultiTurnConversation(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{
			"Hello Alice!",
			"Your name is Alice.",
		},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient: client,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// First turn
	_, err = agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "My name is Alice",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Second turn
	response, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "What's my name?",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if response.Content != "Your name is Alice." {
		t.Errorf("expected context-aware response, got: %s", response.Content)
	}

	// Verify history length (2 turns = 4 messages)
	if agent.HistoryLength() != 4 {
		t.Errorf("expected 4 messages in history, got %d", agent.HistoryLength())
	}

	// Verify second call received full history
	if len(client.lastInput) != 3 {
		t.Errorf("expected 3 messages passed to LLM, got %d", len(client.lastInput))
	}
}

func TestConversationalAgent_WithSystemPrompt(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"I am a helpful assistant. How can I help?"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:     client,
		SystemPrompt:  "You are a helpful assistant",
		IncludeSystem: true,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Hello",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Verify system prompt was included in LLM call
	if len(client.lastInput) != 2 {
		t.Errorf("expected 2 messages (system + user), got %d", len(client.lastInput))
	}
	if client.lastInput[0].Role != "system" {
		t.Errorf("expected first message to be system, got %s", client.lastInput[0].Role)
	}
}

// ============================================================================
// History Management Tests
// ============================================================================

func TestConversationalAgent_HistoryPruning(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"1", "2", "3", "4"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:  client,
		MaxHistory: 4, // 2 turns max
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Turn 1
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "A"})
	// Turn 2
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "B"})
	// Turn 3 - should trigger pruning
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "C"})

	// Should have 4 messages (2 most recent turns)
	if agent.HistoryLength() != 4 {
		t.Errorf("expected 4 messages after pruning, got %d", agent.HistoryLength())
	}

	history := agent.GetHistory()
	// First message should be from turn 2 (turn 1 pruned)
	if history[0].Content != "B" {
		t.Errorf("expected oldest message to be 'B', got %s", history[0].Content)
	}
}

func TestConversationalAgent_SystemPromptPreservedDuringPruning(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"1", "2", "3"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:     client,
		MaxHistory:    4, // System + 3 messages
		SystemPrompt:  "You are helpful",
		IncludeSystem: true,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Turn 1
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "A"})
	// Turn 2
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "B"})

	// Should have 4 messages: system + 3 most recent (1, B, 2)
	if agent.HistoryLength() != 4 {
		t.Errorf("expected 4 messages, got %d", agent.HistoryLength())
	}

	history := agent.GetHistory()
	if history[0].Role != "system" {
		t.Error("expected system message to be preserved")
	}
	// After pruning, oldest non-system message should be assistant response "1" from turn 1
	if history[1].Content != "1" {
		t.Errorf("expected second message to be '1' (assistant from turn 1), got %s", history[1].Content)
	}
}

func TestConversationalAgent_ClearHistory(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"Response"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:     client,
		SystemPrompt:  "You are helpful",
		IncludeSystem: true,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Add some conversation
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "Hello"})

	// Clear history but keep system
	agent.ClearHistory(true)

	if agent.HistoryLength() != 1 {
		t.Errorf("expected 1 message (system), got %d", agent.HistoryLength())
	}
	history := agent.GetHistory()
	if history[0].Role != "system" {
		t.Error("expected system message to be preserved")
	}
}

func TestConversationalAgent_ClearHistoryIncludingSystem(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"Response"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:     client,
		SystemPrompt:  "You are helpful",
		IncludeSystem: true,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Add some conversation
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "Hello"})

	// Clear all history
	agent.ClearHistory(false)

	if agent.HistoryLength() != 0 {
		t.Errorf("expected 0 messages, got %d", agent.HistoryLength())
	}
}

func TestConversationalAgent_SetMaxHistory(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"1", "2", "3"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:  client,
		MaxHistory: 10,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Add 3 turns (6 messages)
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "A"})
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "B"})
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "C"})

	if agent.HistoryLength() != 6 {
		t.Errorf("expected 6 messages, got %d", agent.HistoryLength())
	}

	// Reduce max history to 2
	agent.SetMaxHistory(2)

	// Should prune to 2 messages
	if agent.HistoryLength() != 2 {
		t.Errorf("expected 2 messages after SetMaxHistory, got %d", agent.HistoryLength())
	}

	history := agent.GetHistory()
	if history[0].Content != "C" {
		t.Errorf("expected most recent messages preserved, got %s", history[0].Content)
	}
}

// ============================================================================
// GetHistory Tests
// ============================================================================

func TestConversationalAgent_GetHistoryReturnsACopy(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"Response"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient: client,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "Test"})

	// Get history and modify it
	history := agent.GetHistory()
	history[0].Content = "Modified"

	// Original should be unchanged
	originalHistory := agent.GetHistory()
	if originalHistory[0].Content == "Modified" {
		t.Error("GetHistory should return a copy, not original")
	}
}

// ============================================================================
// Name and Capabilities Tests
// ============================================================================

func TestConversationalAgent_Name(t *testing.T) {
	client := &mockLLMClient{responses: []string{}}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient: client,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if agent.Name() != "ConversationalAgent" {
		t.Errorf("expected name 'ConversationalAgent', got %s", agent.Name())
	}
}

func TestConversationalAgent_Capabilities(t *testing.T) {
	client := &mockLLMClient{responses: []string{}}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient: client,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	capabilities := agent.Capabilities()
	expected := []string{"conversational", "history-management"}
	if len(capabilities) != len(expected) {
		t.Errorf("expected %d capabilities, got %d", len(expected), len(capabilities))
	}
	for i, cap := range expected {
		if capabilities[i] != cap {
			t.Errorf("expected capability %s, got %s", cap, capabilities[i])
		}
	}
}

// ============================================================================
// Edge Cases Tests
// ============================================================================

func TestConversationalAgent_EmptyMaxHistory(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"1", "2"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:     client,
		MaxHistory:    1,
		SystemPrompt:  "System",
		IncludeSystem: true,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// System takes all space
	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "A"})

	// Should only have system message
	if agent.HistoryLength() != 1 {
		t.Errorf("expected 1 message (system only), got %d", agent.HistoryLength())
	}
}

func TestConversationalAgent_LLMClientError(t *testing.T) {
	client := &mockLLMClient{responses: []string{}}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient: client,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err == nil {
		t.Error("expected error when LLM client has no responses")
	}
}

func TestConversationalAgent_HistoryLengthProperty(t *testing.T) {
	client := &mockLLMClient{
		responses: []string{"1", "2"},
	}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient: client,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if agent.HistoryLength() != 0 {
		t.Errorf("expected 0 messages initially, got %d", agent.HistoryLength())
	}

	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "A"})
	if agent.HistoryLength() != 2 {
		t.Errorf("expected 2 messages after 1 turn, got %d", agent.HistoryLength())
	}

	_, _ = agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "B"})
	if agent.HistoryLength() != 4 {
		t.Errorf("expected 4 messages after 2 turns, got %d", agent.HistoryLength())
	}
}
