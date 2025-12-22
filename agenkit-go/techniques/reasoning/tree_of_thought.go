// Package reasoning provides reasoning techniques for AI agents.
package reasoning

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"sync"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// SearchStrategy defines the tree search strategy.
type SearchStrategy string

const (
	// SearchStrategyBFS performs breadth-first search.
	SearchStrategyBFS SearchStrategy = "bfs"
	// SearchStrategyDFS performs depth-first search.
	SearchStrategyDFS SearchStrategy = "dfs"
	// SearchStrategyBestFirst always expands the highest-scoring node.
	SearchStrategyBestFirst SearchStrategy = "best-first"
)

// EvaluatorFunc is a function that scores a reasoning path (0.0-1.0).
type EvaluatorFunc func(text string) float64

// TreeOfThought implements the Tree-of-Thought reasoning technique.
//
// It explores multiple reasoning paths in a tree structure, evaluates each path,
// and selects the best solution using configurable search strategies.
//
// Reference: "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
// Yao et al., 2023 - https://arxiv.org/abs/2305.10601
//
// Example:
//
//	tot := reasoning.NewTreeOfThought(
//	    baseAgent,
//	    reasoning.WithBranchingFactor(3),
//	    reasoning.WithMaxDepth(4),
//	    reasoning.WithStrategy(reasoning.SearchStrategyBestFirst),
//	)
//	response, err := tot.Process(ctx, message)
type TreeOfThought struct {
	agent           agenkit.Agent
	branchingFactor int
	maxDepth        int
	evaluator       EvaluatorFunc
	strategy        SearchStrategy
	pruneThreshold  float64
}

// TreeOfThoughtOption is a functional option for configuring TreeOfThought.
type TreeOfThoughtOption func(*TreeOfThought)

// WithBranchingFactor sets the number of alternative reasoning paths to explore at each step.
func WithBranchingFactor(n int) TreeOfThoughtOption {
	return func(tot *TreeOfThought) {
		tot.branchingFactor = n
	}
}

// WithMaxDepth sets the maximum depth of the reasoning tree.
func WithMaxDepth(depth int) TreeOfThoughtOption {
	return func(tot *TreeOfThought) {
		tot.maxDepth = depth
	}
}

// WithEvaluator sets a custom evaluator function for scoring reasoning paths.
func WithEvaluator(eval EvaluatorFunc) TreeOfThoughtOption {
	return func(tot *TreeOfThought) {
		tot.evaluator = eval
	}
}

// WithStrategy sets the search strategy (bfs, dfs, best-first).
func WithStrategy(strategy SearchStrategy) TreeOfThoughtOption {
	return func(tot *TreeOfThought) {
		tot.strategy = strategy
	}
}

// WithPruneThreshold sets the threshold for pruning low-scoring paths (0.0-1.0).
func WithPruneThreshold(threshold float64) TreeOfThoughtOption {
	return func(tot *TreeOfThought) {
		tot.pruneThreshold = threshold
	}
}

// NewTreeOfThought creates a new TreeOfThought agent.
//
// The agent explores multiple reasoning paths using tree search with branching,
// evaluation, and backtracking.
//
// Example:
//
//	tot := reasoning.NewTreeOfThought(
//	    baseAgent,
//	    reasoning.WithBranchingFactor(3),
//	    reasoning.WithMaxDepth(4),
//	    reasoning.WithStrategy(reasoning.SearchStrategyBestFirst),
//	)
func NewTreeOfThought(agent agenkit.Agent, options ...TreeOfThoughtOption) *TreeOfThought {
	tot := &TreeOfThought{
		agent:           agent,
		branchingFactor: 3,
		maxDepth:        5,
		evaluator:       defaultEvaluator,
		strategy:        SearchStrategyBestFirst,
		pruneThreshold:  0.3,
	}

	for _, option := range options {
		option(tot)
	}

	return tot
}

// Name returns the agent name.
func (tot *TreeOfThought) Name() string {
	return "tree_of_thought"
}

// Capabilities returns the agent capabilities.
func (tot *TreeOfThought) Capabilities() []string {
	return []string{
		"reasoning",
		"tree_search",
		"multi_path_exploration",
		"backtracking",
		"tree_of_thought",
		"planning",
	}
}

