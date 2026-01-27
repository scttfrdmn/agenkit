package reasoning

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Test basic Least-to-Most functionality
func TestLeastToMostBasic(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		// Decomposition response
		"1. Calculate 3*4\n2. Calculate 2*5\n3. Add the results",
		// Solutions
		"12",
		"10",
		"22",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Calculate 3*4 + 2*5")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Check response content
	if response.Content != "22" {
		t.Errorf("Expected content='22', got: %s", response.Content)
	}

	// Check metadata
	if response.Metadata["technique"] != "least_to_most" {
		t.Errorf("Expected technique='least_to_most', got: %v", response.Metadata["technique"])
	}

	numSubproblems, ok := response.Metadata["num_subproblems"].(int)
	if !ok || numSubproblems != 3 {
		t.Errorf("Expected num_subproblems=3, got: %v", response.Metadata["num_subproblems"])
	}

	subproblems, ok := response.Metadata["subproblems"].([]string)
	if !ok || len(subproblems) != 3 {
		t.Errorf("Expected 3 subproblems, got: %v", response.Metadata["subproblems"])
	}

	solutions, ok := response.Metadata["subproblem_solutions"].([]string)
	if !ok || len(solutions) != 3 {
		t.Errorf("Expected 3 solutions, got: %v", response.Metadata["subproblem_solutions"])
	}
}

// Test name and capabilities
func TestLeastToMostNameAndCapabilities(t *testing.T) {
	mockAgent := NewMockAgent([]string{"response"})
	ltm := NewLeastToMost(mockAgent)

	if ltm.Name() != "least_to_most" {
		t.Errorf("Expected name='least_to_most', got: %s", ltm.Name())
	}

	caps := ltm.Capabilities()
	expectedCaps := []string{
		"reasoning",
		"decomposition",
		"compositional_reasoning",
		"least_to_most",
		"sequential_solving",
	}

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

// Test decomposition into subproblems
func TestLeastToMostDecomposition(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. First subproblem\n2. Second subproblem\n3. Third subproblem",
		"Solution 1",
		"Solution 2",
		"Solution 3",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Complex problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	subproblems, ok := response.Metadata["subproblems"].([]string)
	if !ok {
		t.Fatalf("Expected subproblems to be []string")
	}

	expected := []string{"First subproblem", "Second subproblem", "Third subproblem"}
	if len(subproblems) != len(expected) {
		t.Fatalf("Expected %d subproblems, got %d", len(expected), len(subproblems))
	}

	for i, exp := range expected {
		if subproblems[i] != exp {
			t.Errorf("Subproblem %d: expected '%s', got '%s'", i, exp, subproblems[i])
		}
	}
}

// Test sequential solving
func TestLeastToMostSequentialSolving(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. Step A\n2. Step B",
		"Answer A",
		"Answer B",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	solutions, ok := response.Metadata["subproblem_solutions"].([]string)
	if !ok {
		t.Fatalf("Expected subproblem_solutions to be []string")
	}

	expected := []string{"Answer A", "Answer B"}
	if len(solutions) != len(expected) {
		t.Fatalf("Expected %d solutions, got %d", len(expected), len(solutions))
	}

	for i, exp := range expected {
		if solutions[i] != exp {
			t.Errorf("Solution %d: expected '%s', got '%s'", i, exp, solutions[i])
		}
	}
}

// Test final solution is last
func TestLeastToMostFinalSolution(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. Subproblem 1\n2. Subproblem 2",
		"Intermediate",
		"Final answer",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if response.Content != "Final answer" {
		t.Errorf("Expected content='Final answer', got: %s", response.Content)
	}

	if response.Role != "assistant" {
		t.Errorf("Expected role='assistant', got: %s", response.Role)
	}
}

// Test maxSubproblems limit
func TestLeastToMostMaxSubproblemsLimit(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. Sub 1\n2. Sub 2\n3. Sub 3\n4. Sub 4\n5. Sub 5\n6. Sub 6",
		"S1",
		"S2",
		"S3",
	})

	ltm := NewLeastToMost(mockAgent, WithLTMMaxSubproblems(3))

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	numSubproblems, ok := response.Metadata["num_subproblems"].(int)
	if !ok || numSubproblems != 3 {
		t.Errorf("Expected num_subproblems=3, got: %v", response.Metadata["num_subproblems"])
	}

	subproblems, ok := response.Metadata["subproblems"].([]string)
	if !ok || len(subproblems) != 3 {
		t.Errorf("Expected 3 subproblems, got: %d", len(subproblems))
	}
}

