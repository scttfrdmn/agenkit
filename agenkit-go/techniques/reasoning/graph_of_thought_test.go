package reasoning

import (
	"context"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mockAgent is a simple mock agent for testing.
type mockGraphAgent struct {
	responses map[string]string
}

func (m *mockGraphAgent) Name() string {
	return "mock_graph_agent"
}

func (m *mockGraphAgent) Capabilities() []string {
	return []string{"test"}
}

func (m *mockGraphAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(m)
}

func (m *mockGraphAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.ContentString()

	// Match patterns and return appropriate responses
	for pattern, response := range m.responses {
		if strings.Contains(content, pattern) {
			return &agenkit.Message{
				Role:     "assistant",
				Content:  response,
				Metadata: make(map[string]interface{}),
			}, nil
		}
	}

	// Default response
	return &agenkit.Message{
		Role:     "assistant",
		Content:  "Default response",
		Metadata: make(map[string]interface{}),
	}, nil
}

// TestGraphOfThoughtCreation tests creating a GraphOfThought agent.
func TestGraphOfThoughtCreation(t *testing.T) {
	baseAgent := &mockGraphAgent{
		responses: make(map[string]string),
	}

	got := NewGraphOfThought(baseAgent)

	if got.Name() != "graph_of_thought" {
		t.Errorf("Expected name 'graph_of_thought', got '%s'", got.Name())
	}

	if got.maxNodes != 20 {
		t.Errorf("Expected default maxNodes 20, got %d", got.maxNodes)
	}

	if got.maxEdges != 40 {
		t.Errorf("Expected default maxEdges 40, got %d", got.maxEdges)
	}

	if got.aggregator != AggregatorPathBased {
		t.Errorf("Expected default aggregator path_based, got %s", got.aggregator)
	}

	if got.allowCycles {
		t.Error("Expected allowCycles to be false by default")
	}
}

// TestGraphOfThoughtWithOptions tests configuring GraphOfThought with options.
func TestGraphOfThoughtWithOptions(t *testing.T) {
	baseAgent := &mockGraphAgent{
		responses: make(map[string]string),
	}

	got := NewGraphOfThought(
		baseAgent,
		WithMaxNodes(15),
		WithMaxEdges(30),
		WithAggregator(AggregatorNodeBased),
		WithAllowCycles(true),
	)

	if got.maxNodes != 15 {
		t.Errorf("Expected maxNodes 15, got %d", got.maxNodes)
	}

	if got.maxEdges != 30 {
		t.Errorf("Expected maxEdges 30, got %d", got.maxEdges)
	}

	if got.aggregator != AggregatorNodeBased {
		t.Errorf("Expected aggregator node_based, got %s", got.aggregator)
	}

	if !got.allowCycles {
		t.Error("Expected allowCycles to be true")
	}
}

// TestGraphOfThoughtCapabilities tests the capabilities method.
func TestGraphOfThoughtCapabilities(t *testing.T) {
	baseAgent := &mockGraphAgent{
		responses: make(map[string]string),
	}

	got := NewGraphOfThought(baseAgent)
	caps := got.Capabilities()

	expectedCaps := []string{
		"reasoning",
		"graph_of_thought",
		"multi_hop_reasoning",
		"path_aggregation",
		"complex_synthesis",
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("Expected %d capabilities, got %d", len(expectedCaps), len(caps))
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
			t.Errorf("Expected capability '%s' not found", expected)
		}
	}
}

// TestGeneratePremises tests generating premises from a problem.
func TestGeneratePremises(t *testing.T) {
	baseAgent := &mockGraphAgent{
		responses: map[string]string{
			"Premises": "1. Paris is the capital of France\n2. France is in Europe\n3. Europe is a continent",
		},
	}

	got := NewGraphOfThought(baseAgent)
	ctx := context.Background()

	premises, err := got.GeneratePremises(ctx, "What is the capital of France?")
	if err != nil {
		t.Fatalf("GeneratePremises failed: %v", err)
	}

	if len(premises) != 3 {
		t.Errorf("Expected 3 premises, got %d", len(premises))
	}

	// Check that numbering was removed
	for _, premise := range premises {
		if strings.HasPrefix(premise, "1.") || strings.HasPrefix(premise, "2.") {
			t.Errorf("Premise should not contain numbering: %s", premise)
		}
	}
}

