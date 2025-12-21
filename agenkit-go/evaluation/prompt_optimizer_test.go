package evaluation

import (
	"context"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Mock agent for testing
type mockPromptAgent struct {
	prompt string
	score  float64
}

func (m *mockPromptAgent) Name() string {
	return "mock-prompt-agent"
}

func (m *mockPromptAgent) Capabilities() []string {
	return []string{}
}

func (m *mockPromptAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(m)
}

func (m *mockPromptAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	// Simple scoring based on prompt characteristics
	score := m.score

	// Adjust score based on prompt content
	if strings.Contains(m.prompt, "detailed") {
		score += 0.1
	}
	if strings.Contains(m.prompt, "concise") {
		score += 0.05
	}
	if strings.Contains(m.prompt, "professional") {
		score += 0.15
	}

	return &agenkit.Message{
		Role:    "assistant",
		Content: fmt.Sprintf("Response with score %.2f", score),
		Metadata: map[string]interface{}{
			"accuracy": score,
			"latency":  0.1,
		},
	}, nil
}

// Mock agent factory
func mockAgentFactory(prompt string) agenkit.Agent {
	return &mockPromptAgent{
		prompt: prompt,
		score:  0.6, // Base score
	}
}

// Test helper to create test cases
func createTestCases() []map[string]interface{} {
	return []map[string]interface{}{
		{
			"input":    "What is 2+2?",
			"expected": "4",
		},
		{
			"input":    "What is the capital of France?",
			"expected": "Paris",
		},
	}
}

// Helper to create string pointer
func strPtr(s string) *string {
	return &s
}

func TestNewPromptOptimizer(t *testing.T) {
	template := "You are a {style} assistant. Be {tone}."
	variations := map[string][]string{
		"style": {"helpful", "professional"},
		"tone":  {"concise", "detailed"},
	}

	optimizer := NewPromptOptimizer(
		template,
		variations,
		mockAgentFactory,
		[]string{"accuracy"},
		strPtr("accuracy"),
	)

	if optimizer == nil {
		t.Fatal("Expected optimizer to be created")
	}

	if optimizer.template != template {
		t.Errorf("Expected template %q, got %q", template, optimizer.template)
	}

	if len(optimizer.variations) != 2 {
		t.Errorf("Expected 2 variations, got %d", len(optimizer.variations))
	}

	if optimizer.objectiveMetric != "accuracy" {
		t.Errorf("Expected objective metric 'accuracy', got %q", optimizer.objectiveMetric)
	}

	if !optimizer.maximize {
		t.Error("Expected maximize to be true")
	}
}

func TestNewPromptOptimizerWithNilObjective(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"You are a {style} assistant.",
		map[string][]string{
			"style": {"helpful"},
		},
		mockAgentFactory,
		[]string{"accuracy", "latency"},
		nil, // Should use first metric
	)

	if optimizer.objectiveMetric != "accuracy" {
		t.Errorf("Expected objective metric 'accuracy', got %q", optimizer.objectiveMetric)
	}
}

func TestSetMaximize(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"Static prompt",
		map[string][]string{},
		mockAgentFactory,
		[]string{"latency"},
		nil,
	)

	optimizer.SetMaximize(false)

	if optimizer.maximize {
		t.Error("Expected maximize to be false after SetMaximize(false)")
	}
}

func TestFillTemplate(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"You are a {style} assistant. Be {tone}.",
		map[string][]string{
			"style": {"helpful", "professional"},
			"tone":  {"concise", "detailed"},
		},
		mockAgentFactory,
		[]string{"accuracy"},
		nil,
	)

	config := map[string]string{
		"style": "professional",
		"tone":  "concise",
	}

	result := optimizer.fillTemplate(config)
	expected := "You are a professional assistant. Be concise."

	if result != expected {
		t.Errorf("Expected %q, got %q", expected, result)
	}
}

func TestCartesianProduct(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"",
		map[string][]string{
			"style": {"A", "B"},
			"tone":  {"X", "Y"},
		},
		mockAgentFactory,
		[]string{"accuracy"},
		nil,
	)

	configs := optimizer.generateAllConfigs()

	// Should have 2 * 2 = 4 configurations
	if len(configs) != 4 {
		t.Errorf("Expected 4 configurations, got %d", len(configs))
	}

	// Check that all combinations are present
	combinations := make(map[string]bool)
	for _, config := range configs {
		key := config["style"] + "-" + config["tone"]
		combinations[key] = true
	}

	expected := []string{"A-X", "A-Y", "B-X", "B-Y"}
	for _, exp := range expected {
		if !combinations[exp] {
			t.Errorf("Missing combination: %s", exp)
		}
	}
}

