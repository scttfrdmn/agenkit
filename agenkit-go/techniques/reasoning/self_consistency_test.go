package reasoning

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// MockAgent for testing
type MockAgent struct {
	name       string
	responses  []string
	callCount  int
	shouldFail bool
	mu         sync.Mutex
}

var _ agenkit.Agent = (*MockAgent)(nil)

func NewMockAgent(responses []string) *MockAgent {
	return &MockAgent{
		name:      "mock_agent",
		responses: responses,
		callCount: 0,
	}
}

func (m *MockAgent) Name() string {
	return m.name
}

func (m *MockAgent) Capabilities() []string {
	return []string{"mock", "testing"}
}

func (m *MockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.shouldFail {
		return nil, fmt.Errorf("mock agent failed")
	}

	// Return responses in round-robin fashion (thread-safe)
	m.mu.Lock()
	response := m.responses[m.callCount%len(m.responses)]
	m.callCount++
	m.mu.Unlock()

	return agenkit.NewMessage("assistant", response), nil
}

func (m *MockAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(m)
}

// Test basic Self-Consistency functionality
func TestSelfConsistencyBasic(t *testing.T) {
	// Mock agent returns different answers
	mockAgent := NewMockAgent([]string{
		"The answer is 42.",
		"I think it's 42.",
		"The answer is 41.",
		"42 is the answer.",
		"The answer is 42.",
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(5),
		WithVotingStrategy(VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the answer?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Check response content
	if !strings.Contains(response.Content, "42") {
		t.Errorf("Expected answer to contain '42', got: %s", response.Content)
	}

	// Check metadata
	if response.Metadata["technique"] != "self_consistency" {
		t.Errorf("Expected technique='self_consistency', got: %v", response.Metadata["technique"])
	}

	numSamples, ok := response.Metadata["num_samples"].(int)
	if !ok || numSamples != 5 {
		t.Errorf("Expected num_samples=5, got: %v", response.Metadata["num_samples"])
	}

	votingStrategy, ok := response.Metadata["voting_strategy"].(string)
	if !ok || votingStrategy != "majority" {
		t.Errorf("Expected voting_strategy='majority', got: %v", response.Metadata["voting_strategy"])
	}

	// Check consistency score
	consistencyScore, ok := response.Metadata["consistency_score"].(float64)
	if !ok {
		t.Errorf("Expected consistency_score to be float64, got: %v", response.Metadata["consistency_score"])
	}
	if consistencyScore < 0.0 || consistencyScore > 1.0 {
		t.Errorf("Expected consistency_score in [0, 1], got: %f", consistencyScore)
	}

	// Check samples
	samples, ok := response.Metadata["samples"].([]string)
	if !ok || len(samples) != 5 {
		t.Errorf("Expected 5 samples, got: %v", response.Metadata["samples"])
	}

	// Check extracted answers
	extractedAnswers, ok := response.Metadata["extracted_answers"].([]string)
	if !ok || len(extractedAnswers) != 5 {
		t.Errorf("Expected 5 extracted answers, got: %v", response.Metadata["extracted_answers"])
	}
}

// Test majority voting strategy
func TestSelfConsistencyMajorityVoting(t *testing.T) {
	// 3 votes for "Paris", 2 votes for "London"
	mockAgent := NewMockAgent([]string{
		"The answer is Paris.",
		"The answer is London.",
		"The answer is Paris.",
		"The answer is Paris.",
		"The answer is London.",
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(5),
		WithVotingStrategy(VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the capital of France?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Majority vote should be "Paris" (3/5 = 0.6)
	if !strings.Contains(strings.ToLower(response.Content), "paris") {
		t.Errorf("Expected answer to contain 'paris', got: %s", response.Content)
	}

	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 0.6 {
		t.Errorf("Expected consistency_score=0.6, got: %f", consistencyScore)
	}
}

// Test weighted voting strategy
func TestSelfConsistencyWeightedVoting(t *testing.T) {
	// "Paris" has short responses (total weight: 60)
	// "London" has one long response (weight: 100)
	mockAgent := NewMockAgent([]string{
		"The answer is Paris.", // ~20 chars
		"The answer is Paris.", // ~20 chars
		"The answer is Paris.", // ~20 chars
		"After careful consideration and analysis of the question, I believe London is correct.", // ~100 chars
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(4),
		WithVotingStrategy(VotingStrategyWeighted),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the capital?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Weighted vote should favor "London" despite fewer occurrences
	if !strings.Contains(strings.ToLower(response.Content), "london") {
		t.Errorf("Expected answer to contain 'london', got: %s", response.Content)
	}
}

// Test first strategy (no voting)
func TestSelfConsistencyFirstStrategy(t *testing.T) {
	// All mock responses are the same to ensure deterministic result
	mockAgent := NewMockAgent([]string{
		"The answer is A.",
		"The answer is A.",
		"The answer is A.",
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(3),
		WithVotingStrategy(VotingStrategyFirst),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should return the first answer (answers[0])
	if !strings.Contains(response.Content, "A") {
		t.Errorf("Expected answer to contain 'A', got: %s", response.Content)
	}

	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 1.0 {
		t.Errorf("Expected consistency_score=1.0 for first strategy, got: %f", consistencyScore)
	}
}

// Test custom answer extractor
func TestSelfConsistencyCustomExtractor(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"[ANSWER: 42]",
		"[ANSWER: 42]",
		"[ANSWER: 43]",
	})

	customExtractor := func(text string) string {
		// Extract answer between [ANSWER: and ]
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

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(3),
		WithVotingStrategy(VotingStrategyMajority),
		WithAnswerExtractor(customExtractor),
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

// Test answer extractor with various patterns
func TestAnswerExtractorPatterns(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "Therefore pattern",
			input:    "Let me think. Step 1... Step 2... Therefore, the answer is 42.",
			expected: "42", // Extractor captures "the answer is 42" from the pattern
		},
		{
			name:     "Thus pattern",
			input:    "After analysis, thus, 42 is correct.",
			expected: "42", // Extractor captures "42 is correct"
		},
		{
			name:     "So pattern",
			input:    "Calculating... so, the result is 100.",
			expected: "100", // Extractor captures "the result is 100"
		},
		{
			name:     "The answer is pattern",
			input:    "Based on the data, the answer is Paris.",
			expected: "Paris",
		},
		{
			name:     "Math equation pattern",
			input:    "Let x = 5, then 2x = 10. x = 5",
			expected: "5",
		},
		{
			name:     "Conclusion pattern",
			input:    "After review, conclusion: the hypothesis is true.",
			expected: "hypothesis", // Contains "hypothesis"
		},
		{
			name:     "Result pattern",
			input:    "Computation complete. Result: 42",
			expected: "42",
		},
		{
			name:     "Last line fallback",
			input:    "Step 1: do this\nStep 2: do that\nFinal answer is here",
			expected: "Final answer is here",
		},
	}

	extractor := defaultAnswerExtractor

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := extractor(tt.input)
			if !strings.Contains(strings.ToLower(result), strings.ToLower(tt.expected)) {
				t.Errorf("Expected to contain %q, got: %q", tt.expected, result)
			}
		})
	}
}

// Test single sample edge case
func TestSelfConsistencySingleSample(t *testing.T) {
	mockAgent := NewMockAgent([]string{"The answer is 42."})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(1),
		WithVotingStrategy(VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should work with single sample
	if !strings.Contains(response.Content, "42") {
		t.Errorf("Expected answer to contain '42', got: %s", response.Content)
	}

	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 1.0 {
		t.Errorf("Expected consistency_score=1.0 for single sample, got: %f", consistencyScore)
	}
}

// Test perfect consistency
func TestSelfConsistencyPerfectConsistency(t *testing.T) {
	// All samples return the same answer
	mockAgent := NewMockAgent([]string{
		"The answer is 42.",
		"The answer is 42.",
		"The answer is 42.",
		"The answer is 42.",
		"The answer is 42.",
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(5),
		WithVotingStrategy(VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 1.0 {
		t.Errorf("Expected consistency_score=1.0 for perfect consistency, got: %f", consistencyScore)
	}
}

// Test no consistency (all different)
func TestSelfConsistencyNoConsistency(t *testing.T) {
	// All samples return different answers
	mockAgent := NewMockAgent([]string{
		"The answer is 1.",
		"The answer is 2.",
		"The answer is 3.",
		"The answer is 4.",
		"The answer is 5.",
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(5),
		WithVotingStrategy(VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// With all different answers, consistency score should be 1/5 = 0.2
	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 0.2 {
		t.Errorf("Expected consistency_score=0.2 for no consistency, got: %f", consistencyScore)
	}
}

// Test error handling
func TestSelfConsistencyErrorHandling(t *testing.T) {
	mockAgent := NewMockAgent([]string{"response"})
	mockAgent.shouldFail = true

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(3),
		WithVotingStrategy(VotingStrategyMajority),
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

// Test context cancellation
func TestSelfConsistencyContextCancellation(t *testing.T) {
	mockAgent := NewMockAgent([]string{"The answer is 42."})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(10),
		WithVotingStrategy(VotingStrategyMajority),
	)

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	message := agenkit.NewMessage("user", "Test question")

	_, err := sc.Process(ctx, message)
	// Note: Current implementation doesn't check context in Process
	// This test documents the behavior - context checking could be added
	if err != nil {
		// If context checking is implemented, error is expected
		if !strings.Contains(err.Error(), "context") {
			t.Logf("Context cancellation error: %v", err)
		}
	}
}

// Test agent name and capabilities
func TestSelfConsistencyMetadata(t *testing.T) {
	mockAgent := NewMockAgent([]string{"response"})

	sc := NewSelfConsistency(mockAgent)

	if sc.Name() != "self_consistency" {
		t.Errorf("Expected name='self_consistency', got: %s", sc.Name())
	}

	capabilities := sc.Capabilities()
	expectedCaps := []string{"reasoning", "self_consistency", "majority_voting", "reliability", "consensus"}

	if len(capabilities) != len(expectedCaps) {
		t.Errorf("Expected %d capabilities, got: %d", len(expectedCaps), len(capabilities))
	}

	for _, expected := range expectedCaps {
		found := false
		for _, cap := range capabilities {
			if cap == expected {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected capability %q not found in: %v", expected, capabilities)
		}
	}
}

// Test invalid voting strategy
func TestSelfConsistencyInvalidStrategy(t *testing.T) {
	mockAgent := NewMockAgent([]string{"response"})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(3),
	)

	// Manually set invalid strategy (not possible via public API)
	sc.votingStrategy = VotingStrategy("invalid")

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	_, err := sc.Process(ctx, message)
	if err == nil {
		t.Fatal("Expected error for invalid voting strategy, got nil")
	}

	if !strings.Contains(err.Error(), "invalid voting strategy") {
		t.Errorf("Expected error to contain 'invalid voting strategy', got: %v", err)
	}
}

// Test case-insensitive answer matching
func TestSelfConsistencyCaseInsensitive(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"The answer is PARIS.",
		"The answer is Paris.",
		"The answer is paris.",
		"The answer is PaRiS.",
		"The answer is London.",
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(5),
		WithVotingStrategy(VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the capital?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should recognize all case variations as the same answer (4/5 = 0.8)
	if !strings.Contains(strings.ToLower(response.Content), "paris") {
		t.Errorf("Expected answer to contain 'paris', got: %s", response.Content)
	}

	consistencyScore := response.Metadata["consistency_score"].(float64)
	if consistencyScore != 0.8 {
		t.Errorf("Expected consistency_score=0.8 (4/5), got: %f", consistencyScore)
	}
}

// Test answer counts metadata
func TestSelfConsistencyAnswerCounts(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"The answer is A.",
		"The answer is B.",
		"The answer is A.",
		"The answer is C.",
		"The answer is A.",
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(5),
		WithVotingStrategy(VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	response, err := sc.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	answerCounts, ok := response.Metadata["answer_counts"].(map[string]int)
	if !ok {
		t.Fatalf("Expected answer_counts to be map[string]int, got: %T", response.Metadata["answer_counts"])
	}

	// Check counts (case-insensitive, so "a" should have count 3)
	if answerCounts["a"] != 3 {
		t.Errorf("Expected count for 'a' to be 3, got: %d", answerCounts["a"])
	}
	if answerCounts["b"] != 1 {
		t.Errorf("Expected count for 'b' to be 1, got: %d", answerCounts["b"])
	}
	if answerCounts["c"] != 1 {
		t.Errorf("Expected count for 'c' to be 1, got: %d", answerCounts["c"])
	}
}

// Benchmark majority voting
func BenchmarkSelfConsistencyMajority(b *testing.B) {
	mockAgent := NewMockAgent([]string{
		"The answer is 42.",
		"The answer is 43.",
		"The answer is 42.",
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(3),
		WithVotingStrategy(VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = sc.Process(ctx, message)
	}
}

// Benchmark weighted voting
func BenchmarkSelfConsistencyWeighted(b *testing.B) {
	mockAgent := NewMockAgent([]string{
		"The answer is 42.",
		"After extensive analysis, I believe 43 is the correct answer.",
		"The answer is 42.",
	})

	sc := NewSelfConsistency(
		mockAgent,
		WithNumSamples(3),
		WithVotingStrategy(VotingStrategyWeighted),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test question")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = sc.Process(ctx, message)
	}
}
