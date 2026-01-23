// Package main demonstrates the Graph-of-Thought reasoning technique.
//
// Graph-of-Thought (GoT) represents reasoning as a directed graph where nodes are
// thoughts/conclusions and edges represent logical connections. More flexible than
// tree-based approaches, it allows for complex multi-hop reasoning and thought combination.
//
// This example shows:
//   - Building a reasoning graph with premises, intermediate thoughts, and conclusions
//   - Identifying logical connections (supports, depends_on, contradicts, refines)
//   - Finding reasoning paths from premises to conclusions
//   - Aggregating multiple paths to reach final answer
//   - Cycle detection in reasoning
//   - Path-based vs node-based aggregation strategies
//
// Use GraphOfThought for:
//   - Multi-hop reasoning problems
//   - Problems with multiple interconnected concepts
//   - Situations requiring synthesis of multiple reasoning chains
//   - Complex knowledge integration tasks
//
// Reference: "Graph of Thoughts: Solving Elaborate Problems with Large Language Models"
// https://arxiv.org/abs/2308.09687
//
// Run with: go run main.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"
)

// MockGraphLLM simulates an LLM that generates reasoning graphs.
type MockGraphLLM struct {
	step int
}

func NewMockGraphLLM() *MockGraphLLM {
	return &MockGraphLLM{step: 0}
}

func (m *MockGraphLLM) Name() string {
	return "mock-graph-llm"
}

func (m *MockGraphLLM) Capabilities() []string {
	return []string{"reasoning", "graph_of_thought"}
}

func (m *MockGraphLLM) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MockGraphLLM) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content
	m.step++

	// Simulate LLM responses based on prompt patterns
	if strings.Contains(content, "Premises:") {
		return agenkit.NewMessage("assistant", `1. Machine learning requires data
2. Algorithms learn patterns from data
3. More data generally leads to better learning`), nil
	}

	if strings.Contains(content, "New thoughts") {
		switch m.step % 3 {
		case 0:
			return agenkit.NewMessage("assistant", `- Quality of data is crucial
- Algorithms must be appropriate for the problem
- Training requires computational resources`), nil
		case 1:
			return agenkit.NewMessage("assistant", `- Overfitting can occur with too much complexity
- Validation data helps assess performance
- Feature engineering improves results`), nil
		default:
			return agenkit.NewMessage("assistant", `- Model selection impacts accuracy
- Hyperparameter tuning is essential
- Deployment requires infrastructure`), nil
		}
	}

	if strings.Contains(content, "relationship") {
		// Simulate identifying connections between thoughts
		if strings.Contains(content, "data") && strings.Contains(content, "quality") {
			return agenkit.NewMessage("assistant", "REFINE"), nil
		} else if strings.Contains(content, "data") && strings.Contains(content, "Algorithm") {
			return agenkit.NewMessage("assistant", "DEPEND"), nil
		} else if strings.Contains(content, "learn") && strings.Contains(content, "pattern") {
			return agenkit.NewMessage("assistant", "SUPPORT"), nil
		}
		return agenkit.NewMessage("assistant", "NO_RELATION"), nil
	}

	if strings.Contains(content, "Final conclusion") {
		return agenkit.NewMessage("assistant", `Machine learning is a data-driven process that requires:
1. High-quality data
2. Appropriate algorithms
3. Sufficient computational resources
4. Careful validation and tuning
Success depends on the interplay of these factors.`), nil
	}

	return agenkit.NewMessage("assistant", "Default response"), nil
}