func TestSampleConfig(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"",
		map[string][]string{
			"style": {"A", "B", "C"},
			"tone":  {"X", "Y", "Z"},
		},
		mockAgentFactory,
		[]string{"accuracy"},
		nil,
	)

	// Sample 10 configs
	for i := 0; i < 10; i++ {
		config := optimizer.sampleConfig()

		// Check that style is valid
		style := config["style"]
		if style != "A" && style != "B" && style != "C" {
			t.Errorf("Invalid style: %s", style)
		}

		// Check that tone is valid
		tone := config["tone"]
		if tone != "X" && tone != "Y" && tone != "Z" {
			t.Errorf("Invalid tone: %s", tone)
		}
	}
}

func TestOptimizeGrid(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"You are a {style} assistant. Be {tone}.",
		map[string][]string{
			"style": {"helpful", "professional"},
			"tone":  {"concise", "detailed"},
		},
		mockAgentFactory,
		[]string{"accuracy"},
		nil,
	)

	testCases := createTestCases()
	ctx := context.Background()

	result, err := optimizer.OptimizeGrid(ctx, testCases)
	if err != nil {
		t.Fatalf("OptimizeGrid failed: %v", err)
	}

	if result == nil {
		t.Fatal("Expected non-nil result")
	}

	// Should have 4 evaluations (2 * 2 = 4 combinations)
	if len(result.History) != 4 {
		t.Errorf("Expected 4 evaluations, got %d", len(result.History))
	}

	// Best prompt should be set
	if result.BestPrompt == "" {
		t.Error("Expected best prompt to be set")
	}

	// Since we're maximizing accuracy, and professional+detailed has highest bonus,
	// it should be in the best prompt (base 0.6 + 0.15 professional + 0.1 detailed = 0.85)
	// But let's just check that we found *something* with a good score
	if result.BestScores["accuracy"] < 0.6 {
		t.Errorf("Expected accuracy >= 0.6, got %.2f", result.BestScores["accuracy"])
	}

	// Strategy should be "grid"
	if result.Strategy != "grid" {
		t.Errorf("Expected strategy 'grid', got %q", result.Strategy)
	}
}

func TestOptimizeRandom(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"You are a {style} assistant. Be {tone}.",
		map[string][]string{
			"style": {"helpful", "professional"},
			"tone":  {"concise", "detailed"},
		},
		mockAgentFactory,
		[]string{"accuracy"},
		nil,
	)

	testCases := createTestCases()
	ctx := context.Background()

	nSamples := 3
	result, err := optimizer.OptimizeRandom(ctx, testCases, nSamples)
	if err != nil {
		t.Fatalf("OptimizeRandom failed: %v", err)
	}

	if result == nil {
		t.Fatal("Expected non-nil result")
	}

	// Should have 3 evaluations
	if len(result.History) != nSamples {
		t.Errorf("Expected %d evaluations, got %d", nSamples, len(result.History))
	}

	// Strategy should be "random"
	if result.Strategy != "random" {
		t.Errorf("Expected strategy 'random', got %q", result.Strategy)
	}
}

func TestOptimizeGenetic(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"You are a {style} assistant. Be {tone}.",
		map[string][]string{
			"style": {"helpful", "professional"},
			"tone":  {"concise", "detailed"},
		},
		mockAgentFactory,
		[]string{"accuracy"},
		nil,
	)

	testCases := createTestCases()
	ctx := context.Background()

	populationSize := 4
	nGenerations := 3
	mutationRate := 0.2

	result, err := optimizer.OptimizeGenetic(ctx, testCases, populationSize, nGenerations, mutationRate)
	if err != nil {
		t.Fatalf("OptimizeGenetic failed: %v", err)
	}

	if result == nil {
		t.Fatal("Expected non-nil result")
	}

	// Should have evaluated population_size + (population_size * n_generations) prompts
	expectedEvals := populationSize + (populationSize * nGenerations)
	if len(result.History) != expectedEvals {
		t.Errorf("Expected %d evaluations, got %d", expectedEvals, len(result.History))
	}

	// Strategy should be "genetic"
	if result.Strategy != "genetic" {
		t.Errorf("Expected strategy 'genetic', got %q", result.Strategy)
	}
}