// defaultEvaluator is the default scoring function for reasoning paths.
//
// It scores based on text length (more detailed = better) with a cap to avoid
// favoring extremely verbose reasoning. It also gives a bonus for structured reasoning.
func defaultEvaluator(text string) float64 {
	// Penalize very short responses
	if len(text) < 50 {
		return 0.2
	}

	// Favor moderate length (100-500 chars optimal)
	lengthScore := float64(len(text)) / 500.0
	if lengthScore > 1.0 {
		lengthScore = 1.0
	}

	// Bonus for structured reasoning (numbered steps)
	structureBonus := 0.0
	if strings.Contains(text, "1.") || strings.Contains(text, "2.") ||
		strings.Contains(text, "-") || strings.Contains(text, "•") {
		structureBonus = 0.1
	}

	score := lengthScore + structureBonus
	if score > 1.0 {
		score = 1.0
	}
	return score
}

// generateBranches generates N alternative reasoning branches in parallel.
func (tot *TreeOfThought) generateBranches(ctx context.Context, prompt string, n int) ([]string, error) {
	results := make(chan string, n)
	errors := make(chan error, n)
	var wg sync.WaitGroup

	// Generate N branches in parallel using goroutines
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()

			// Add variation to prompt to encourage diversity
			variedPrompt := fmt.Sprintf("%s\n\nAlternative approach #%d:", prompt, idx+1)

			msg := &agenkit.Message{
				Role:     "user",
				Content:  variedPrompt,
				Metadata: make(map[string]interface{}),
			}

			response, err := tot.agent.Process(ctx, msg)
			if err != nil {
				errors <- err
				return
			}

			results <- response.Content
		}(i)
	}

	// Wait for all goroutines to complete
	wg.Wait()
	close(results)
	close(errors)

	// Check for errors
	if len(errors) > 0 {
		return nil, fmt.Errorf("branch generation failed: %w", <-errors)
	}

	// Collect results
	branches := make([]string, 0, n)
	for branch := range results {
		branches = append(branches, branch)
	}

	return branches, nil
}

// expandNode expands a node by generating child branches.
func (tot *TreeOfThought) expandNode(ctx context.Context, tree *ReasoningTree, nodeID int, query string) ([]int, error) {
	node := tree.GetNode(nodeID)
	if node == nil {
		return nil, nil
	}

	// Build prompt with path so far
	pathText := tree.GetPathText(nodeID, "\n")
	prompt := fmt.Sprintf("Original question: %s\n\nReasoning so far:\n%s\n\nContinue reasoning:", query, pathText)

	// Generate branches
	branches, err := tot.generateBranches(ctx, prompt, tot.branchingFactor)
	if err != nil {
		return nil, fmt.Errorf("failed to generate branches: %w", err)
	}

	// Add branches as children
	childIDs := []int{}
	for _, branchText := range branches {
		// Score the branch
		fullPath := pathText + "\n" + branchText
		score := tot.evaluator(fullPath)

		// Add child node
		childID, err := tree.AddChild(nodeID, branchText, score, nil)
		if err != nil {
			return nil, fmt.Errorf("failed to add child: %w", err)
		}

		// Prune if score too low
		if score < tot.pruneThreshold {
			tree.PruneNode(childID)
		} else {
			childIDs = append(childIDs, childID)
		}
	}

	// Mark node as evaluated
	node.State = NodeStateEvaluated

	return childIDs, nil
}

// searchBFS performs breadth-first search through the reasoning tree.
func (tot *TreeOfThought) searchBFS(ctx context.Context, tree *ReasoningTree, rootID int, query string) error {
	queue := []int{rootID}

	for len(queue) > 0 {
		// Dequeue
		nodeID := queue[0]
		queue = queue[1:]

		node := tree.GetNode(nodeID)
		if node == nil || node.State == NodeStatePruned {
			continue
		}

		// Stop if max depth reached
		if node.Depth >= tot.maxDepth {
			node.State = NodeStateTerminal
			continue
		}

		// Expand node
		childIDs, err := tot.expandNode(ctx, tree, nodeID, query)
		if err != nil {
			return fmt.Errorf("bfs expansion failed: %w", err)
		}

		// Enqueue children
		queue = append(queue, childIDs...)
	}

	return nil
}

