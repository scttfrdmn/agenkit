package reasoning

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// VariedMockAgent generates varied responses for tree branching
type VariedMockAgent struct {
	callCount int
	mu        sync.Mutex
}

func NewVariedMockAgent() *VariedMockAgent {
	return &VariedMockAgent{callCount: 0}
}

func (m *VariedMockAgent) Name() string {
	return "varied_mock_agent"
}

func (m *VariedMockAgent) Capabilities() []string {
	return []string{"mock", "testing"}
}

func (m *VariedMockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	m.mu.Lock()
	m.callCount++
	count := m.callCount
	m.mu.Unlock()

	// Generate varied responses for tree branches
	responses := []string{
		fmt.Sprintf("Branch A: Analyze systematically (call %d).", count),
		fmt.Sprintf("Branch B: Break into parts (call %d).", count),
		fmt.Sprintf("Branch C: Consider edge cases (call %d).", count),
		fmt.Sprintf("Step %d: Continue with details.", count),
	}

	response := responses[count%len(responses)]
	return agenkit.NewMessage("assistant", response), nil
}

func (m *VariedMockAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(m)
}

// Test basic Tree-of-Thought functionality
func TestTreeOfThoughtBasic(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	tot := NewTreeOfThought(
		mockAgent,
		WithBranchingFactor(2),
		WithMaxDepth(2),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Solve this problem")

	response, err := tot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Check metadata
	if response.Metadata["technique"] != "tree_of_thought" {
		t.Errorf("Expected technique='tree_of_thought', got: %v", response.Metadata["technique"])
	}

	// Check search strategy
	if _, ok := response.Metadata["search_strategy"].(string); !ok {
		t.Error("Expected search_strategy to be present")
	}

	// Check tree statistics
	if _, ok := response.Metadata["reasoning_tree_stats"].(TreeStatistics); !ok {
		t.Error("Expected reasoning_tree_stats to be present")
	}

	// Check reasoning path
	path, ok := response.Metadata["reasoning_path"].([]string)
	if !ok {
		t.Fatalf("Expected reasoning_path to be []string, got: %T", response.Metadata["reasoning_path"])
	}

	if len(path) == 0 {
		t.Error("Expected reasoning_path to have at least one step")
	}

	// Check num_steps
	numSteps, ok := response.Metadata["num_steps"].(int)
	if !ok || numSteps == 0 {
		t.Errorf("Expected num_steps > 0, got: %v", response.Metadata["num_steps"])
	}

	// Check best_score
	if _, ok := response.Metadata["best_score"].(float64); !ok {
		t.Error("Expected best_score to be present")
	}
}

// Test name and capabilities
func TestTreeOfThoughtNameAndCapabilities(t *testing.T) {
	mockAgent := NewVariedMockAgent()
	tot := NewTreeOfThought(mockAgent)

	if tot.Name() != "tree_of_thought" {
		t.Errorf("Expected name='tree_of_thought', got: %s", tot.Name())
	}

	caps := tot.Capabilities()
	expectedCaps := []string{"reasoning", "tree_search", "multi_path_exploration", "backtracking", "tree_of_thought", "planning"}

	for _, expected := range expectedCaps {
		found := false
		for _, cap := range caps {
			if cap == expected {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected capability '%s' not found in: %v", expected, caps)
		}
	}
}

// Test BFS search strategy
func TestTreeOfThoughtBFS(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	tot := NewTreeOfThought(
		mockAgent,
		WithBranchingFactor(2),
		WithMaxDepth(2),
		WithStrategy(SearchStrategyBFS),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test query")

	response, err := tot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	strategy, ok := response.Metadata["search_strategy"].(string)
	if !ok || strategy != "bfs" {
		t.Errorf("Expected search_strategy='bfs', got: %v", response.Metadata["search_strategy"])
	}
}

// Test DFS search strategy
func TestTreeOfThoughtDFS(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	tot := NewTreeOfThought(
		mockAgent,
		WithBranchingFactor(2),
		WithMaxDepth(2),
		WithStrategy(SearchStrategyDFS),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test query")

	response, err := tot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	strategy, ok := response.Metadata["search_strategy"].(string)
	if !ok || strategy != "dfs" {
		t.Errorf("Expected search_strategy='dfs', got: %v", response.Metadata["search_strategy"])
	}
}

// Test best-first search strategy
func TestTreeOfThoughtBestFirst(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	tot := NewTreeOfThought(
		mockAgent,
		WithBranchingFactor(2),
		WithMaxDepth(2),
		WithStrategy(SearchStrategyBestFirst),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test query")

	response, err := tot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	strategy, ok := response.Metadata["search_strategy"].(string)
	if !ok || strategy != "best-first" {
		t.Errorf("Expected search_strategy='best-first', got: %v", response.Metadata["search_strategy"])
	}
}

// Test invalid strategy
func TestTreeOfThoughtInvalidStrategy(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	tot := NewTreeOfThought(
		mockAgent,
		WithStrategy("invalid"),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	_, err := tot.Process(ctx, message)
	if err == nil {
		t.Fatal("Expected error for invalid strategy")
	}

	if !strings.Contains(err.Error(), "invalid strategy") {
		t.Errorf("Expected error message about invalid strategy, got: %v", err)
	}
}

// Test tree statistics
func TestTreeOfThoughtStatistics(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	tot := NewTreeOfThought(
		mockAgent,
		WithBranchingFactor(2),
		WithMaxDepth(2),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := tot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	stats, ok := response.Metadata["reasoning_tree_stats"].(TreeStatistics)
	if !ok {
		t.Fatalf("Expected reasoning_tree_stats to be TreeStatistics")
	}

	if stats.TotalNodes < 1 {
		t.Errorf("Expected at least 1 node, got: %d", stats.TotalNodes)
	}

	if stats.MaxDepth > 2 {
		t.Errorf("Expected max depth <= 2, got: %d", stats.MaxDepth)
	}

	if stats.NumLeaves < 1 {
		t.Errorf("Expected at least 1 leaf, got: %d", stats.NumLeaves)
	}

	if stats.BestScore < 0 || stats.BestScore > 1 {
		t.Errorf("Expected best score in [0, 1], got: %f", stats.BestScore)
	}
}

// Test custom evaluator
func TestTreeOfThoughtCustomEvaluator(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	// Custom evaluator that favors responses with "Branch A"
	customEvaluator := func(text string) float64 {
		if strings.Contains(text, "Branch A") {
			return 1.0
		}
		return 0.5
	}

	tot := NewTreeOfThought(
		mockAgent,
		WithBranchingFactor(3),
		WithMaxDepth(2),
		WithEvaluator(customEvaluator),
		WithStrategy(SearchStrategyBestFirst),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := tot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Best path should contain "Branch A" due to custom evaluator
	pathText := response.Content
	if !strings.Contains(pathText, "Branch A") {
		t.Errorf("Expected best path to contain 'Branch A', got: %s", pathText)
	}
}

// Test pruning
func TestTreeOfThoughtPruning(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	// Low evaluator to trigger pruning
	lowEvaluator := func(text string) float64 {
		return 0.1 // Below default prune threshold
	}

	tot := NewTreeOfThought(
		mockAgent,
		WithBranchingFactor(3),
		WithMaxDepth(2),
		WithEvaluator(lowEvaluator),
		WithPruneThreshold(0.2),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := tot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	stats, ok := response.Metadata["reasoning_tree_stats"].(TreeStatistics)
	if !ok {
		t.Fatalf("Expected reasoning_tree_stats to be TreeStatistics")
	}

	if stats.NumPruned == 0 {
		t.Error("Expected some nodes to be pruned with low scores")
	}
}

// Test reasoning path structure
func TestTreeOfThoughtReasoningPath(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	tot := NewTreeOfThought(
		mockAgent,
		WithBranchingFactor(2),
		WithMaxDepth(3),
	)

	ctx := context.Background()
	query := "Test query"
	message := agenkit.NewMessage("user", query)

	response, err := tot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	path, ok := response.Metadata["reasoning_path"].([]string)
	if !ok {
		t.Fatalf("Expected reasoning_path to be []string")
	}

	if len(path) == 0 {
		t.Fatal("Expected non-empty reasoning path")
	}

	// First element should be the query (root node)
	if path[0] != query {
		t.Errorf("Expected first element to be query '%s', got: %s", query, path[0])
	}

	// Path length should not exceed maxDepth + 1 (root)
	if len(path) > 4 {
		t.Errorf("Expected path length <= 4, got: %d", len(path))
	}
}

// Test default evaluator behavior
func TestTreeOfThoughtDefaultEvaluator(t *testing.T) {
	// Test short response (should get low score)
	shortScore := defaultEvaluator("Hi")
	if shortScore >= 0.5 {
		t.Errorf("Expected low score for short text, got: %f", shortScore)
	}

	// Test structured response (should get bonus)
	structuredText := "1. First step with detail\n2. Second step with more content\n3. Third step"
	structuredScore := defaultEvaluator(structuredText)
	if structuredScore <= 0.2 {
		t.Errorf("Expected higher score for structured text, got: %f", structuredScore)
	}
}

// Test max depth limiting
func TestTreeOfThoughtMaxDepth(t *testing.T) {
	mockAgent := NewVariedMockAgent()

	maxDepth := 1
	tot := NewTreeOfThought(
		mockAgent,
		WithBranchingFactor(2),
		WithMaxDepth(maxDepth),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := tot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	path, ok := response.Metadata["reasoning_path"].([]string)
	if !ok {
		t.Fatalf("Expected reasoning_path to be []string")
	}

	// Root + maxDepth levels = maxDepth + 1 nodes max
	if len(path) > maxDepth+1 {
		t.Errorf("Expected path length <= %d, got: %d", maxDepth+1, len(path))
	}
}
