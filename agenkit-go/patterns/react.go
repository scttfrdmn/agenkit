// Package patterns provides the ReAct (Reasoning + Acting) pattern.
//
// ReAct combines reasoning (thinking through a problem) with acting
// (using tools to gather information or take actions). The agent alternates between:
// 1. Thought: Reasoning about what to do next
// 2. Action: Executing a tool to gather information or take action
// 3. Observation: Receiving the result of the action
//
// This pattern is based on the paper "ReAct: Synergizing Reasoning and Acting in
// Language Models" (Yao et al., 2022) and enables agents to dynamically reason about
// and interact with their environment through tool use.
//
// Key concepts:
//   - Interleaved reasoning and acting
//   - Tool-augmented agent behavior
//   - Observable decision-making process
//   - Self-directed exploration
//
// Performance characteristics:
//   - Steps: O(maxSteps) - bounded by configuration
//   - Each step: agent inference + optional tool execution
//   - Memory: O(steps) for conversation history
package patterns

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ReActStep represents a single step in the ReAct reasoning-acting loop.
type ReActStep struct {
	// Thought is the agent's reasoning about what to do
	Thought string
	// Action is the tool to use (if any)
	Action string
	// ActionInput is the input to the tool (if any)
	ActionInput string
	// Observation is the result of the action (if any)
	Observation string
	// IsFinal indicates whether this is the final answer
	IsFinal bool
}

// ReActStopReason indicates why the ReAct loop terminated.
type ReActStopReason string

const (
	// StopReasonFinalAnswer indicates the agent provided a final answer
	StopReasonFinalAnswer ReActStopReason = "final_answer"
	// StopReasonMaxSteps indicates the maximum number of steps was reached
	StopReasonMaxSteps ReActStopReason = "max_steps"
	// StopReasonInvalidAction indicates the agent made an invalid action
	StopReasonInvalidAction ReActStopReason = "invalid_action"
	// StopReasonToolError indicates tool execution failed
	StopReasonToolError ReActStopReason = "tool_error"
)

// ReActConfig configures a ReActAgent.
type ReActConfig struct {
	// Agent to use for reasoning
	Agent agenkit.Agent
	// Tools available to the agent
	Tools []agenkit.Tool
	// MaxSteps is the maximum number of reasoning-acting steps (default: 10)
	MaxSteps int
	// Verbose includes step-by-step reasoning in final output (default: true)
	Verbose bool
	// PromptTemplate is a custom prompt template for the agent
	PromptTemplate string
}

// ReActAgent combines reasoning with tool use.
//
// The agent follows this loop:
// 1. Think: Reason about what to do next
// 2. Act: Use a tool to gather information or take action
// 3. Observe: See the result and incorporate into reasoning
// 4. Repeat until final answer or max steps
//
// Expected agent response format:
//
//	Thought: [reasoning about what to do]
//	Action: [tool name]
//	Action Input: [tool input]
//
// Or for final answer:
//
//	Thought: [reasoning about conclusion]
//	Final Answer: [the final answer]
type ReActAgent struct {
	name           string
	agent          agenkit.Agent
	tools          map[string]agenkit.Tool
	maxSteps       int
	verbose        bool
	promptTemplate string
	steps          []ReActStep
}

// NewReActAgent creates a new ReAct agent.
func NewReActAgent(config *ReActConfig) (*ReActAgent, error) {
	if config == nil {
		return nil, fmt.Errorf("config is required")
	}
	if config.Agent == nil {
		return nil, fmt.Errorf("agent is required")
	}
	if len(config.Tools) == 0 {
		return nil, fmt.Errorf("at least one tool is required")
	}

	// Build tools map
	toolsMap := make(map[string]agenkit.Tool)
	for _, tool := range config.Tools {
		toolsMap[tool.Name()] = tool
	}

	maxSteps := config.MaxSteps
	if maxSteps == 0 {
		maxSteps = 10
	}

	verbose := config.Verbose
	// Default to true if not explicitly set
	if !config.Verbose && config.MaxSteps == 0 && config.PromptTemplate == "" {
		verbose = true
	}

	promptTemplate := config.PromptTemplate
	if promptTemplate == "" {
		promptTemplate = buildDefaultPrompt(config.Tools)
	}

	return &ReActAgent{
		name:           "ReActAgent",
		agent:          config.Agent,
		tools:          toolsMap,
		maxSteps:       maxSteps,
		verbose:        verbose,
		promptTemplate: promptTemplate,
		steps:          []ReActStep{},
	}, nil
}

// buildDefaultPrompt creates the default prompt template with tool descriptions.
func buildDefaultPrompt(tools []agenkit.Tool) string {
	var toolDescriptions strings.Builder
	for i, tool := range tools {
		if i > 0 {
			toolDescriptions.WriteString("\n")
		}
		toolDescriptions.WriteString(fmt.Sprintf("- %s: %s", tool.Name(), tool.Description()))
	}

	return fmt.Sprintf(`You are a helpful assistant that can use tools to answer questions.

Available tools:
%s

Use the following format:

Thought: Think about what to do next
Action: [tool name]
Action Input: [input for the tool]
Observation: [result will be provided]

... (repeat Thought/Action/Observation as needed)

Thought: I now know the final answer
Final Answer: [your final answer here]

Begin!`, toolDescriptions.String())
}

// Name returns the agent name.
func (r *ReActAgent) Name() string {
	return r.name
}

// Capabilities returns the agent's capabilities.
func (r *ReActAgent) Capabilities() []string {
	return []string{"reasoning", "tool-use", "react"}
}