// TestGenerateThoughts tests generating new thoughts.
func TestGenerateThoughts(t *testing.T) {
	baseAgent := &mockGraphAgent{
		responses: map[string]string{
			"New thoughts": "- The capital city is a major urban center\n- It has significant historical importance\n- It's a tourist destination",
		},
	}

	got := NewGraphOfThought(baseAgent)
	ctx := context.Background()

	existing := []string{"Paris is the capital of France"}
	thoughts, err := got.GenerateThoughts(ctx, "What is special about Paris?", existing, 3)
	if err != nil {
		t.Fatalf("GenerateThoughts failed: %v", err)
	}

	if len(thoughts) == 0 {
		t.Error("Expected at least one thought")
	}

	// Check that bullets were removed
	for _, thought := range thoughts {
		if strings.HasPrefix(thought, "-") || strings.HasPrefix(thought, "•") {
			t.Errorf("Thought should not contain bullet: %s", thought)
		}
	}
}

// TestIdentifyConnections tests identifying logical connections between thoughts.
func TestIdentifyConnections(t *testing.T) {
	tests := []struct {
		name       string
		response   string
		expectedEdge EdgeType
		expectError bool
	}{
		{
			name:         "Support relationship",
			response:     "SUPPORT",
			expectedEdge: EdgeTypeSupports,
			expectError:  false,
		},
		{
			name:         "Dependency relationship",
			response:     "DEPEND",
			expectedEdge: EdgeTypeDependsOn,
			expectError:  false,
		},
		{
			name:         "Contradiction relationship",
			response:     "CONTRADICT",
			expectedEdge: EdgeTypeContradicts,
			expectError:  false,
		},
		{
			name:         "Refinement relationship",
			response:     "REFINE",
			expectedEdge: EdgeTypeRefines,
			expectError:  false,
		},
		{
			name:         "No relationship",
			response:     "NO_RELATION",
			expectedEdge: "",
			expectError:  true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			baseAgent := &mockGraphAgent{
				responses: map[string]string{
					"relationship": tt.response,
				},
			}

			got := NewGraphOfThought(baseAgent)
			ctx := context.Background()

			edgeType, err := got.IdentifyConnections(ctx, "Statement 1", "Statement 2")

			if tt.expectError {
				if err == nil {
					t.Error("Expected error but got none")
				}
			} else {
				if err != nil {
					t.Fatalf("Unexpected error: %v", err)
				}
				if edgeType != tt.expectedEdge {
					t.Errorf("Expected edge type %s, got %s", tt.expectedEdge, edgeType)
				}
			}
		})
	}
}

// TestBuildGraph tests building a reasoning graph.
func TestBuildGraph(t *testing.T) {
	baseAgent := &mockGraphAgent{
		responses: map[string]string{
			"Premises": "1. Machine learning uses algorithms\n2. Algorithms process data",
			"New thoughts": "- ML can predict outcomes\n- Data quality matters",
			"relationship": "SUPPORT",
			"Final conclusion": "Machine learning is powerful but requires good data",
		},
	}

	got := NewGraphOfThought(baseAgent, WithMaxNodes(8), WithMaxEdges(10))
	ctx := context.Background()

	graph, err := got.BuildGraph(ctx, "How does machine learning work?")
	if err != nil {
		t.Fatalf("BuildGraph failed: %v", err)
	}

	stats := graph.Statistics()

	if stats.NumNodes == 0 {
		t.Error("Expected graph to have nodes")
	}

	if stats.NumNodes > 8 {
		t.Errorf("Expected max 8 nodes, got %d", stats.NumNodes)
	}

	if stats.NumEdges > 10 {
		t.Errorf("Expected max 10 edges, got %d", stats.NumEdges)
	}

	// Check that we have different node types
	if stats.NodeTypes[string(NodeTypePremise)] == 0 {
		t.Error("Expected at least one premise node")
	}
}

// TestFindReasoningPaths tests finding paths from premises to conclusions.
func TestFindReasoningPaths(t *testing.T) {
	graph := NewReasoningGraph()

	// Build a simple graph: premise -> intermediate -> conclusion
	premiseID := graph.AddNode("Start", NodeTypePremise, 0.9, nil)
	intermediateID := graph.AddNode("Middle", NodeTypeIntermediate, 0.8, nil)
	conclusionID := graph.AddNode("End", NodeTypeConclusion, 0.9, nil)

	_ = graph.AddEdge(premiseID, intermediateID, EdgeTypeSupports, 0.8, nil)
	_ = graph.AddEdge(intermediateID, conclusionID, EdgeTypeSupports, 0.9, nil)

	baseAgent := &mockGraphAgent{responses: make(map[string]string)}
	got := NewGraphOfThought(baseAgent)

	paths := got.FindReasoningPaths(graph)

	if len(paths) == 0 {
		t.Error("Expected to find at least one reasoning path")
	}

	// Check that path goes from premise to conclusion
	if len(paths) > 0 {
		firstPath := paths[0]
		if len(firstPath) < 2 {
			t.Error("Expected path to have at least 2 nodes")
		}
		if firstPath[0] != premiseID {
			t.Errorf("Expected path to start with premise %d, got %d", premiseID, firstPath[0])
		}
		if firstPath[len(firstPath)-1] != conclusionID {
			t.Errorf("Expected path to end with conclusion %d, got %d", conclusionID, firstPath[len(firstPath)-1])
		}
	}
}

