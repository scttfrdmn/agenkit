// Package reasoning provides reasoning techniques like Chain-of-Thought, Self-Consistency, etc.
package reasoning

import (
	"context"
	"fmt"
	"regexp"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ChainOfThought implements the Chain-of-Thought reasoning technique.
//
// It applies structured prompting to encourage step-by-step reasoning,
// optionally parsing and tracking individual reasoning steps.
//
// Reference: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
// Wei et al., 2022 - https://arxiv.org/abs/2201.11903
//
// Example:
//
//	cot := reasoning.NewChainOfThought(
//	    baseAgent,
//	    reasoning.WithPromptTemplate("Solve step by step:\n{query}"),
//	    reasoning.WithMaxSteps(5),
//	)
//	response, err := cot.Process(ctx, message)
type ChainOfThought struct {
	agent          agenkit.Agent
	promptTemplate string
	parseSteps     bool
	stepDelimiter  string
	maxSteps       *int
}

// ChainOfThoughtOption is a functional option for configuring ChainOfThought.
type ChainOfThoughtOption func(*ChainOfThought)

// WithPromptTemplate sets the prompt template with {query} placeholder.
func WithPromptTemplate(template string) ChainOfThoughtOption {
	return func(cot *ChainOfThought) {
		cot.promptTemplate = template
	}
}

// WithParseSteps sets whether to extract and track individual reasoning steps.
func WithParseSteps(parse bool) ChainOfThoughtOption {
	return func(cot *ChainOfThought) {
		cot.parseSteps = parse
	}
}

// WithStepDelimiter sets the delimiter for splitting steps.
func WithStepDelimiter(delimiter string) ChainOfThoughtOption {
	return func(cot *ChainOfThought) {
		cot.stepDelimiter = delimiter
	}
}

// WithMaxSteps sets the maximum number of reasoning steps to extract.
func WithMaxSteps(max int) ChainOfThoughtOption {
	return func(cot *ChainOfThought) {
		cot.maxSteps = &max
	}
}

// NewChainOfThought creates a new ChainOfThought agent.
//
// The agent wraps a base agent and applies CoT prompting to encourage
// step-by-step reasoning, leading to more accurate and explainable results.
//
// Example:
//
//	cot := reasoning.NewChainOfThought(
//	    baseAgent,
//	    reasoning.WithPromptTemplate("Think carefully:\n{query}"),
//	    reasoning.WithMaxSteps(5),
//	)
func NewChainOfThought(agent agenkit.Agent, options ...ChainOfThoughtOption) *ChainOfThought {
	cot := &ChainOfThought{
		agent:          agent,
		promptTemplate: "Let's think step by step:\n{query}",
		parseSteps:     true,
		stepDelimiter:  "\n",
		maxSteps:       nil,
	}

	for _, option := range options {
		option(cot)
	}

	return cot
}

// Name returns the agent name.
func (cot *ChainOfThought) Name() string {
	return "chain_of_thought"
}

// Capabilities returns the agent capabilities.
func (cot *ChainOfThought) Capabilities() []string {
	return []string{
		"reasoning",
		"step_by_step",
		"chain_of_thought",
		"explainable_ai",
	}
}

// Process processes a message with Chain-of-Thought reasoning.
//
// It applies the CoT prompt template to the input message, generates a
// response using the wrapped agent, and optionally parses reasoning steps.
//
// The response metadata includes:
//   - technique: "chain_of_thought"
//   - reasoning_steps: []string (if parseSteps is true)
//   - num_steps: int (if parseSteps is true)
func (cot *ChainOfThought) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Validate prompt template
	if !strings.Contains(cot.promptTemplate, "{query}") {
		return nil, fmt.Errorf("prompt template must contain {query} placeholder")
	}

	// Apply CoT prompting
	cotPrompt := strings.ReplaceAll(cot.promptTemplate, "{query}", message.Content)

	// Get response from agent
	promptMessage := &agenkit.Message{
		Role:     "user",
		Content:  cotPrompt,
		Metadata: make(map[string]interface{}),
	}

	response, err := cot.agent.Process(ctx, promptMessage)
	if err != nil {
		return nil, fmt.Errorf("chain of thought processing failed: %w", err)
	}

	// Initialize metadata if nil
	if response.Metadata == nil {
		response.Metadata = make(map[string]interface{})
	}

	// Parse steps if requested
	if cot.parseSteps {
		steps := cot.extractSteps(response.Content)
		response.Metadata["reasoning_steps"] = steps
		response.Metadata["num_steps"] = len(steps)
	}

	response.Metadata["technique"] = "chain_of_thought"

	return response, nil
}

// extractSteps extracts reasoning steps from response text.
//
// Supports multiple common step formats:
//   - Numbered steps (1. Step one, 2. Step two)
//   - Bullet points (- Step, * Step, • Step)
//   - Newline-separated thoughts (fallback)
//
// The parser tries formats in order: numbered, bullets, delimiter-based.
func (cot *ChainOfThought) extractSteps(text string) []string {
	// Try numbered steps first (1. 2. 3. or 1) 2) 3))
	numberedRegex := regexp.MustCompile(`(?m)^\d+[\.)]\s*(.+)$`)
	numberedMatches := numberedRegex.FindAllStringSubmatch(text, -1)

	if len(numberedMatches) >= 2 {
		steps := make([]string, 0, len(numberedMatches))
		for _, match := range numberedMatches {
			steps = append(steps, strings.TrimSpace(match[1]))
		}
		return cot.limitSteps(steps)
	}

	// Try bullet points (-, *, •)
	bulletRegex := regexp.MustCompile(`(?m)^[•\-\*]\s*(.+)$`)
	bulletMatches := bulletRegex.FindAllStringSubmatch(text, -1)

	if len(bulletMatches) >= 2 {
		steps := make([]string, 0, len(bulletMatches))
		for _, match := range bulletMatches {
			steps = append(steps, strings.TrimSpace(match[1]))
		}
		return cot.limitSteps(steps)
	}

	// Fall back to delimiter-based splitting
	lines := strings.Split(text, cot.stepDelimiter)
	steps := make([]string, 0, len(lines))
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" {
			steps = append(steps, trimmed)
		}
	}

	return cot.limitSteps(steps)
}

// limitSteps applies the maxSteps limit if configured.
func (cot *ChainOfThought) limitSteps(steps []string) []string {
	if cot.maxSteps != nil && len(steps) > *cot.maxSteps {
		return steps[:*cot.maxSteps]
	}
	return steps
}
