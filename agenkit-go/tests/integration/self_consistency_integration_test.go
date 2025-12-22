package integration

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"
)

// MockVariableAgent returns varying responses for testing
type MockVariableAgent struct {
	responses  []string
	shouldFail bool
	callCount  int
	mu         sync.Mutex
}

func NewMockVariableAgent(responses []string) *MockVariableAgent {
	return &MockVariableAgent{
		responses: responses,
	}
}

func (m *MockVariableAgent) Name() string {
	return "mock_variable"
}

func (m *MockVariableAgent) Capabilities() []string {
	return []string{"mock", "variable_response"}
}

func (m *MockVariableAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MockVariableAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.shouldFail {
		return nil, fmt.Errorf("mock agent failure")
	}

	response := m.responses[m.callCount%len(m.responses)]
	m.callCount++

	return agenkit.NewMessage("assistant", response), nil
}

// MockDeterministicAgent always returns the same response
type MockDeterministicAgent struct {
	response string
}

func NewMockDeterministicAgent(response string) *MockDeterministicAgent {
	return &MockDeterministicAgent{response: response}
}

func (m *MockDeterministicAgent) Name() string {
	return "mock_deterministic"
}

func (m *MockDeterministicAgent) Capabilities() []string {
	return []string{"mock", "deterministic"}
}

func (m *MockDeterministicAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MockDeterministicAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", m.response), nil
}

// ============================================================================
// Basic Functionality Tests (No External Dependencies)
// ============================================================================

func TestSelfConsistencyIntegrationBasic(t *testing.T) {
	// Mock agent returns 3 votes for "42" and 2 for "43"
	baseAgent := NewMockVariableAgent([]string{
		"After calculation, the answer is 42.",
		"Let me think... I believe it's 43.",
		"The answer is 42.",
		"Definitely 42.",
		"I think the answer is 43.",
	})

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(5),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is 6 * 7?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Check basic response properties
	if response.Role != "assistant" {
		t.Errorf("Expected role='assistant', got '%s'", response.Role)
	}

	if !strings.Contains(response.Content, "42") {
		t.Errorf("Expected content to contain '42', got: %s", response.Content)
	}

	// Check metadata
	if response.Metadata["technique"] != "self_consistency" {
		t.Errorf("Expected technique='self_consistency', got: %v", response.Metadata["technique"])
	}

	if response.Metadata["num_samples"] != 5 {
		t.Errorf("Expected num_samples=5, got: %v", response.Metadata["num_samples"])
	}

	if response.Metadata["voting_strategy"] != "majority" {
		t.Errorf("Expected voting_strategy='majority', got: %v", response.Metadata["voting_strategy"])
	}

	consistencyScore, ok := response.Metadata["consistency_score"].(float64)
	if !ok {
		t.Errorf("Expected consistency_score to be float64, got: %T", response.Metadata["consistency_score"])
	}

	if consistencyScore < 0.4 || consistencyScore > 1.0 {
		t.Errorf("Expected consistency_score >= 0.4, got: %f", consistencyScore)
	}

	// Check samples are stored
	samples, ok := response.Metadata["samples"].([]string)
	if !ok || len(samples) != 5 {
		t.Errorf("Expected 5 samples, got: %v", response.Metadata["samples"])
	}

	extractedAnswers, ok := response.Metadata["extracted_answers"].([]string)
	if !ok || len(extractedAnswers) != 5 {
		t.Errorf("Expected 5 extracted answers, got: %v", response.Metadata["extracted_answers"])
	}
}

func TestSelfConsistencyIntegrationPerfectAgreement(t *testing.T) {
	baseAgent := NewMockDeterministicAgent("The answer is 42.")

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(5),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the answer?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Perfect consistency should give score of 1.0
	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 1.0 {
		t.Errorf("Expected consistency_score=1.0, got: %f", consistencyScore)
	}

	if !strings.Contains(response.Content, "42") {
		t.Errorf("Expected content to contain '42', got: %s", response.Content)
	}
}

func TestSelfConsistencyIntegrationNoAgreement(t *testing.T) {
	baseAgent := NewMockVariableAgent([]string{
		"The answer is 1.",
		"The answer is 2.",
		"The answer is 3.",
		"The answer is 4.",
		"The answer is 5.",
	})

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(5),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the answer?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// No agreement should give low consistency score (1/5 = 0.2)
	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 0.2 {
		t.Errorf("Expected consistency_score=0.2, got: %f", consistencyScore)
	}
}