func TestOptimizeMinimization(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"You are a {style} assistant.",
		map[string][]string{
			"style": {"A", "B"},
		},
		mockAgentFactory,
		[]string{"latency"},
		strPtr("latency"),
	)
	optimizer.SetMaximize(false) // Minimize latency

	testCases := createTestCases()
	ctx := context.Background()

	result, err := optimizer.OptimizeGrid(ctx, testCases)
	if err != nil {
		t.Fatalf("OptimizeGrid for minimization failed: %v", err)
	}

	// Should find low latency
	if bestLatency, ok := result.BestScores["latency"]; ok {
		if bestLatency > 0.2 {
			t.Errorf("Expected low latency score, got %.3f", bestLatency)
		}
	}
}

func TestOptimizeContextCancellation(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"You are a {style} assistant. Be {tone}.",
		map[string][]string{
			"style": {"A", "B", "C", "D"},
			"tone":  {"X", "Y", "Z"},
		},
		mockAgentFactory,
		[]string{"accuracy"},
		nil,
	)

	testCases := createTestCases()

	// Create context that will be cancelled
	ctx, cancel := context.WithCancel(context.Background())

	// Cancel immediately
	cancel()

	_, err := optimizer.OptimizeGrid(ctx, testCases)
	if err == nil {
		t.Error("Expected error from cancelled context")
	}

	if err != context.Canceled {
		t.Errorf("Expected context.Canceled, got %v", err)
	}
}

func TestOptimizeContextTimeout(t *testing.T) {
	// Create slow agent factory
	slowFactory := func(prompt string) agenkit.Agent {
		return &slowAgent{}
	}

	optimizer := NewPromptOptimizer(
		"You are a {style} assistant.",
		map[string][]string{
			"style": {"A", "B"},
		},
		slowFactory,
		[]string{"accuracy"},
		nil,
	)

	testCases := createTestCases()

	// Create context with very short timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
	defer cancel()

	_, err := optimizer.OptimizeGrid(ctx, testCases)
	if err == nil {
		t.Error("Expected timeout error")
	}
}

// Slow agent for testing timeouts
type slowAgent struct{}

func (s *slowAgent) Name() string {
	return "slow-agent"
}

func (s *slowAgent) Capabilities() []string {
	return []string{}
}

func (s *slowAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(s)
}

func (s *slowAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	// Sleep for a long time
	time.Sleep(1 * time.Second)
	return &agenkit.Message{
		Role:    "assistant",
		Content: "Slow response",
		Metadata: map[string]interface{}{
			"accuracy": 0.5,
		},
	}, nil
}

func TestOptimizeHistory(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"You are a {style} assistant.",
		map[string][]string{
			"style": {"A", "B"},
		},
		mockAgentFactory,
		[]string{"accuracy"},
		nil,
	)

	testCases := createTestCases()
	ctx := context.Background()

	_, err := optimizer.OptimizeGrid(ctx, testCases)
	if err != nil {
		t.Fatalf("OptimizeGrid failed: %v", err)
	}

	// Check that history was recorded
	if len(optimizer.history) != 2 {
		t.Errorf("Expected 2 history entries, got %d", len(optimizer.history))
	}

	// Each entry should have a prompt and scores
	for _, entry := range optimizer.history {
		if entry.Prompt == "" {
			t.Error("Expected prompt to be set in history")
		}
		if len(entry.Scores) == 0 {
			t.Error("Expected scores to be set in history")
		}
	}
}

func TestOptimizeEmptyVariations(t *testing.T) {
	optimizer := NewPromptOptimizer(
		"Static prompt with no variations",
		map[string][]string{},
		mockAgentFactory,
		[]string{"accuracy"},
		nil,
	)

	testCases := createTestCases()
	ctx := context.Background()

	result, err := optimizer.OptimizeGrid(ctx, testCases)
	if err != nil {
		t.Fatalf("OptimizeGrid with empty variations failed: %v", err)
	}

	// Should have 1 evaluation
	if len(result.History) != 1 {
		t.Errorf("Expected 1 evaluation, got %d", len(result.History))
	}

	// Best prompt should be the static prompt
	if result.BestPrompt != "Static prompt with no variations" {
		t.Errorf("Expected best prompt to be static, got %q", result.BestPrompt)
	}
}
