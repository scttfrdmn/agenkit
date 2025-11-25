// Package patterns provides the Reasoning with Tools pattern.
//
// Enables interleaved reasoning and tool usage, where tools can be called
// DURING the reasoning process rather than only after reasoning completes.
//
// This pattern is inspired by Claude 4 and o3's extended thinking capabilities,
// where the model can use tools to refine its reasoning in real-time.
//
// Key differences from ReAct:
//   - ReAct: Observe → Think → Act → Observe → Think → Act (sequential)
//   - This: Think ↔ Act (interleaved, tools available during thinking)
//   - Tools help refine reasoning, not just execute actions
//   - Supports extended thinking with tool integration
//
// Example:
//
//	agent := patterns.NewReasoningWithToolsAgent(
//	    llmAgent,
//	    []agenkit.Tool{calculator, webSearch},
//	    &patterns.ReasoningWithToolsConfig{MaxReasoningSteps: 10},
//	)
//
//	// Agent can use tools WHILE reasoning about the problem
//	response, _ := agent.Process(ctx, &agenkit.Message{
//	    Role: "user",
//	    Content: "What's the total cost if I buy 3 items at $15.99 each with 8.5% tax?",
//	})
package patterns

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ReasoningStepType represents the type of reasoning step.
type ReasoningStepType string

const (
	// ReasoningStepThinking indicates a thinking step
	ReasoningStepThinking ReasoningStepType = "thinking"
	// ReasoningStepToolCall indicates a tool call step
	ReasoningStepToolCall ReasoningStepType = "tool_call"
	// ReasoningStepToolResult indicates a tool result step
	ReasoningStepToolResult ReasoningStepType = "tool_result"
	// ReasoningStepConclusion indicates a conclusion step
	ReasoningStepConclusion ReasoningStepType = "conclusion"
)

// ReasoningStep represents a single step in the reasoning process.
type ReasoningStep struct {
	// StepNumber is the step number
	StepNumber int
	// StepType is the type of step
	StepType ReasoningStepType
	// Content is the step content
	Content string
	// ToolName for tool calls
	ToolName string
	// ToolParameters for tool calls
	ToolParameters map[string]interface{}
	// ToolResult for tool results
	ToolResult interface{}
	// Confidence score
	Confidence float64
	// Timestamp in milliseconds
	Timestamp int64
}

// ReasoningTrace represents a complete trace of the reasoning process.
type ReasoningTrace struct {
	// Steps contains all reasoning steps
	Steps []ReasoningStep
	// TotalToolsUsed count
	TotalToolsUsed int
	// TotalThinkingSteps count
	TotalThinkingSteps int
	// StartTime in milliseconds
	StartTime int64
	// EndTime in milliseconds
	EndTime int64
}

// ReasoningWithToolsConfig configures a ReasoningWithToolsAgent.
type ReasoningWithToolsConfig struct {
	// MaxReasoningSteps is the maximum reasoning steps
	MaxReasoningSteps int
	// ToolUsePrompt is a custom tool use prompt
	ToolUsePrompt string
	// EnableTrace enables reasoning trace
	EnableTrace bool
	// ConfidenceThreshold is the confidence threshold
	ConfidenceThreshold float64
}

// ReasoningWithToolsAgent can use tools during reasoning (not just after).
//
// This pattern enables the model to:
// 1. Start reasoning about a problem
// 2. Realize it needs information
// 3. Call a tool to get that information
// 4. Continue reasoning with the new information
// 5. Repeat as needed
//
// This is different from ReAct where:
//   - Reasoning happens BEFORE action
//   - Action is taken BASED ON completed reasoning
//   - New observation triggers NEW reasoning
//
// Example:
//
//	agent := NewReasoningWithToolsAgent(llm, tools, &ReasoningWithToolsConfig{
//	    MaxReasoningSteps: 20,
//	    EnableTrace: true,
//	})
//
//	result, _ := agent.Process(ctx, &agenkit.Message{
//	    Role: "user",
//	    Content: "Calculate compound interest",
//	})
type ReasoningWithToolsAgent struct {
	name                string
	llm                 agenkit.Agent
	tools               map[string]agenkit.Tool
	maxReasoningSteps   int
	toolUsePrompt       string
	enableTrace         bool
	confidenceThreshold float64
}

