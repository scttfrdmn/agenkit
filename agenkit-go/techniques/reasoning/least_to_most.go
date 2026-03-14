// Package reasoning provides reasoning techniques like Chain-of-Thought, Self-Consistency, etc.
package reasoning

import (
	"context"
	"fmt"
	"regexp"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Subproblem represents a subproblem in the decomposition.
type Subproblem struct {
	Content      string
	Difficulty   int
	Dependencies []int
}

// DecomposerFunc is a function that decomposes a problem into subproblems.
type DecomposerFunc func(problem string) ([]string, error)

// LeastToMost implements the Least-to-Most reasoning technique.
//
// It breaks complex problems into simpler subproblems, solves them sequentially
// from simplest to most complex, using solutions to build up to the final answer.
//
// This technique is particularly effective for compositional reasoning where
// complex problems can be decomposed into manageable pieces.
//
// Reference: "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models"
// Zhou et al., 2022 - https://arxiv.org/abs/2205.10625
//
// Example:
//
//	ltm := reasoning.NewLeastToMost(
//	    baseAgent,
//	    reasoning.WithLTMMaxSubproblems(5),
//	    reasoning.WithComposeSolutions(true),
//	)
//	response, err := ltm.Process(ctx, message)
type LeastToMost struct {
	agent            agenkit.Agent
	decomposer       DecomposerFunc
	maxSubproblems   int
	composeSolutions bool
}

// LeastToMostOption is a functional option for configuring LeastToMost.
type LeastToMostOption func(*LeastToMost)

// WithLTMDecomposer sets a custom decomposer function.
func WithLTMDecomposer(decomposer DecomposerFunc) LeastToMostOption {
	return func(ltm *LeastToMost) {
		ltm.decomposer = decomposer
	}
}

// WithLTMMaxSubproblems sets the maximum number of subproblems.
func WithLTMMaxSubproblems(max int) LeastToMostOption {
	return func(ltm *LeastToMost) {
		ltm.maxSubproblems = max
	}
}

// WithComposeSolutions sets whether to use previous solutions as context.
func WithComposeSolutions(compose bool) LeastToMostOption {
	return func(ltm *LeastToMost) {
		ltm.composeSolutions = compose
	}
}

// NewLeastToMost creates a new LeastToMost agent.
//
// The agent wraps a base agent and applies least-to-most prompting to
// break down complex problems into simpler subproblems, solve them sequentially,
// and compose the final solution.
//
// Example:
//
//	ltm := reasoning.NewLeastToMost(
//	    baseAgent,
//	    reasoning.WithLTMMaxSubproblems(5),
//	    reasoning.WithComposeSolutions(true),
//	)
func NewLeastToMost(agent agenkit.Agent, options ...LeastToMostOption) *LeastToMost {
	ltm := &LeastToMost{
		agent:            agent,
		decomposer:       nil,
		maxSubproblems:   5,
		composeSolutions: true,
	}

	for _, option := range options {
		option(ltm)
	}

	return ltm
}

// Name returns the agent name.
func (ltm *LeastToMost) Name() string {
	return "least_to_most"
}

// Capabilities returns the agent capabilities.
func (ltm *LeastToMost) Capabilities() []string {
	return []string{
		"reasoning",
		"decomposition",
		"compositional_reasoning",
		"least_to_most",
		"sequential_solving",
	}
}

// decompose breaks down a problem into subproblems.
//
// Uses custom decomposer if provided, otherwise uses LLM.
func (ltm *LeastToMost) decompose(ctx context.Context, problem string) ([]Subproblem, error) {
	if ltm.decomposer != nil {
		// Use custom decomposer
		subproblemTexts, err := ltm.decomposer(problem)
		if err != nil {
			return nil, fmt.Errorf("custom decomposer failed: %w", err)
		}

		subproblems := make([]Subproblem, 0, len(subproblemTexts))
		for i, text := range subproblemTexts {
			if i >= ltm.maxSubproblems {
				break
			}
			subproblems = append(subproblems, Subproblem{
				Content:      text,
				Difficulty:   i,
				Dependencies: []int{},
			})
		}
		return subproblems, nil
	}

	// Use LLM to decompose
	decompositionPrompt := fmt.Sprintf(`Break down this problem into simpler subproblems, ordered from easiest to hardest.
List each subproblem on a separate line, numbered 1, 2, 3, etc.

Problem: %s

Subproblems (from simplest to most complex):`, problem)

	promptMessage := &agenkit.Message{
		Role:     "user",
		Content:  decompositionPrompt,
		Metadata: make(map[string]interface{}),
	}

	response, err := ltm.agent.Process(ctx, promptMessage)
	if err != nil {
		return nil, fmt.Errorf("decomposition failed: %w", err)
	}

	// Parse subproblems from response
	subproblems := ltm.parseSubproblems(response.ContentString(), problem)

	return subproblems, nil
}

// parseSubproblems parses subproblems from LLM response.
func (ltm *LeastToMost) parseSubproblems(responseText, originalProblem string) []Subproblem {
	subproblems := []Subproblem{}
	lines := strings.Split(strings.TrimSpace(responseText), "\n")

	// Regex to match numbered lines (1., 1), etc.)
	numberedRegex := regexp.MustCompile(`^\d+[.)]`)

	for i, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		// Only match lines that START with a number followed by . or )
		if !numberedRegex.MatchString(line) {
			continue
		}

		// Remove numbering
		cleaned := regexp.MustCompile(`^\d+[.)]\s*`).ReplaceAllString(line, "")

		if cleaned != "" && len(subproblems) < ltm.maxSubproblems {
			subproblems = append(subproblems, Subproblem{
				Content:      cleaned,
				Difficulty:   i,
				Dependencies: []int{},
			})
		}
	}

	// If decomposition failed or no valid numbered steps found, treat as atomic problem
	if len(subproblems) == 0 {
		subproblems = append(subproblems, Subproblem{
			Content:      originalProblem,
			Difficulty:   0,
			Dependencies: []int{},
		})
	}

	return subproblems
}