// Test custom decomposer
func TestLeastToMostCustomDecomposer(t *testing.T) {
	customDecomposer := func(problem string) ([]string, error) {
		return []string{
			"Custom step 1",
			"Custom step 2",
			"Custom step 3",
		}, nil
	}

	mockAgent := NewMockAgent([]string{"Sol 1", "Sol 2", "Sol 3"})

	ltm := NewLeastToMost(mockAgent, WithLTMDecomposer(customDecomposer))

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Any problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	subproblems, ok := response.Metadata["subproblems"].([]string)
	if !ok {
		t.Fatalf("Expected subproblems to be []string")
	}

	expected := []string{"Custom step 1", "Custom step 2", "Custom step 3"}
	if len(subproblems) != len(expected) {
		t.Fatalf("Expected %d subproblems, got %d", len(expected), len(subproblems))
	}

	for i, exp := range expected {
		if subproblems[i] != exp {
			t.Errorf("Subproblem %d: expected '%s', got '%s'", i, exp, subproblems[i])
		}
	}
}

// Test custom decomposer error handling
func TestLeastToMostCustomDecomposerError(t *testing.T) {
	failingDecomposer := func(problem string) ([]string, error) {
		return nil, fmt.Errorf("decomposer failed")
	}

	mockAgent := NewMockAgent([]string{})

	ltm := NewLeastToMost(mockAgent, WithLTMDecomposer(failingDecomposer))

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	_, err := ltm.Process(ctx, message)
	if err == nil {
		t.Fatal("Expected error from failing decomposer")
	}

	if !strings.Contains(err.Error(), "custom decomposer failed") {
		t.Errorf("Expected error message about decomposer, got: %v", err)
	}
}

// Test solution composition enabled (default)
func TestLeastToMostComposeSolutionsEnabled(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. Sub 1\n2. Sub 2",
		"Solution 1",
		"Solution 2",
	})

	ltm := NewLeastToMost(mockAgent, WithComposeSolutions(true))

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify compose_solutions is enabled
	composeSolutions, ok := response.Metadata["compose_solutions"].(bool)
	if !ok || !composeSolutions {
		t.Errorf("Expected compose_solutions=true, got: %v", response.Metadata["compose_solutions"])
	}

	// Verify solutions were composed
	solutions, ok := response.Metadata["subproblem_solutions"].([]string)
	if !ok || len(solutions) != 2 {
		t.Errorf("Expected 2 solutions, got: %v", response.Metadata["subproblem_solutions"])
	}
}

// Test solution composition disabled
func TestLeastToMostComposeSolutionsDisabled(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. Sub 1\n2. Sub 2",
		"Solution",
		"Solution",
	})

	ltm := NewLeastToMost(mockAgent, WithComposeSolutions(false))

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify compose_solutions is disabled
	composeSolutions, ok := response.Metadata["compose_solutions"].(bool)
	if !ok || composeSolutions {
		t.Errorf("Expected compose_solutions=false, got: %v", response.Metadata["compose_solutions"])
	}

	// Verify solutions exist
	solutions, ok := response.Metadata["subproblem_solutions"].([]string)
	if !ok || len(solutions) != 2 {
		t.Errorf("Expected 2 solutions, got: %v", response.Metadata["subproblem_solutions"])
	}
}

// Test parsing numbered steps with periods
func TestLeastToMostParseNumberedStepsPeriods(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. First\n2. Second\n3. Third",
		"S1",
		"S2",
		"S3",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	subproblems, ok := response.Metadata["subproblems"].([]string)
	if !ok {
		t.Fatalf("Expected subproblems to be []string")
	}

	expected := []string{"First", "Second", "Third"}
	if len(subproblems) != len(expected) {
		t.Fatalf("Expected %d subproblems, got %d", len(expected), len(subproblems))
	}

	for i, exp := range expected {
		if subproblems[i] != exp {
			t.Errorf("Subproblem %d: expected '%s', got '%s'", i, exp, subproblems[i])
		}
	}
}