// NewReasoningWithToolsAgent creates a new reasoning with tools agent.
func NewReasoningWithToolsAgent(
	llm agenkit.Agent,
	tools []agenkit.Tool,
	config *ReasoningWithToolsConfig,
) *ReasoningWithToolsAgent {
	if config == nil {
		config = &ReasoningWithToolsConfig{
			EnableTrace: true, // Default when config is nil
		}
	}

	maxSteps := config.MaxReasoningSteps
	if maxSteps == 0 {
		maxSteps = 20
	}

	confidenceThreshold := config.ConfidenceThreshold
	if confidenceThreshold == 0 {
		confidenceThreshold = 0.8
	}

	enableTrace := config.EnableTrace

	toolsMap := make(map[string]agenkit.Tool)
	for _, tool := range tools {
		toolsMap[tool.Name()] = tool
	}

	agent := &ReasoningWithToolsAgent{
		name:                fmt.Sprintf("reasoning_with_tools_%s", llm.Name()),
		llm:                 llm,
		tools:               toolsMap,
		maxReasoningSteps:   maxSteps,
		enableTrace:         enableTrace,
		confidenceThreshold: confidenceThreshold,
	}

	if config.ToolUsePrompt != "" {
		agent.toolUsePrompt = config.ToolUsePrompt
	} else {
		agent.toolUsePrompt = agent.defaultToolPrompt()
	}

	return agent
}

// defaultToolPrompt generates the default tool usage prompt.
func (r *ReasoningWithToolsAgent) defaultToolPrompt() string {
	toolDescriptions := make([]string, 0)
	for _, tool := range r.tools {
		toolDescriptions = append(toolDescriptions, fmt.Sprintf("- %s: %s", tool.Name(), tool.Description()))
	}

	return fmt.Sprintf(`You can use tools WHILE reasoning about the problem.
When you need information or computation, use a tool immediately.
Don't wait until you finish reasoning - use tools as needed.

Available tools:
%s

To use a tool, output:
TOOL_CALL: <tool_name>
PARAMETERS: {"param1": "value1", ...}

Continue reasoning after you get the tool result.`, strings.Join(toolDescriptions, "\n"))
}

// Name returns the agent name.
func (r *ReasoningWithToolsAgent) Name() string {
	return r.name
}

// Capabilities returns the agent capabilities.
func (r *ReasoningWithToolsAgent) Capabilities() []string {
	return []string{"reasoning", "tool-use", "interleaved-thinking"}
}