func main() {
	fmt.Println("=== Graph-of-Thought Reasoning Example ===\n")

	ctx := context.Background()

	// Create base LLM agent
	llm := NewMockGraphLLM()

	// ====================================================================
	// Example 1: Basic Graph-of-Thought with Path-Based Aggregation
	// ====================================================================
	fmt.Println("1. Basic Graph-of-Thought (Path-Based Aggregation)\n")

	got := reasoning.NewGraphOfThought(
		llm,
		reasoning.WithMaxNodes(12),
		reasoning.WithMaxEdges(20),
		reasoning.WithAggregator(reasoning.AggregatorPathBased),
	)

	message := agenkit.NewMessage("user", "How does machine learning work?")

	response, err := got.Process(ctx, message)
	if err != nil {
		log.Fatalf("Graph-of-Thought failed: %v", err)
	}

	fmt.Printf("Question: %s\n\n", message.Content)
	fmt.Printf("Answer:\n%s\n\n", response.Content)

	// Display graph statistics
	fmt.Println("Graph Statistics:")
	fmt.Printf("  - Nodes: %d\n", response.Metadata["num_nodes"])
	fmt.Printf("  - Edges: %d\n", response.Metadata["num_edges"])
	fmt.Printf("  - Has Cycles: %v\n", response.Metadata["has_cycles"])
	fmt.Printf("  - Node Types: %v\n", response.Metadata["node_types"])
	fmt.Printf("  - Edge Types: %v\n", response.Metadata["edge_types"])
	fmt.Printf("  - Aggregator: %s\n", response.Metadata["aggregator"])

	// Display reasoning paths
	if paths, ok := response.Metadata["reasoning_paths"].([][]int); ok {
		fmt.Printf("\n  Reasoning Paths Found: %d\n", len(paths))
		for i, path := range paths {
			fmt.Printf("    Path %d: %d nodes\n", i+1, len(path))
		}
	}

	fmt.Println()

	// ====================================================================
	// Example 2: Node-Based Aggregation
	// ====================================================================
	fmt.Println("2. Graph-of-Thought with Node-Based Aggregation\n")

	llm2 := NewMockGraphLLM()
	got2 := reasoning.NewGraphOfThought(
		llm2,
		reasoning.WithMaxNodes(10),
		reasoning.WithMaxEdges(15),
		reasoning.WithAggregator(reasoning.AggregatorNodeBased),
	)

	message2 := agenkit.NewMessage("user", "What are the key factors in machine learning?")
	response2, err := got2.Process(ctx, message2)
	if err != nil {
		log.Fatalf("Graph-of-Thought failed: %v", err)
	}

	fmt.Printf("Question: %s\n\n", message2.Content)
	fmt.Printf("Answer (Node-Based):\n%s\n\n", response2.Content)
	fmt.Printf("Aggregation Strategy: %s\n", response2.Metadata["aggregator"])
	fmt.Printf("Nodes: %d, Edges: %d\n\n", response2.Metadata["num_nodes"], response2.Metadata["num_edges"])

	// ====================================================================
	// Example 3: Allowing Cycles in Reasoning
	// ====================================================================
	fmt.Println("3. Graph-of-Thought with Cycles Allowed\n")

	llm3 := NewMockGraphLLM()
	got3 := reasoning.NewGraphOfThought(
		llm3,
		reasoning.WithMaxNodes(8),
		reasoning.WithMaxEdges(12),
		reasoning.WithAllowCycles(true),
	)

	message3 := agenkit.NewMessage("user", "Explain the relationship between data and algorithms")
	response3, err := got3.Process(ctx, message3)
	if err != nil {
		log.Fatalf("Graph-of-Thought failed: %v", err)
	}

	fmt.Printf("Question: %s\n\n", message3.Content)
	fmt.Printf("Answer:\n%s\n\n", response3.Content)
	fmt.Printf("Cycles Allowed: %v\n", response3.Metadata["allow_cycles"])
	fmt.Printf("Has Cycles: %v\n\n", response3.Metadata["has_cycles"])

	// ====================================================================
	// Example 4: Inspecting the Reasoning Graph
	// ====================================================================
	fmt.Println("4. Inspecting the Reasoning Graph Structure\n")

	llm4 := NewMockGraphLLM()
	got4 := reasoning.NewGraphOfThought(
		llm4,
		reasoning.WithMaxNodes(6),
		reasoning.WithMaxEdges(8),
	)

	message4 := agenkit.NewMessage("user", "Simple ML question")
	response4, err := got4.Process(ctx, message4)
	if err != nil {
		log.Fatalf("Graph-of-Thought failed: %v", err)
	}

	// Access the graph from metadata
	if graph, ok := response4.Metadata["graph"].(*reasoning.ReasoningGraph); ok {
		fmt.Println("Graph Structure:")

		// Show premises
		premises := graph.GetPremises()
		fmt.Printf("  Premises (%d):\n", len(premises))
		for _, premise := range premises {
			fmt.Printf("    - [%d] %s (confidence: %.2f)\n",
				premise.ID, premise.Content, premise.Confidence)
		}

		// Show conclusions
		conclusions := graph.GetConclusions()
		fmt.Printf("\n  Conclusions (%d):\n", len(conclusions))
		for _, conclusion := range conclusions {
			fmt.Printf("    - [%d] %s (confidence: %.2f)\n",
				conclusion.ID, conclusion.Content, conclusion.Confidence)
		}

		// Show statistics
		stats := graph.Statistics()
		fmt.Printf("\n  Graph Statistics:\n")
		fmt.Printf("    - Total Nodes: %d\n", stats.NumNodes)
		fmt.Printf("    - Total Edges: %d\n", stats.NumEdges)
		fmt.Printf("    - Average Confidence: %.2f\n", stats.AvgConfidence)
		fmt.Printf("    - Has Cycles: %v\n", stats.HasCycles)
	}

	fmt.Println()

	// ====================================================================
	// Key Takeaways
	// ====================================================================
	fmt.Println("=== Key Takeaways ===\n")
	fmt.Println("Graph-of-Thought (GoT) vs Tree-of-Thought (ToT):")
	fmt.Println("  ✓ GoT allows arbitrary graph structures (not just trees)")
	fmt.Println("  ✓ GoT supports multiple reasoning paths converging/diverging")
	fmt.Println("  ✓ GoT can represent thought refinement and contradictions")
	fmt.Println("  ✓ GoT enables complex multi-hop reasoning")
	fmt.Println()
	fmt.Println("Use Graph-of-Thought when:")
	fmt.Println("  • Problem requires synthesizing multiple reasoning chains")
	fmt.Println("  • Thoughts may support, contradict, or refine each other")
	fmt.Println("  • Need to model complex dependencies between concepts")
	fmt.Println("  • Multiple valid reasoning paths exist")
	fmt.Println()
	fmt.Println("Configuration Options:")
	fmt.Println("  • MaxNodes: Control graph size (default: 20)")
	fmt.Println("  • MaxEdges: Limit connections (default: 40)")
	fmt.Println("  • Aggregator: path_based or node_based (default: path_based)")
	fmt.Println("  • AllowCycles: Enable circular reasoning (default: false)")
	fmt.Println()
	fmt.Println("Aggregation Strategies:")
	fmt.Println("  • Path-Based: Select best complete reasoning path (score by path)")
	fmt.Println("  • Node-Based: Weight nodes by appearance frequency (score by node)")
}