// searchDFS performs depth-first search through the reasoning tree.
func (tot *TreeOfThought) searchDFS(ctx context.Context, tree *ReasoningTree, rootID int, query string) error {
	stack := []int{rootID}

	for len(stack) > 0 {
		// Pop
		nodeID := stack[len(stack)-1]
		stack = stack[:len(stack)-1]

		node := tree.GetNode(nodeID)
		if node == nil || node.State == NodeStatePruned {
			continue
		}

		// Stop if max depth reached
		if node.Depth >= tot.maxDepth {
			node.State = NodeStateTerminal
			continue
		}

		// Expand node
		childIDs, err := tot.expandNode(ctx, tree, nodeID, query)
		if err != nil {
			return fmt.Errorf("dfs expansion failed: %w", err)
		}

		// Push children in reverse order to maintain left-to-right traversal
		for i := len(childIDs) - 1; i >= 0; i-- {
			stack = append(stack, childIDs[i])
		}
	}

	return nil
}

// searchBestFirst performs best-first search - always expand highest scoring node.
func (tot *TreeOfThought) searchBestFirst(ctx context.Context, tree *ReasoningTree, rootID int, query string) error {
	openNodes := []int{rootID}

	for len(openNodes) > 0 {
		// Sort by score (highest first)
		sort.Slice(openNodes, func(i, j int) bool {
			nodeI := tree.GetNode(openNodes[i])
			nodeJ := tree.GetNode(openNodes[j])
			if nodeI == nil {
				return false
			}
			if nodeJ == nil {
				return true
			}
			return nodeI.Score > nodeJ.Score
		})

		// Pop highest scoring node
		nodeID := openNodes[0]
		openNodes = openNodes[1:]

		node := tree.GetNode(nodeID)
		if node == nil || node.State == NodeStatePruned {
			continue
		}

		// Stop if max depth reached
		if node.Depth >= tot.maxDepth {
			node.State = NodeStateTerminal
			continue
		}

		// Expand node
		childIDs, err := tot.expandNode(ctx, tree, nodeID, query)
		if err != nil {
			return fmt.Errorf("best-first expansion failed: %w", err)
		}

		// Add children to open list
		openNodes = append(openNodes, childIDs...)
	}

	return nil
}

// Process processes a message with Tree-of-Thought reasoning.
//
// It builds a reasoning tree, explores multiple paths using the configured
// search strategy, and returns the best complete reasoning path.
//
// The response metadata includes:
//   - technique: "tree_of_thought"
//   - search_strategy: string
//   - reasoning_tree_stats: TreeStatistics
//   - reasoning_path: []string
//   - num_steps: int
//   - best_score: float64
func (tot *TreeOfThought) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	query := message.Content

	// Create reasoning tree
	tree := NewReasoningTree()
	rootID := tree.CreateRoot(query, nil)

	// Run search strategy
	var err error
	switch tot.strategy {
	case SearchStrategyBFS:
		err = tot.searchBFS(ctx, tree, rootID, query)
	case SearchStrategyDFS:
		err = tot.searchDFS(ctx, tree, rootID, query)
	case SearchStrategyBestFirst:
		err = tot.searchBestFirst(ctx, tree, rootID, query)
	default:
		return nil, fmt.Errorf("invalid strategy: %s", tot.strategy)
	}

	if err != nil {
		return nil, fmt.Errorf("tree search failed: %w", err)
	}

	// Get best leaf node
	bestLeaf := tree.GetBestLeaf()

	if bestLeaf == nil {
		// No valid path found
		stats := tree.GetStatistics()
		return &agenkit.Message{
			Role:    "assistant",
			Content: "Unable to find valid reasoning path.",
			Metadata: map[string]interface{}{
				"technique":            "tree_of_thought",
				"search_strategy":      string(tot.strategy),
				"reasoning_tree_stats": stats,
				"error":                "no_valid_path",
			},
		}, nil
	}

	// Get best path
	bestPath := tree.GetPath(bestLeaf.ID)
	pathText := tree.GetPathText(bestLeaf.ID, "\n")

	// Build reasoning path as string slice
	reasoningPath := make([]string, len(bestPath))
	for i, node := range bestPath {
		reasoningPath[i] = node.Content
	}

	stats := tree.GetStatistics()

	return &agenkit.Message{
		Role:    "assistant",
		Content: pathText,
		Metadata: map[string]interface{}{
			"technique":            "tree_of_thought",
			"search_strategy":      string(tot.strategy),
			"reasoning_tree_stats": stats,
			"reasoning_path":       reasoningPath,
			"num_steps":            len(bestPath),
			"best_score":           bestLeaf.Score,
		},
	}, nil
}