// Process processes message with reasoning and tool use.
func (r *ReasoningWithToolsAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	var trace *ReasoningTrace
	if r.enableTrace {
		trace = &ReasoningTrace{
			Steps:          make([]ReasoningStep, 0),
			StartTime:      currentTimeMillis(),
			TotalToolsUsed: 0,
		}
	}

	// Enhance message with tool instructions
	enhancedContent := fmt.Sprintf(`%s

USER QUESTION:
%s

Begin reasoning. Use tools as needed while thinking.`, r.toolUsePrompt, message.Content)

	// Reasoning loop
	currentContext := enhancedContent
	var finalAnswer string

	for stepNum := 0; stepNum < r.maxReasoningSteps; stepNum++ {
		// Check context cancellation
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		// Get next reasoning step from LLM
		response, err := r.llm.Process(ctx, &agenkit.Message{
			Role:    "user",
			Content: currentContext,
		})
		if err != nil {
			return nil, fmt.Errorf("LLM process failed: %w", err)
		}

		responseText := response.Content

		// Check if this is a tool call
		if strings.Contains(responseText, "TOOL_CALL:") {
			toolName, parameters, remainingText := r.parseToolCall(responseText)

			if toolName != "" && r.tools[toolName] != nil {
				// Record thinking before tool call
				if trace != nil && strings.TrimSpace(remainingText) != "" {
					trace.Steps = append(trace.Steps, ReasoningStep{
						StepNumber: stepNum,
						StepType:   ReasoningStepThinking,
						Content:    strings.TrimSpace(remainingText),
						Timestamp:  currentTimeMillis(),
					})
					trace.TotalThinkingSteps++
				}

				// Execute tool
				tool := r.tools[toolName]
				toolResult, err := tool.Execute(ctx, parameters)

				if err == nil {
					// Record tool call and result
					if trace != nil {
						trace.Steps = append(trace.Steps, ReasoningStep{
							StepNumber:     stepNum,
							StepType:       ReasoningStepToolCall,
							Content:        fmt.Sprintf("Called %s", toolName),
							ToolName:       toolName,
							ToolParameters: parameters,
							Timestamp:      currentTimeMillis(),
						})

						trace.Steps = append(trace.Steps, ReasoningStep{
							StepNumber: stepNum,
							StepType:   ReasoningStepToolResult,
							Content:    fmt.Sprintf("%v", toolResult.Data),
							ToolName:   toolName,
							ToolResult: toolResult.Data,
							Timestamp:  currentTimeMillis(),
						})
						trace.TotalToolsUsed++
					}

					// Update context with tool result
					currentContext = fmt.Sprintf(`Previous reasoning: %s

TOOL RESULT from %s:
%v

Continue reasoning with this information.`, currentContext, toolName, toolResult.Data)
				} else {
					// Tool execution failed
					errorMsg := fmt.Sprintf("Tool %s failed: %v", toolName, err)
					if trace != nil {
						trace.Steps = append(trace.Steps, ReasoningStep{
							StepNumber: stepNum,
							StepType:   ReasoningStepToolResult,
							Content:    errorMsg,
							ToolName:   toolName,
							Timestamp:  currentTimeMillis(),
						})
					}

					currentContext = fmt.Sprintf(`%s

ERROR: %s

Continue reasoning without this tool.`, currentContext, errorMsg)
				}
			} else {
				// Unknown tool, continue with regular thinking
				if trace != nil {
					trace.Steps = append(trace.Steps, ReasoningStep{
						StepNumber: stepNum,
						StepType:   ReasoningStepThinking,
						Content:    responseText,
						Timestamp:  currentTimeMillis(),
					})
					trace.TotalThinkingSteps++
				}

				currentContext = fmt.Sprintf(`%s

%s

Continue.`, currentContext, responseText)
			}
		} else {
			// Check if we have a final answer
			if r.isConclusion(responseText) {
				finalAnswer = r.extractAnswer(responseText)
				if trace != nil {
					trace.Steps = append(trace.Steps, ReasoningStep{
						StepNumber: stepNum,
						StepType:   ReasoningStepConclusion,
						Content:    finalAnswer,
						Timestamp:  currentTimeMillis(),
					})
				}
				break
			}

			// Regular thinking step
			if trace != nil {
				trace.Steps = append(trace.Steps, ReasoningStep{
					StepNumber: stepNum,
					StepType:   ReasoningStepThinking,
					Content:    responseText,
					Timestamp:  currentTimeMillis(),
				})
				trace.TotalThinkingSteps++
			}

			// Update context for next iteration
			currentContext = fmt.Sprintf(`%s

%s

Continue reasoning or provide final answer.`, currentContext, responseText)
		}
	}

	// Finalize trace
	if trace != nil {
		trace.EndTime = currentTimeMillis()
	}

	// If no answer found, use last response
	if finalAnswer == "" {
		finalAnswer = currentContext
	}

	// Create response with trace
	metadata := make(map[string]interface{})
	if trace != nil {
		metadata["reasoning_trace"] = traceToDict(trace)
		metadata["reasoning_steps"] = len(trace.Steps)
		metadata["tools_used"] = trace.TotalToolsUsed
	}

	return &agenkit.Message{
		Role:     "assistant",
		Content:  finalAnswer,
		Metadata: metadata,
	}, nil
}