// Process executes the ReAct reasoning-acting loop.
func (r *ReActAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	r.steps = []ReActStep{}
	conversationHistory := []string{r.promptTemplate, fmt.Sprintf("\nQuestion: %s", message.Content)}

	for step := 0; step < r.maxSteps; step++ {
		// Get agent's reasoning
		prompt := strings.Join(conversationHistory, "\n")
		response, err := r.agent.Process(ctx, &agenkit.Message{
			Role:    "user",
			Content: prompt,
		})
		if err != nil {
			return nil, fmt.Errorf("agent process failed: %w", err)
		}

		responseText := response.Content

		// Parse the response
		parsed := r.parseResponse(responseText)

		// Check for final answer
		if parsed.IsFinal {
			r.steps = append(r.steps, parsed)
			return r.formatFinalAnswer(parsed, StopReasonFinalAnswer), nil
		}

		// Validate action
		if parsed.Action == "" {
			r.steps = append(r.steps, parsed)
			return r.formatFinalAnswer(parsed, StopReasonInvalidAction), nil
		}

		// Execute action
		tool, ok := r.tools[parsed.Action]
		if !ok {
			toolNames := make([]string, 0, len(r.tools))
			for name := range r.tools {
				toolNames = append(toolNames, name)
			}
			parsed.Observation = fmt.Sprintf("Error: Tool '%s' not found. Available tools: %s",
				parsed.Action, strings.Join(toolNames, ", "))
			r.steps = append(r.steps, parsed)
			conversationHistory = append(conversationHistory, r.formatStep(parsed))
			continue
		}

		// Execute tool
		toolResult, err := tool.Execute(ctx, map[string]interface{}{"input": parsed.ActionInput})
		if err != nil {
			parsed.Observation = fmt.Sprintf("Error: %v", err)
			r.steps = append(r.steps, parsed)
			return r.formatFinalAnswer(parsed, StopReasonToolError), nil
		}

		if toolResult.Success {
			parsed.Observation = fmt.Sprintf("%v", toolResult.Data)
		} else {
			errorMsg := "Tool execution failed"
			if toolResult.Error != "" {
				errorMsg = toolResult.Error
			}
			parsed.Observation = fmt.Sprintf("Error: %s", errorMsg)
		}

		// Record step and add to conversation
		r.steps = append(r.steps, parsed)
		conversationHistory = append(conversationHistory, r.formatStep(parsed))
	}

	// Max steps reached
	lastStep := ReActStep{
		Thought: "Reached maximum steps without finding answer",
		IsFinal: false,
	}
	if len(r.steps) > 0 {
		lastStep = r.steps[len(r.steps)-1]
	}

	return r.formatFinalAnswer(lastStep, StopReasonMaxSteps), nil
}

// parseResponse parses agent response into structured step.
func (r *ReActAgent) parseResponse(response string) ReActStep {
	lines := strings.Split(response, "\n")
	step := ReActStep{}

	for _, line := range lines {
		line = strings.TrimSpace(line)

		if strings.HasPrefix(line, "Thought:") {
			step.Thought = strings.TrimSpace(strings.TrimPrefix(line, "Thought:"))
		} else if strings.HasPrefix(line, "Action:") {
			step.Action = strings.TrimSpace(strings.TrimPrefix(line, "Action:"))
		} else if strings.HasPrefix(line, "Action Input:") {
			step.ActionInput = strings.TrimSpace(strings.TrimPrefix(line, "Action Input:"))
		} else if strings.HasPrefix(line, "Final Answer:") {
			if step.Thought == "" {
				step.Thought = "Reached final answer"
			}
			step.Observation = strings.TrimSpace(strings.TrimPrefix(line, "Final Answer:"))
			step.IsFinal = true
			break
		}
	}

	return step
}

// formatStep formats a step for conversation history.
func (r *ReActAgent) formatStep(step ReActStep) string {
	var formatted strings.Builder
	formatted.WriteString(fmt.Sprintf("Thought: %s", step.Thought))

	if step.Action != "" {
		formatted.WriteString(fmt.Sprintf("\nAction: %s", step.Action))
		formatted.WriteString(fmt.Sprintf("\nAction Input: %s", step.ActionInput))
	}

	if step.Observation != "" {
		formatted.WriteString(fmt.Sprintf("\nObservation: %s", step.Observation))
	}

	return formatted.String()
}

// formatFinalAnswer formats the final answer message.
func (r *ReActAgent) formatFinalAnswer(step ReActStep, stopReason ReActStopReason) *agenkit.Message {
	var content strings.Builder

	if r.verbose {
		// Include full reasoning trace
		for i, s := range r.steps {
			if i > 0 {
				content.WriteString("\n\n")
			}
			content.WriteString(r.formatStep(s))
		}
		content.WriteString("\n\n---\n\n")
	}

	// Add final answer
	if stopReason == StopReasonFinalAnswer {
		finalAnswer := step.Observation
		if finalAnswer == "" {
			finalAnswer = "No final answer provided"
		}
		content.WriteString(finalAnswer)
	} else {
		content.WriteString(fmt.Sprintf("Unable to complete task (%s)", stopReason))
		if step.Thought != "" {
			content.WriteString(fmt.Sprintf("\nLast thought: %s", step.Thought))
		}
	}

	return &agenkit.Message{
		Role:    "assistant",
		Content: content.String(),
		Metadata: map[string]interface{}{
			"stop_reason": string(stopReason),
			"steps":       len(r.steps),
			"reasoning":   r.steps,
		},
	}
}

// GetSteps returns the reasoning history (useful for debugging/analysis).
func (r *ReActAgent) GetSteps() []ReActStep {
	// Return a copy to prevent external modification
	steps := make([]ReActStep, len(r.steps))
	copy(steps, r.steps)
	return steps
}