// solveSubproblem solves one subproblem, optionally using previous solutions as context.
func (ltm *LeastToMost) solveSubproblem(
	ctx context.Context,
	subproblem Subproblem,
	previousSolutions []string,
) (string, error) {
	var prompt string

	if ltm.composeSolutions && len(previousSolutions) > 0 {
		// Include previous solutions as context
		var contextParts []string
		for i, sol := range previousSolutions {
			contextParts = append(contextParts, fmt.Sprintf("Previous solution %d: %s", i+1, sol))
		}
		context := strings.Join(contextParts, "\n")

		prompt = fmt.Sprintf(`Given these previous solutions to simpler subproblems:

%s

Now solve this subproblem:
%s

Solution:`, context, subproblem.Content)
	} else {
		// Solve without context
		prompt = fmt.Sprintf(`Solve this subproblem:

%s

Solution:`, subproblem.Content)
	}

	promptMessage := &agenkit.Message{
		Role:     "user",
		Content:  prompt,
		Metadata: make(map[string]interface{}),
	}

	response, err := ltm.agent.Process(ctx, promptMessage)
	if err != nil {
		return "", fmt.Errorf("subproblem solving failed: %w", err)
	}

	return strings.TrimSpace(response.ContentString()), nil
}

// Process processes a message with Least-to-Most reasoning.
//
// It decomposes the problem, solves subproblems sequentially from easiest
// to hardest, and composes the final solution.
//
// The response metadata includes:
//   - technique: "least_to_most"
//   - num_subproblems: int
//   - subproblems: []string
//   - subproblem_solutions: []string
//   - compose_solutions: bool
func (ltm *LeastToMost) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	problem := message.ContentString()

	// Step 1: Decompose problem
	subproblems, err := ltm.decompose(ctx, problem)
	if err != nil {
		return nil, fmt.Errorf("least to most decomposition failed: %w", err)
	}

	// Step 2: Solve subproblems sequentially
	solutions := make([]string, 0, len(subproblems))
	for _, subproblem := range subproblems {
		solution, err := ltm.solveSubproblem(ctx, subproblem, solutions)
		if err != nil {
			return nil, fmt.Errorf("subproblem solving failed: %w", err)
		}
		solutions = append(solutions, solution)
	}

	// Step 3: Final solution is the last one (hardest problem)
	finalSolution := ""
	if len(solutions) > 0 {
		finalSolution = solutions[len(solutions)-1]
	}

	// Build subproblem texts for metadata
	subproblemTexts := make([]string, len(subproblems))
	for i, sp := range subproblems {
		subproblemTexts[i] = sp.Content
	}

	response := agenkit.NewMessage("assistant", finalSolution)
	response.Metadata["technique"] = "least_to_most"
	response.Metadata["num_subproblems"] = len(subproblems)
	response.Metadata["subproblems"] = subproblemTexts
	response.Metadata["subproblem_solutions"] = solutions
	response.Metadata["compose_solutions"] = ltm.composeSolutions

	return response, nil
}

// Introspect returns introspection information about the agent.
func (ltm *LeastToMost) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(ltm)
}