// parseToolCall parses tool call from text.
func (r *ReasoningWithToolsAgent) parseToolCall(text string) (string, map[string]interface{}, string) {
	if !strings.Contains(text, "TOOL_CALL:") {
		return "", nil, text
	}

	parts := strings.SplitN(text, "TOOL_CALL:", 2)
	before := parts[0]
	after := parts[1]

	// Get tool name (first line after TOOL_CALL:)
	lines := strings.Split(after, "\n")
	toolName := strings.TrimSpace(lines[0])

	// Extract parameters
	parameters := make(map[string]interface{})
	if strings.Contains(after, "PARAMETERS:") {
		paramParts := strings.SplitN(after, "PARAMETERS:", 2)
		paramText := strings.TrimSpace(paramParts[1])

		// Try to parse JSON
		start := strings.Index(paramText, "{")
		if start != -1 {
			// Find matching closing brace
			depth := 0
			end := start
			for i := start; i < len(paramText); i++ {
				if paramText[i] == '{' {
					depth++
				} else if paramText[i] == '}' {
					depth--
					if depth == 0 {
						end = i + 1
						break
					}
				}
			}

			jsonStr := paramText[start:end]
			_ = json.Unmarshal([]byte(jsonStr), &parameters)
		}
	}

	return toolName, parameters, before
}

// isConclusion checks if text contains a final conclusion.
func (r *ReasoningWithToolsAgent) isConclusion(text string) bool {
	conclusionMarkers := []string{
		"FINAL ANSWER:",
		"CONCLUSION:",
		"Therefore,",
		"In conclusion,",
		"The answer is",
	}

	textUpper := strings.ToUpper(text)
	for _, marker := range conclusionMarkers {
		if strings.Contains(textUpper, strings.ToUpper(marker)) {
			return true
		}
	}

	return false
}

// extractAnswer extracts final answer from conclusion text.
func (r *ReasoningWithToolsAgent) extractAnswer(text string) string {
	markers := []string{"FINAL ANSWER:", "CONCLUSION:", "The answer is"}
	textUpper := strings.ToUpper(text)

	for _, marker := range markers {
		if strings.Contains(textUpper, strings.ToUpper(marker)) {
			idx := strings.Index(textUpper, strings.ToUpper(marker))
			return strings.TrimSpace(text[idx+len(marker):])
		}
	}

	return text
}

// GetTool gets a tool by name.
func (r *ReasoningWithToolsAgent) GetTool(name string) agenkit.Tool {
	return r.tools[name]
}

// AddTool adds a tool.
func (r *ReasoningWithToolsAgent) AddTool(tool agenkit.Tool) {
	r.tools[tool.Name()] = tool
}

// RemoveTool removes a tool.
func (r *ReasoningWithToolsAgent) RemoveTool(name string) bool {
	if _, exists := r.tools[name]; exists {
		delete(r.tools, name)
		return true
	}
	return false
}

// Helper functions

func currentTimeMillis() int64 {
	return time.Now().UnixNano() / 1000000
}

func traceToDict(trace *ReasoningTrace) map[string]interface{} {
	steps := make([]map[string]interface{}, len(trace.Steps))
	for i, step := range trace.Steps {
		steps[i] = map[string]interface{}{
			"step_number":     step.StepNumber,
			"step_type":       string(step.StepType),
			"content":         step.Content,
			"tool_name":       step.ToolName,
			"tool_parameters": step.ToolParameters,
			"tool_result":     step.ToolResult,
			"confidence":      step.Confidence,
			"timestamp":       step.Timestamp,
		}
	}

	durationSeconds := float64(trace.EndTime-trace.StartTime) / 1000.0

	return map[string]interface{}{
		"steps":                steps,
		"total_tools_used":     trace.TotalToolsUsed,
		"total_thinking_steps": trace.TotalThinkingSteps,
		"duration_seconds":     durationSeconds,
	}
}