// TestAggregatePaths tests aggregating reasoning paths.
func TestAggregatePaths(t *testing.T) {
	graph := NewReasoningGraph()

	// Build a simple graph with paths
	node1 := graph.AddNode("First thought", NodeTypePremise, 0.9, nil)
	node2 := graph.AddNode("Second thought", NodeTypeIntermediate, 0.8, nil)
	node3 := graph.AddNode("Final answer", NodeTypeConclusion, 0.9, nil)

	_ = graph.AddEdge(node1, node2, EdgeTypeSupports, 0.8, nil)
	_ = graph.AddEdge(node2, node3, EdgeTypeSupports, 0.9, nil)

	baseAgent := &mockGraphAgent{responses: make(map[string]string)}
	got := NewGraphOfThought(baseAgent, WithAggregator(AggregatorPathBased))

	paths := [][]int{{node1, node2, node3}}
	result := got.AggregatePaths(graph, paths)

	if result != "Final answer" {
		t.Errorf("Expected 'Final answer', got '%s'", result)
	}

	// Test node-based aggregation
	got.aggregator = AggregatorNodeBased
	result = got.AggregatePaths(graph, paths)

	if result == "" {
		t.Error("Expected non-empty result from node-based aggregation")
	}
}

// TestProcess tests the complete Process method.
func TestProcess(t *testing.T) {
	baseAgent := &mockGraphAgent{
		responses: map[string]string{
			"Premises": "1. Premise A\n2. Premise B",
			"New thoughts": "- Thought 1\n- Thought 2",
			"relationship": "SUPPORT",
			"Final conclusion": "This is the answer",
		},
	}

	got := NewGraphOfThought(baseAgent, WithMaxNodes(6), WithMaxEdges(8))
	ctx := context.Background()

	message := &agenkit.Message{
		Role:     "user",
		Content:  "Test problem",
		Metadata: make(map[string]interface{}),
	}

	response, err := got.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if response.Role != "assistant" {
		t.Errorf("Expected role 'assistant', got '%s'", response.Role)
	}

	if response.ContentString() == "" {
		t.Error("Expected non-empty content")
	}

	// Check metadata
	if response.Metadata["technique"] != "graph_of_thought" {
		t.Errorf("Expected technique 'graph_of_thought', got '%v'", response.Metadata["technique"])
	}

	if response.Metadata["num_nodes"] == nil {
		t.Error("Expected num_nodes in metadata")
	}

	if response.Metadata["num_edges"] == nil {
		t.Error("Expected num_edges in metadata")
	}

	if response.Metadata["reasoning_paths"] == nil {
		t.Error("Expected reasoning_paths in metadata")
	}

	// Check that graph is in metadata
	if response.Metadata["graph"] == nil {
		t.Error("Expected graph in metadata")
	}
}

// TestProcessWithCycleDetection tests cycle detection in Process.
func TestProcessWithCycleDetection(t *testing.T) {
	baseAgent := &mockGraphAgent{
		responses: map[string]string{
			"Premises": "1. Start point",
			"New thoughts": "- Step 1",
			"relationship": "SUPPORT",
			"Final conclusion": "End point",
		},
	}

	got := NewGraphOfThought(baseAgent, WithAllowCycles(false), WithMaxNodes(4), WithMaxEdges(4))
	ctx := context.Background()

	message := &agenkit.Message{
		Role:     "user",
		Content:  "Test problem",
		Metadata: make(map[string]interface{}),
	}

	response, err := got.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify cycle checking was done (metadata should indicate has_cycles status)
	if response.Metadata["has_cycles"] == nil {
		t.Error("Expected has_cycles in metadata")
	}
}

// TestAggregatePathsEmpty tests aggregating with no paths.
func TestAggregatePathsEmpty(t *testing.T) {
	graph := NewReasoningGraph()
	_ = graph.AddNode("Fallback conclusion", NodeTypeConclusion, 0.8, nil)

	baseAgent := &mockGraphAgent{responses: make(map[string]string)}
	got := NewGraphOfThought(baseAgent)

	// Test with empty paths
	result := got.AggregatePaths(graph, [][]int{})

	if result != "Fallback conclusion" {
		t.Errorf("Expected fallback to conclusion node, got '%s'", result)
	}

	// Test with empty graph
	emptyGraph := NewReasoningGraph()
	emptyGraph.AddNode("Only node", NodeTypeIntermediate, 0.7, nil)
	result = got.AggregatePaths(emptyGraph, [][]int{})

	if result != "Only node" {
		t.Errorf("Expected fallback to any node, got '%s'", result)
	}
}
