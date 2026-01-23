// Package reasoning provides reasoning techniques for AI agents.
package reasoning

import (
	"context"
	"fmt"
	"regexp"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// AggregatorType defines the aggregation strategy for combining reasoning paths.
type AggregatorType string

const (
	// AggregatorPathBased aggregates entire reasoning paths.
	AggregatorPathBased AggregatorType = "path_based"
	// AggregatorNodeBased aggregates individual nodes.
	AggregatorNodeBased AggregatorType = "node_based"
)

// GraphOfThought implements the Graph-of-Thought reasoning technique.
//
// It builds a directed graph of reasoning steps, explores connections,
// and aggregates multiple reasoning paths to reach conclusions.
//
// This technique is particularly effective for:
// - Multi-hop reasoning with complex dependencies
// - Problems requiring synthesis of multiple chains of thought
// - Situations where thoughts may support, contradict, or refine each other
// - Complex knowledge integration tasks
//
// Reference: "Graph of Thoughts: Solving Elaborate Problems with Large Language Models"
// https://arxiv.org/abs/2308.09687
//
// Example:
//
//	got := reasoning.NewGraphOfThought(
//	    baseAgent,
//	    reasoning.WithMaxNodes(20),
//	    reasoning.WithMaxEdges(40),
//	    reasoning.WithAggregator(reasoning.AggregatorPathBased),
//	)
//	response, err := got.Process(ctx, message)
type GraphOfThought struct {
	agent       agenkit.Agent
	maxNodes    int
	maxEdges    int
	aggregator  AggregatorType
	allowCycles bool
}

// GraphOfThoughtOption is a functional option for configuring GraphOfThought.
type GraphOfThoughtOption func(*GraphOfThought)

// WithMaxNodes sets the maximum number of nodes in the reasoning graph.
func WithMaxNodes(n int) GraphOfThoughtOption {
	return func(got *GraphOfThought) {
		got.maxNodes = n
	}
}

// WithMaxEdges sets the maximum number of edges in the reasoning graph.
func WithMaxEdges(n int) GraphOfThoughtOption {
	return func(got *GraphOfThought) {
		got.maxEdges = n
	}
}

// WithAggregator sets the aggregation strategy for combining paths.
func WithAggregator(agg AggregatorType) GraphOfThoughtOption {
	return func(got *GraphOfThought) {
		got.aggregator = agg
	}
}

// WithAllowCycles sets whether to allow cycles in the reasoning graph.
func WithAllowCycles(allow bool) GraphOfThoughtOption {
	return func(got *GraphOfThought) {
		got.allowCycles = allow
	}
}

// NewGraphOfThought creates a new GraphOfThought agent.
//
// The agent builds a directed graph of reasoning, explores multiple paths,
// and aggregates them to reach conclusions.
//
// Example:
//
//	got := reasoning.NewGraphOfThought(
//	    baseAgent,
//	    reasoning.WithMaxNodes(20),
//	    reasoning.WithAggregator(reasoning.AggregatorPathBased),
//	)
func NewGraphOfThought(agent agenkit.Agent, options ...GraphOfThoughtOption) *GraphOfThought {
	got := &GraphOfThought{
		agent:       agent,
		maxNodes:    20,
		maxEdges:    40,
		aggregator:  AggregatorPathBased,
		allowCycles: false,
	}

	for _, option := range options {
		option(got)
	}

	return got
}

// Name returns the agent name.
func (got *GraphOfThought) Name() string {
	return "graph_of_thought"
}

// Capabilities returns the agent capabilities.
func (got *GraphOfThought) Capabilities() []string {
	return []string{
		"reasoning",
		"graph_of_thought",
		"multi_hop_reasoning",
		"path_aggregation",
		"complex_synthesis",
	}
}

// llmCall calls the underlying LLM with a prompt.
func (got *GraphOfThought) llmCall(ctx context.Context, prompt string) (string, error) {
	msg := &agenkit.Message{
		Role:     "user",
		Content:  prompt,
		Metadata: make(map[string]interface{}),
	}

	response, err := got.agent.Process(ctx, msg)
	if err != nil {
		return "", fmt.Errorf("llm call failed: %w", err)
	}

	return response.Content, nil
}

// GeneratePremises generates initial premises/facts for the problem.
func (got *GraphOfThought) GeneratePremises(ctx context.Context, problem string) ([]string, error) {
	prompt := fmt.Sprintf(`Identify the key facts and premises for this problem.
List 2-4 foundational facts or assumptions, one per line.

Problem: %s

Premises:`, problem)

	response, err := got.llmCall(ctx, prompt)
	if err != nil {
		return nil, err
	}

	// Parse premises
	premises := []string{}
	re := regexp.MustCompile(`^[•\-*\d]+[.)\s]*`)

	for _, line := range strings.Split(strings.TrimSpace(response), "\n") {
		line = strings.TrimSpace(line)
		if line != "" && !strings.HasPrefix(line, "#") {
			// Remove numbering and bullets
			cleaned := re.ReplaceAllString(line, "")
			if cleaned != "" && len(premises) < 4 {
				premises = append(premises, cleaned)
			}
		}
	}

	return premises, nil
}

// GenerateThoughts generates new intermediate thoughts based on existing ones.
func (got *GraphOfThought) GenerateThoughts(ctx context.Context, problem string, existingThoughts []string, maxNew int) ([]string, error) {
	var prompt string

	if len(existingThoughts) > 0 {
		context := ""
		for _, t := range existingThoughts {
			context += fmt.Sprintf("- %s\n", t)
		}

		prompt = fmt.Sprintf(`Given this problem and existing thoughts, generate %d new insights or conclusions.

Problem: %s

Existing thoughts:
%s

New thoughts (one per line):`, maxNew, problem, context)
	} else {
		prompt = fmt.Sprintf(`Generate %d initial thoughts or insights about this problem.

Problem: %s

Thoughts (one per line):`, maxNew, problem)
	}

	response, err := got.llmCall(ctx, prompt)
	if err != nil {
		return nil, err
	}

	// Parse new thoughts
	thoughts := []string{}
	re := regexp.MustCompile(`^[•\-*\d]+[.)\s]*`)

	for _, line := range strings.Split(strings.TrimSpace(response), "\n") {
		line = strings.TrimSpace(line)
		if line != "" && !strings.HasPrefix(line, "#") {
			cleaned := re.ReplaceAllString(line, "")
			if cleaned != "" && len(thoughts) < maxNew {
				thoughts = append(thoughts, cleaned)
			}
		}
	}

	return thoughts, nil
}

// IdentifyConnections identifies the logical connection between two thoughts.
func (got *GraphOfThought) IdentifyConnections(ctx context.Context, thought1, thought2 string) (EdgeType, error) {
	prompt := fmt.Sprintf(`Analyze the logical relationship between these two statements.

Statement 1: %s

Statement 2: %s

Does statement 2:
- SUPPORT statement 1 (provides evidence or reasoning for it)
- DEPEND on statement 1 (requires it to be true)
- CONTRADICT statement 1 (conflicts with it)
- REFINE statement 1 (improves or clarifies it)
- NO_RELATION (no clear logical connection)

Answer with one word: SUPPORT, DEPEND, CONTRADICT, REFINE, or NO_RELATION`, thought1, thought2)

	response, err := got.llmCall(ctx, prompt)
	if err != nil {
		return "", err
	}

	responseUpper := strings.ToUpper(strings.TrimSpace(response))

	if strings.Contains(responseUpper, "SUPPORT") {
		return EdgeTypeSupports, nil
	} else if strings.Contains(responseUpper, "DEPEND") {
		return EdgeTypeDependsOn, nil
	} else if strings.Contains(responseUpper, "CONTRADICT") {
		return EdgeTypeContradicts, nil
	} else if strings.Contains(responseUpper, "REFINE") {
		return EdgeTypeRefines, nil
	}

	// No relation found
	return "", fmt.Errorf("no relation identified")
}

// BuildGraph builds the reasoning graph for the problem.
func (got *GraphOfThought) BuildGraph(ctx context.Context, problem string) (*ReasoningGraph, error) {
	graph := NewReasoningGraph()

	// Step 1: Generate premises
	premises, err := got.GeneratePremises(ctx, problem)
	if err != nil {
		return nil, fmt.Errorf("failed to generate premises: %w", err)
	}

	premiseIDs := []int{}
	for _, premise := range premises {
		nodeID := graph.AddNode(premise, NodeTypePremise, 0.9, nil)
		premiseIDs = append(premiseIDs, nodeID)
	}

	// Step 2: Generate intermediate thoughts
	allThoughts := make([]string, len(premises))
	copy(allThoughts, premises)
	nodeIDs := make([]int, len(premiseIDs))
	copy(nodeIDs, premiseIDs)

	for len(graph.nodes) < got.maxNodes {
		// Generate new thoughts based on existing ones
		maxNew := got.maxNodes - len(graph.nodes)
		if maxNew > 3 {
			maxNew = 3
		}
		if maxNew <= 0 {
			break
		}

		newThoughts, err := got.GenerateThoughts(ctx, problem, allThoughts, maxNew)
		if err != nil {
			return nil, fmt.Errorf("failed to generate thoughts: %w", err)
		}

		if len(newThoughts) == 0 {
			break
		}

		// Add new thoughts as intermediate nodes
		for _, thought := range newThoughts {
			if len(graph.nodes) >= got.maxNodes {
				break
			}

			nodeID := graph.AddNode(thought, NodeTypeIntermediate, 0.7, nil)
			allThoughts = append(allThoughts, thought)
			nodeIDs = append(nodeIDs, nodeID)
		}
	}

	// Step 3: Identify connections between thoughts
	edgeCount := 0
	for i := 0; i < len(nodeIDs) && edgeCount < got.maxEdges; i++ {
		for j := i + 1; j < len(nodeIDs) && edgeCount < got.maxEdges; j++ {
			node1ID := nodeIDs[i]
			node2ID := nodeIDs[j]

			node1 := graph.GetNode(node1ID)
			node2 := graph.GetNode(node2ID)

			// Check connection from node1 to node2
			edgeType, err := got.IdentifyConnections(ctx, node1.Content, node2.Content)
			if err == nil {
				if err := graph.AddEdge(node1ID, node2ID, edgeType, 0.8, nil); err == nil {
					edgeCount++
				}
			}
		}
	}

	// Step 4: Generate final conclusion
	if len(graph.nodes) < got.maxNodes {
		thoughtsText := ""
		for _, t := range allThoughts {
			thoughtsText += fmt.Sprintf("- %s\n", t)
		}

		conclusionPrompt := fmt.Sprintf(`Based on all these thoughts, what is the final conclusion?

Problem: %s

Thoughts:
%s

Final conclusion:`, problem, thoughtsText)

		conclusion, err := got.llmCall(ctx, conclusionPrompt)
		if err == nil {
			conclusionID := graph.AddNode(strings.TrimSpace(conclusion), NodeTypeConclusion, 0.8, nil)

			// Connect conclusion to recent thoughts
			recentStart := len(nodeIDs) - 3
			if recentStart < 0 {
				recentStart = 0
			}
			for k := recentStart; k < len(nodeIDs) && edgeCount < got.maxEdges; k++ {
				if err := graph.AddEdge(nodeIDs[k], conclusionID, EdgeTypeSupports, 0.9, nil); err == nil {
					edgeCount++
				}
			}
		}
	}

	return graph, nil
}

// FindReasoningPaths finds reasoning paths from premises to conclusions.
func (got *GraphOfThought) FindReasoningPaths(graph *ReasoningGraph) [][]int {
	premises := graph.GetPremises()
	conclusions := graph.GetConclusions()

	allPaths := [][]int{}
	for _, premise := range premises {
		for _, conclusion := range conclusions {
			paths := graph.FindPaths(premise.ID, conclusion.ID, 6)
			allPaths = append(allPaths, paths...)
		}
	}

	return allPaths
}

// AggregatePaths aggregates multiple reasoning paths into a final answer.
func (got *GraphOfThought) AggregatePaths(graph *ReasoningGraph, paths [][]int) string {
	if len(paths) == 0 {
		// No paths found - use conclusion nodes directly
		conclusions := graph.GetConclusions()
		if len(conclusions) > 0 {
			return conclusions[0].Content
		}
		// Fallback to any node
		for _, node := range graph.nodes {
			return node.Content
		}
		return "Unable to reach conclusion"
	}

	if got.aggregator == AggregatorPathBased {
		// Aggregate by considering complete paths
		// Find highest scoring path
		bestPath := paths[0]
		bestScore := graph.GetPathScore(bestPath)

		for _, path := range paths[1:] {
			score := graph.GetPathScore(path)
			if score > bestScore {
				bestScore = score
				bestPath = path
			}
		}

		// Get conclusion from best path
		conclusionNode := graph.GetNode(bestPath[len(bestPath)-1])
		return conclusionNode.Content

	} else if got.aggregator == AggregatorNodeBased {
		// Aggregate by considering individual nodes
		// Count node appearances across paths
		nodeCounts := make(map[int]int)
		for _, path := range paths {
			for _, nodeID := range path {
				nodeCounts[nodeID]++
			}
		}

		// Weight by confidence
		nodeScores := make(map[int]float64)
		for nodeID, count := range nodeCounts {
			node := graph.GetNode(nodeID)
			nodeScores[nodeID] = float64(count) * node.Confidence
		}

		// Return highest scoring node's content
		bestNodeID := -1
		bestScore := 0.0
		for nodeID, score := range nodeScores {
			if score > bestScore {
				bestScore = score
				bestNodeID = nodeID
			}
		}

		if bestNodeID >= 0 {
			return graph.GetNode(bestNodeID).Content
		}
		return "Unable to reach conclusion"
	}

	return "Invalid aggregator type"
}

// Process processes a message with Graph-of-Thought reasoning.
//
// Builds a reasoning graph, finds paths, and aggregates them into a final answer.
//
// The response metadata includes:
//   - technique: "graph_of_thought"
//   - graph: The reasoning graph (pointer)
//   - reasoning_paths: List of reasoning paths
//   - num_nodes: Number of nodes in graph
//   - num_edges: Number of edges in graph
//   - has_cycles: Whether graph contains cycles
//   - aggregator: Aggregation strategy used
//
// Example:
//
//	response, err := got.Process(ctx, message)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	fmt.Printf("Nodes: %v\n", response.Metadata["num_nodes"])
func (got *GraphOfThought) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	problem := message.Content

	// Step 1: Build reasoning graph
	graph, err := got.BuildGraph(ctx, problem)
	if err != nil {
		return nil, fmt.Errorf("failed to build graph: %w", err)
	}

	// Step 2: Check for cycles (if not allowed)
	if !got.allowCycles && graph.HasCycle() {
		// Note: Could implement cycle removal here
		// For now, we just note it in metadata
	}

	// Step 3: Find reasoning paths
	reasoningPaths := got.FindReasoningPaths(graph)

	// Step 4: Aggregate paths to final answer
	finalAnswer := got.AggregatePaths(graph, reasoningPaths)

	// Get statistics
	stats := graph.Statistics()

	return &agenkit.Message{
		Role:    "assistant",
		Content: finalAnswer,
		Metadata: map[string]interface{}{
			"technique":       "graph_of_thought",
			"graph":           graph,
			"reasoning_paths": reasoningPaths,
			"num_nodes":       stats.NumNodes,
			"num_edges":       stats.NumEdges,
			"has_cycles":      stats.HasCycles,
			"node_types":      stats.NodeTypes,
			"edge_types":      stats.EdgeTypes,
			"aggregator":      string(got.aggregator),
			"allow_cycles":    got.allowCycles,
		},
	}, nil
}