func TestSelfConsistencyIntegrationWeightedVoting(t *testing.T) {
	baseAgent := NewMockVariableAgent([]string{
		"Paris.",
		"Paris.",
		"Paris.",
		"After extensive analysis of historical data, geographical considerations, and political significance, I can confidently conclude that the capital of France is London.",
	})

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(4),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyWeighted),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the capital of France?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Weighted voting should favor the longer "London" response
	if !strings.Contains(strings.ToLower(response.Content), "london") {
		t.Errorf("Expected answer to contain 'london', got: %s", response.Content)
	}

	if response.Metadata["voting_strategy"] != "weighted" {
		t.Errorf("Expected voting_strategy='weighted', got: %v", response.Metadata["voting_strategy"])
	}
}

func TestSelfConsistencyIntegrationFirstStrategy(t *testing.T) {
	baseAgent := NewMockVariableAgent([]string{
		"The answer is A.",
		"The answer is A.",
		"The answer is A.",
	})

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(3),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyFirst),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// First strategy should return first answer
	if !strings.Contains(response.Content, "A") {
		t.Errorf("Expected answer to contain 'A', got: %s", response.Content)
	}

	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 1.0 {
		t.Errorf("Expected consistency_score=1.0 for first strategy, got: %f", consistencyScore)
	}
}

func TestSelfConsistencyIntegrationCustomExtractor(t *testing.T) {
	baseAgent := NewMockVariableAgent([]string{
		"[ANSWER: 42]",
		"[ANSWER: 42]",
		"[ANSWER: 43]",
	})

	customExtractor := func(text string) string {
		// Extract answer from custom format
		start := strings.Index(text, "[ANSWER: ")
		if start == -1 {
			return text
		}
		start += len("[ANSWER: ")
		end := strings.Index(text[start:], "]")
		if end == -1 {
			return text
		}
		return text[start : start+end]
	}

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(3),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
		reasoning.WithAnswerExtractor(customExtractor),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should extract "42" as majority
	if response.Content != "42" {
		t.Errorf("Expected answer='42', got: %s", response.Content)
	}
}

func TestSelfConsistencyIntegrationSingleSample(t *testing.T) {
	baseAgent := NewMockDeterministicAgent("The answer is 42.")

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(1),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Single sample should work with perfect consistency
	if !strings.Contains(response.Content, "42") {
		t.Errorf("Expected content to contain '42', got: %s", response.Content)
	}

	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 1.0 {
		t.Errorf("Expected consistency_score=1.0, got: %f", consistencyScore)
	}

	samples := response.Metadata["samples"].([]string)
	if len(samples) != 1 {
		t.Errorf("Expected 1 sample, got: %d", len(samples))
	}
}

func TestSelfConsistencyIntegrationErrorHandling(t *testing.T) {
	baseAgent := NewMockVariableAgent([]string{"response"})
	baseAgent.shouldFail = true

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(3),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	_, err := sc.Process(ctx, message)
	if err == nil {
		t.Fatal("Expected error when base agent fails, got nil")
	}

	if !strings.Contains(err.Error(), "sampling failed") {
		t.Errorf("Expected error to contain 'sampling failed', got: %v", err)
	}
}

func TestSelfConsistencyIntegrationCaseInsensitive(t *testing.T) {
	baseAgent := NewMockVariableAgent([]string{
		"The answer is PARIS.",
		"The answer is Paris.",
		"The answer is paris.",
		"The answer is PaRiS.",
		"The answer is London.",
	})

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(5),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the capital?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should recognize all case variations as the same (4/5 = 0.8)
	if !strings.Contains(strings.ToLower(response.Content), "paris") {
		t.Errorf("Expected answer to contain 'paris', got: %s", response.Content)
	}

	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 0.8 {
		t.Errorf("Expected consistency_score=0.8 (4/5), got: %f", consistencyScore)
	}
}

// ============================================================================
// Metadata Validation Tests
// ============================================================================

func TestSelfConsistencyIntegrationMetadataCompleteness(t *testing.T) {
	baseAgent := NewMockDeterministicAgent("The answer is 42.")

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(3),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Check all required metadata fields
	requiredFields := []string{
		"technique",
		"num_samples",
		"voting_strategy",
		"consistency_score",
		"samples",
		"extracted_answers",
		"answer_counts",
		"base_agent",
	}

	for _, field := range requiredFields {
		if _, ok := response.Metadata[field]; !ok {
			t.Errorf("Missing required metadata field: %s", field)
		}
	}
}