// Test parsing numbered steps with parentheses
func TestLeastToMostParseNumberedStepsParens(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1) First\n2) Second\n3) Third",
		"S1",
		"S2",
		"S3",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	subproblems, ok := response.Metadata["subproblems"].([]string)
	if !ok {
		t.Fatalf("Expected subproblems to be []string")
	}

	expected := []string{"First", "Second", "Third"}
	if len(subproblems) != len(expected) {
		t.Fatalf("Expected %d subproblems, got %d", len(expected), len(subproblems))
	}

	for i, exp := range expected {
		if subproblems[i] != exp {
			t.Errorf("Subproblem %d: expected '%s', got '%s'", i, exp, subproblems[i])
		}
	}
}

// Test skipping empty lines
func TestLeastToMostSkipEmptyLines(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. First\n\n2. Second\n\n\n3. Third",
		"S1",
		"S2",
		"S3",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	numSubproblems, ok := response.Metadata["num_subproblems"].(int)
	if !ok || numSubproblems != 3 {
		t.Errorf("Expected num_subproblems=3, got: %v", response.Metadata["num_subproblems"])
	}
}

// Test atomic problem when decomposition fails
func TestLeastToMostAtomicProblem(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"No valid decomposition",
		"Single solution",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Simple problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	numSubproblems, ok := response.Metadata["num_subproblems"].(int)
	if !ok || numSubproblems != 1 {
		t.Errorf("Expected num_subproblems=1, got: %v", response.Metadata["num_subproblems"])
	}

	subproblems, ok := response.Metadata["subproblems"].([]string)
	if !ok {
		t.Fatalf("Expected subproblems to be []string")
	}

	if len(subproblems) != 1 || subproblems[0] != "Simple problem" {
		t.Errorf("Expected atomic problem, got: %v", subproblems)
	}

	if response.Content != "Single solution" {
		t.Errorf("Expected content='Single solution', got: %s", response.Content)
	}
}

// Test whitespace trimming in decomposition
func TestLeastToMostWhitespaceTrimming(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"  1.   Trimmed   \n  2.   Also trimmed   ",
		"S1",
		"S2",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	subproblems, ok := response.Metadata["subproblems"].([]string)
	if !ok {
		t.Fatalf("Expected subproblems to be []string")
	}

	expected := []string{"Trimmed", "Also trimmed"}
	if len(subproblems) != len(expected) {
		t.Fatalf("Expected %d subproblems, got %d", len(expected), len(subproblems))
	}

	for i, exp := range expected {
		if subproblems[i] != exp {
			t.Errorf("Subproblem %d: expected '%s', got '%s'", i, exp, subproblems[i])
		}
	}
}

// Test compose_solutions metadata
func TestLeastToMostComposeSolutionsMetadata(t *testing.T) {
	mockAgent := NewMockAgent([]string{"1. Sub", "Sol"})

	ltm1 := NewLeastToMost(mockAgent, WithComposeSolutions(true))

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response1, err := ltm1.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	composeSolutions, ok := response1.Metadata["compose_solutions"].(bool)
	if !ok || !composeSolutions {
		t.Errorf("Expected compose_solutions=true, got: %v", response1.Metadata["compose_solutions"])
	}

	// Test disabled
	mockAgent = NewMockAgent([]string{"1. Sub", "Sol"})
	ltm2 := NewLeastToMost(mockAgent, WithComposeSolutions(false))

	response2, err := ltm2.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	composeSolutions, ok = response2.Metadata["compose_solutions"].(bool)
	if !ok || composeSolutions {
		t.Errorf("Expected compose_solutions=false, got: %v", response2.Metadata["compose_solutions"])
	}
}

// Test multiline subproblem content
func TestLeastToMostMultilineSubproblem(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. First part\n   continued\n2. Second",
		"S1",
		"S2",
	})

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	response, err := ltm.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should only parse lines starting with numbers
	numSubproblems, ok := response.Metadata["num_subproblems"].(int)
	if !ok || numSubproblems != 2 {
		t.Errorf("Expected num_subproblems=2, got: %v", response.Metadata["num_subproblems"])
	}
}

// Test error propagation
func TestLeastToMostErrorPropagation(t *testing.T) {
	mockAgent := NewMockAgent([]string{"response"})
	mockAgent.shouldFail = true

	ltm := NewLeastToMost(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Problem")

	_, err := ltm.Process(ctx, message)
	if err == nil {
		t.Fatal("Expected error from failing agent")
	}

	if !strings.Contains(err.Error(), "mock agent failed") {
		t.Errorf("Expected error message about agent failure, got: %v", err)
	}
}
